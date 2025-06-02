from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
import uuid
from datetime import datetime
import asyncio
import pandas as pd
import io
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import time
import re

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Pydantic Models
class SeasonFixture(BaseModel):
    season: str
    match_date: str
    home_team: str
    away_team: str
    match_url: str

class MatchData(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    match_date: str
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    season: str
    stadium: str
    referee: str
    assistant_referees: List[str] = []
    fourth_official: str = ""
    var_referee: str = ""
    
    # Team Stats - Home Team
    home_possession: float = 0.0
    home_shots: int = 0
    home_shots_on_target: int = 0
    home_expected_goals: float = 0.0
    home_corners: int = 0
    home_tackles: int = 0
    home_fouls_committed: int = 0
    home_fouls_drawn: int = 0
    home_yellow_cards: int = 0
    home_red_cards: int = 0
    home_passing_accuracy: float = 0.0
    home_crosses_completed: int = 0
    home_clearances: int = 0
    home_blocks: int = 0
    home_saves: int = 0
    home_expected_goals_against: float = 0.0
    
    # Team Stats - Away Team
    away_possession: float = 0.0
    away_shots: int = 0
    away_shots_on_target: int = 0
    away_expected_goals: float = 0.0
    away_corners: int = 0
    away_tackles: int = 0
    away_fouls_committed: int = 0
    away_fouls_drawn: int = 0
    away_yellow_cards: int = 0
    away_red_cards: int = 0
    away_passing_accuracy: float = 0.0
    away_crosses_completed: int = 0
    away_clearances: int = 0
    away_blocks: int = 0
    away_saves: int = 0
    away_expected_goals_against: float = 0.0
    
    match_url: str = ""
    scraped_at: datetime = Field(default_factory=datetime.utcnow)

class ScrapingStatus(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: str  # "running", "completed", "failed"
    matches_scraped: int = 0
    total_matches: int = 0
    current_match: str = ""
    errors: List[str] = []
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

class FilterRequest(BaseModel):
    season: Optional[str] = None
    teams: Optional[List[str]] = []
    referee: Optional[str] = None

# Enhanced FBref Scraper with Playwright for ARM64 compatibility
class FBrefScraper:
    def __init__(self):
        self.browser = None
        self.page = None
        self.playwright = None
        
    async def setup_browser(self):
        """Setup Playwright browser for ARM64"""
        try:
            self.playwright = await async_playwright().start()
            
            # Launch Chromium with optimized settings for ARM64
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage", 
                    "--disable-gpu",
                    "--disable-software-rasterizer",
                    "--disable-extensions",
                    "--disable-plugins",
                    "--disable-images",
                    "--disable-web-security",
                    "--single-process"
                ]
            )
            
            # Create new page with proper viewport
            self.page = await self.browser.new_page(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
            )
            
            logger.info("Playwright browser setup successful for ARM64 - REAL scraping enabled")
            return True
            
        except Exception as e:
            logger.error(f"Playwright browser setup failed: {e}")
            return False
    
    def get_season_fixtures_url(self, season: str) -> str:
        """Get the fixtures URL for a specific season"""
        if season == "2024-25":
            return "https://fbref.com/en/comps/9/schedule/Premier-League-Scores-and-Fixtures"
        else:
            # For historical seasons, use a different URL pattern
            return f"https://fbref.com/en/comps/9/{season}/schedule/2023-24-Premier-League-Scores-and-Fixtures"
    
    def extract_match_links(self, season: str) -> List[str]:
        """Extract all match report links from a season's fixtures page"""
        try:
            fixtures_url = self.get_season_fixtures_url(season)
            logger.info(f"Fetching fixtures from: {fixtures_url}")
            
            self.driver.get(fixtures_url)
            time.sleep(5)
            
            # Find match report links - look for both score links and "Match Report" text
            match_links = set()  # Use set to avoid duplicates
            links = self.driver.find_elements(By.TAG_NAME, "a")
            
            import re
            # Score patterns: "2-1", "0-0", etc. (including em dash and regular dash)
            score_pattern = re.compile(r'^\d+[–-]\d+$')
            
            for link in links:
                href = link.get_attribute("href")
                link_text = link.text.strip()
                
                if href and "/en/matches/" in href and len(href.split("/")) > 5:
                    # Check for score links or "Match Report" text
                    if score_pattern.match(link_text) or link_text == "Match Report":
                        match_links.add(href)
                        logger.info(f"Found match: {link_text} -> {href}")
            
            match_links_list = list(match_links)
            logger.info(f"Found {len(match_links_list)} unique match reports for season {season}")
            return match_links_list
            
        except Exception as e:
            logger.error(f"Error extracting match links for season {season}: {e}")
            return []
    
    def extract_match_metadata(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract basic match metadata"""
        metadata = {}
        
        try:
            # Extract team names and score from the page title or scorebox
            scorebox = soup.find("div", {"class": "scorebox"})
            if scorebox:
                teams = scorebox.find_all("div", {"itemprop": "name"})
                if len(teams) >= 2:
                    metadata["home_team"] = teams[0].get_text().strip()
                    metadata["away_team"] = teams[1].get_text().strip()
                
                # Extract scores
                scores = scorebox.find_all("div", {"class": "score"})
                if len(scores) >= 2:
                    metadata["home_score"] = int(scores[0].get_text().strip() or 0)
                    metadata["away_score"] = int(scores[1].get_text().strip() or 0)
            
            # Extract match date
            match_date_elem = soup.find("span", {"class": "venuetime"})
            if match_date_elem:
                date_text = match_date_elem.get("data-venue-date")
                if date_text:
                    metadata["match_date"] = date_text
                    
            # Extract referee information
            match_info = soup.find("div", {"id": "info_box"}) or soup.find("div", {"class": "info_box"})
            if match_info:
                referee_text = match_info.get_text()
                
                # Extract referee
                referee_match = re.search(r"Referee:\s*([^,\n]+)", referee_text)
                if referee_match:
                    metadata["referee"] = referee_match.group(1).strip()
                
                # Extract assistants
                assistant_match = re.search(r"Assistant(?:s)?:\s*([^,\n]+)", referee_text)
                if assistant_match:
                    assistants = [a.strip() for a in assistant_match.group(1).split(",")]
                    metadata["assistant_referees"] = assistants
                
                # Extract 4th official
                fourth_match = re.search(r"Fourth [Oo]fficial:\s*([^,\n]+)", referee_text)
                if fourth_match:
                    metadata["fourth_official"] = fourth_match.group(1).strip()
                
                # Extract VAR
                var_match = re.search(r"VAR:\s*([^,\n]+)", referee_text)
                if var_match:
                    metadata["var_referee"] = var_match.group(1).strip()
                    
                # Extract stadium
                stadium_match = re.search(r"Venue:\s*([^,\n]+)", referee_text)
                if stadium_match:
                    metadata["stadium"] = stadium_match.group(1).strip()
            
        except Exception as e:
            logger.error(f"Error extracting metadata: {e}")
        
        return metadata
    
    def extract_team_stats(self, soup: BeautifulSoup, team_name: str) -> Dict[str, Any]:
        """Extract statistics for a specific team"""
        stats = {}
        
        try:
            # Normalize team name for table IDs
            team_id = team_name.replace(" ", "-").replace("'", "")
            
            # Summary stats table
            summary_table = soup.find("table", {"id": f"stats_summary_{team_id}"})
            if summary_table:
                # Extract possession from summary
                poss_cell = summary_table.find("td", {"data-stat": "possession"})
                if poss_cell:
                    poss_text = poss_cell.get_text().strip().replace("%", "")
                    try:
                        stats["possession"] = float(poss_text)
                    except ValueError:
                        stats["possession"] = 0.0
            
            # Look for team stats in various possible table structures
            for table in soup.find_all("table"):
                table_text = table.get_text().lower()
                
                if team_name.lower() in table_text:
                    # Extract shots data
                    shots_cell = table.find("td", {"data-stat": "shots_total"})
                    if shots_cell:
                        try:
                            stats["shots"] = int(shots_cell.get_text().strip() or 0)
                        except ValueError:
                            pass
                    
                    # Extract shots on target
                    sot_cell = table.find("td", {"data-stat": "shots_on_target"})
                    if sot_cell:
                        try:
                            stats["shots_on_target"] = int(sot_cell.get_text().strip() or 0)
                        except ValueError:
                            pass
                    
                    # Extract xG
                    xg_cell = table.find("td", {"data-stat": "xg"})
                    if xg_cell:
                        try:
                            stats["expected_goals"] = float(xg_cell.get_text().strip() or 0)
                        except ValueError:
                            pass
                    
                    # Extract fouls
                    fouls_cell = table.find("td", {"data-stat": "fouls"})
                    if fouls_cell:
                        try:
                            stats["fouls_committed"] = int(fouls_cell.get_text().strip() or 0)
                        except ValueError:
                            pass
                    
                    # Extract cards
                    yellow_cell = table.find("td", {"data-stat": "cards_yellow"})
                    if yellow_cell:
                        try:
                            stats["yellow_cards"] = int(yellow_cell.get_text().strip() or 0)
                        except ValueError:
                            pass
                    
                    red_cell = table.find("td", {"data-stat": "cards_red"})
                    if red_cell:
                        try:
                            stats["red_cards"] = int(red_cell.get_text().strip() or 0)
                        except ValueError:
                            pass
            
        except Exception as e:
            logger.error(f"Error extracting stats for {team_name}: {e}")
        
        return stats
    
    def scrape_match_report(self, match_url: str, season: str) -> Optional[MatchData]:
        """Scrape a single match report"""
        try:
            logger.info(f"Scraping match: {match_url}")
            self.driver.get(match_url)
            time.sleep(3)
            
            # Get page source and parse with BeautifulSoup
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Extract metadata
            metadata = self.extract_match_metadata(soup)
            
            if not metadata.get("home_team") or not metadata.get("away_team"):
                logger.warning(f"Could not extract team names from {match_url}")
                return None
            
            # Extract team stats
            home_stats = self.extract_team_stats(soup, metadata["home_team"])
            away_stats = self.extract_team_stats(soup, metadata["away_team"])
            
            # Create MatchData object
            match_data = MatchData(
                season=season,
                match_url=match_url,
                home_team=metadata.get("home_team", ""),
                away_team=metadata.get("away_team", ""),
                home_score=metadata.get("home_score", 0),
                away_score=metadata.get("away_score", 0),
                match_date=metadata.get("match_date", ""),
                stadium=metadata.get("stadium", ""),
                referee=metadata.get("referee", ""),
                assistant_referees=metadata.get("assistant_referees", []),
                fourth_official=metadata.get("fourth_official", ""),
                var_referee=metadata.get("var_referee", ""),
                
                # Home team stats
                home_possession=home_stats.get("possession", 0.0),
                home_shots=home_stats.get("shots", 0),
                home_shots_on_target=home_stats.get("shots_on_target", 0),
                home_expected_goals=home_stats.get("expected_goals", 0.0),
                home_fouls_committed=home_stats.get("fouls_committed", 0),
                home_yellow_cards=home_stats.get("yellow_cards", 0),
                home_red_cards=home_stats.get("red_cards", 0),
                
                # Away team stats
                away_possession=away_stats.get("possession", 0.0),
                away_shots=away_stats.get("shots", 0),
                away_shots_on_target=away_stats.get("shots_on_target", 0),
                away_expected_goals=away_stats.get("expected_goals", 0.0),
                away_fouls_committed=away_stats.get("fouls_committed", 0),
                away_yellow_cards=away_stats.get("yellow_cards", 0),
                away_red_cards=away_stats.get("red_cards", 0),
            )
            
            return match_data
            
        except Exception as e:
            logger.error(f"Error scraping match {match_url}: {e}")
            return None
    
    def cleanup(self):
        """Clean up Playwright browser resources"""
        async def _cleanup():
            try:
                if self.page:
                    await self.page.close()
                if self.browser:
                    await self.browser.close()
                if self.playwright:
                    await self.playwright.stop()
            except Exception as e:
                logger.error(f"Error during Playwright cleanup: {e}")
        
        # Run cleanup in async context
        try:
            asyncio.create_task(_cleanup())
        except:
            pass

    async def extract_season_fixtures(self, season: str) -> List[SeasonFixture]:
        """Extract fixtures for a season using Playwright"""
        try:
            logger.info(f"Extracting REAL fixtures from FBref for season {season}")
            
            fixtures_url = self.get_season_fixtures_url(season)
            current_season = season == "2024-25"
            
            logger.info(f"Fetching fixtures from: {fixtures_url} (Current season: {current_season})")
            
            # Navigate to fixtures page
            await self.page.goto(fixtures_url, wait_until='networkidle')
            
            # Wait for the fixtures table to load
            await self.page.wait_for_selector('table', timeout=30000)
            
            # Get page content and parse with BeautifulSoup
            content = await self.page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Debug: Log page title to confirm we're on the right page
            title = soup.find('title')
            logger.info(f"Page title: {title.text if title else 'No title found'}")
            
            # Find all tables on the page and log their IDs
            all_tables = soup.find_all('table')
            logger.info(f"Found {len(all_tables)} tables on page")
            for i, table in enumerate(all_tables):
                table_id = table.get('id', f'no-id-{i}')
                logger.info(f"Table {i}: ID = {table_id}")
            
            # Try multiple table selectors
            fixtures_table = None
            table_selectors = [
                'table[id*="sched"]',  # Tables with 'sched' in ID
                'table[id*="schedule"]',  # Tables with 'schedule' in ID  
                'table.stats_table',  # Tables with stats_table class
                'table'  # Any table as fallback
            ]
            
            for selector in table_selectors:
                tables = soup.select(selector)
                if tables:
                    fixtures_table = tables[0]
                    logger.info(f"Using table found with selector: {selector}")
                    break
            
            if not fixtures_table:
                logger.error("Could not find any fixtures table")
                return []
            
            fixtures = []
            rows = fixtures_table.find_all('tr')
            logger.info(f"Found {len(rows)} rows in fixtures table")
            
            # Skip header and process data rows
            for row_idx, row in enumerate(rows[1:]):  # Skip header
                cells = row.find_all(['td', 'th'])
                
                if len(cells) < 5:  # Need at least date, home, away, score cells
                    continue
                
                try:
                    # Debug: Log first few cells to understand structure
                    if row_idx < 3:
                        cell_texts = [cell.get_text(strip=True)[:20] for cell in cells[:6]]
                        logger.info(f"Row {row_idx} cells: {cell_texts}")
                    
                    # Extract match info - adjust indices based on actual table structure
                    match_date = ""
                    home_team = ""
                    away_team = ""
                    match_url = ""
                    
                    # Try to find date (usually in first few columns)
                    for i in range(min(3, len(cells))):
                        cell_text = cells[i].get_text(strip=True)
                        if '2023' in cell_text or '2024' in cell_text:
                            match_date = cell_text
                            break
                    
                    # Try to find team names and match links
                    for i, cell in enumerate(cells):
                        cell_text = cell.get_text(strip=True)
                        
                        # Look for score cell with match link
                        links = cell.find_all('a')
                        for link in links:
                            href = link.get('href', '')
                            if '/matches/' in href:  # FBref match URLs contain '/matches/'
                                match_url = f"https://fbref.com{href}"
                                
                                # Try to extract teams from surrounding cells
                                if i >= 2:
                                    home_team = cells[i-2].get_text(strip=True)
                                if i >= 1:
                                    away_team = cells[i+1].get_text(strip=True) if i+1 < len(cells) else ""
                                
                                break
                        
                        if match_url:
                            break
                    
                    # Alternative: Look for team names in specific patterns
                    if not home_team or not away_team:
                        for i, cell in enumerate(cells):
                            text = cell.get_text(strip=True)
                            # Common team names to identify
                            if any(team in text for team in ['Arsenal', 'Liverpool', 'Chelsea', 'Manchester', 'City', 'United', 'Tottenham']):
                                if not home_team:
                                    home_team = text
                                elif not away_team and text != home_team:
                                    away_team = text
                    
                    if home_team and away_team and match_url:
                        fixture = SeasonFixture(
                            season=season,
                            match_date=match_date or f"2023-{row_idx+1:02d}-01",  # Fallback date
                            home_team=home_team,
                            away_team=away_team,
                            match_url=match_url
                        )
                        fixtures.append(fixture)
                        
                        if len(fixtures) <= 3:  # Log first few successful extractions
                            logger.info(f"Extracted fixture: {home_team} vs {away_team} - {match_url}")
                        
                except Exception as e:
                    logger.warning(f"Error parsing fixture row {row_idx}: {e}")
                    continue
            
            logger.info(f"Successfully extracted {len(fixtures)} fixtures for season {season}")
            return fixtures
            
        except Exception as e:
            logger.error(f"Error extracting fixtures for season {season}: {e}")
            return []

class TeamMatchData(BaseModel):
    match_date: str
    season: str
    home_team: str
    away_team: str
    team_name: str
    is_home: bool
    match_url: str
    team_score: int = 0
    opponent_score: int = 0
    possession: float = 0.0
    shots: int = 0
    shots_on_target: int = 0
    passes_completed: int = 0
    passes_attempted: int = 0

class PlayerMatchData(BaseModel):
    match_date: str
    season: str
    home_team: str
    away_team: str
    team_name: str
    player_name: str
    match_url: str
    minutes_played: int = 0
    goals: int = 0
    assists: int = 0
    shots: int = 0

# Global scraper instance and active jobs tracking
scraper = FBrefScraper()
active_scraping_jobs: Dict[str, ScrapingStatus] = {}

# API Routes
@api_router.get("/")
async def root():
    return {"message": "FBref Match Report Scraper API"}

@api_router.post("/scrape-season/{season}")
async def start_scraping(season: str, background_tasks: BackgroundTasks):
    """Start scraping a season's match reports"""
    try:
        # Create scraping status
        status = ScrapingStatus(
            status="running",
            request_type="single_season",
            seasons=[season],
            current_season=season,
            total_seasons=1,
            current_match=f"Starting scrape for season {season}"
        )
        
        # Save status to database
        await db.scraping_status.insert_one(status.dict())
        
        # Start background scraping task
        background_tasks.add_task(scrape_season_background, season, status.id)
        
        return {"message": f"Started scraping season {season}", "status_id": status.id}
        
    except Exception as e:
        logger.error(f"Error starting scrape: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def scrape_real_match_data_playwright(fixture: SeasonFixture) -> Optional[MatchData]:
    """Scrape a single match report using Playwright"""
    try:
        logger.info(f"Scraping match: {fixture.match_url}")
        
        # Navigate to match page
        await scraper.page.goto(fixture.match_url, wait_until='networkidle')
        await scraper.page.wait_for_selector('div.scorebox', timeout=30000)
        
        # Get page content and parse with BeautifulSoup
        content = await scraper.page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Extract metadata
        metadata = scraper.extract_match_metadata(soup)
        
        if not metadata.get("home_team") or not metadata.get("away_team"):
            logger.warning(f"Could not extract team names from {fixture.match_url}")
            return None
        
        # Extract team stats
        home_stats = scraper.extract_team_stats(soup, metadata["home_team"])
        away_stats = scraper.extract_team_stats(soup, metadata["away_team"])
        
        # Create MatchData object
        match_data = MatchData(
            season=fixture.season,
            match_url=fixture.match_url,
            home_team=metadata.get("home_team", ""),
            away_team=metadata.get("away_team", ""),
            home_score=metadata.get("home_score", 0),
            away_score=metadata.get("away_score", 0),
            match_date=metadata.get("match_date", ""),
            stadium=metadata.get("stadium", ""),
            referee=metadata.get("referee", ""),
            assistant_referees=metadata.get("assistant_referees", []),
            fourth_official=metadata.get("fourth_official", ""),
            var_referee=metadata.get("var_referee", ""),
            
            # Home team stats
            home_possession=home_stats.get("possession", 0.0),
            home_shots=home_stats.get("shots", 0),
            home_shots_on_target=home_stats.get("shots_on_target", 0),
            home_expected_goals=home_stats.get("expected_goals", 0.0),
            home_fouls_committed=home_stats.get("fouls_committed", 0),
            home_yellow_cards=home_stats.get("yellow_cards", 0),
            home_red_cards=home_stats.get("red_cards", 0),
            
            # Away team stats
            away_possession=away_stats.get("possession", 0.0),
            away_shots=away_stats.get("shots", 0),
            away_shots_on_target=away_stats.get("shots_on_target", 0),
            away_expected_goals=away_stats.get("expected_goals", 0.0),
            away_fouls_committed=away_stats.get("fouls_committed", 0),
            away_yellow_cards=away_stats.get("yellow_cards", 0),
            away_red_cards=away_stats.get("red_cards", 0),
        )
        
        return match_data
        
    except Exception as e:
        logger.error(f"Error scraping match {fixture.match_url}: {e}")
        return None

async def scrape_season_background(season: str, status_id: str):
    """Background task to scrape all matches in a season"""
    try:
        # Setup Playwright browser
        if not await scraper.setup_browser():
            await db.scraping_status.update_one(
                {"id": status_id},
                {"$set": {"status": "failed", "errors": ["Failed to setup Chrome driver"]}}
            )
            return
        
        # Get real fixtures from FBref
        fixtures = await scraper.extract_season_fixtures(season)
        
        if not fixtures:
            await db.scraping_status.update_one(
                {"id": status_id},
                {"$set": {"status": "failed", "errors": ["No fixtures found"]}}
            )
            return
        
        # Update total matches
        await db.scraping_status.update_one(
            {"id": status_id},
            {"$set": {
                "total_matches": len(fixtures),
                "fixtures_found": len(fixtures),
                "current_season": season,
                "seasons": [season],
                "total_seasons": 1
            }}
        )
        
        # Scrape each match
        scraped_count = 0
        errors = []
        
        for fixture in fixtures:
            try:
                # Update current match
                await db.scraping_status.update_one(
                    {"id": status_id},
                    {"$set": {"current_match": fixture.match_url}}
                )
                
                # Scrape match
                match_data = await scrape_real_match_data_playwright(fixture)
                
                if match_data:
                    # Save to database
                    await db.team_matches.insert_one(match_data.dict())
                    scraped_count += 1
                    
                    # Update progress
                    await db.scraping_status.update_one(
                        {"id": status_id},
                        {"$set": {
                            "matches_scraped": scraped_count,
                            "completed_seasons": 1 if scraped_count == len(fixtures) else 0
                        }}
                    )
                else:
                    errors.append(f"Failed to scrape {fixture.match_url}")
                
                # Small delay between requests
                time.sleep(2)
                
            except Exception as e:
                error_msg = f"Error scraping {fixture.match_url}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        # Mark as completed
        await db.scraping_status.update_one(
            {"id": status_id},
            {"$set": {
                "status": "completed",
                "completed_at": datetime.utcnow(),
                "errors": errors,
                "completed_seasons": 1
            }}
        )
        
        logger.info(f"Completed scraping season {season}. Scraped {scraped_count} matches with {len(errors)} errors")
        
    except Exception as e:
        logger.error(f"Background scraping error: {e}")
        await db.scraping_status.update_one(
            {"id": status_id},
            {"$set": {"status": "failed", "errors": [str(e)]}}
        )
    finally:
        scraper.cleanup()

@api_router.get("/scraping-status/{status_id}")
async def get_scraping_status(status_id: str):
    """Get scraping status by ID"""
    status = await db.scraping_status.find_one({"id": status_id}, {"_id": 0})
    if not status:
        raise HTTPException(status_code=404, detail="Status not found")
    return status

@api_router.get("/matches")
async def get_matches(season: Optional[str] = None, team: Optional[str] = None):
    """Get scraped matches with optional filtering"""
    query = {}
    
    if season:
        query["season"] = season
    
    if team:
        query["team_name"] = {"$regex": team, "$options": "i"}
    
    matches = await db.team_matches.find(query, {"_id": 0}).to_list(1000)
    return matches

@api_router.post("/export-csv")
async def export_csv(filters: FilterRequest):
    """Export filtered match data as CSV"""
    try:
        # Build query
        query = {}
        if filters.season:
            query["season"] = filters.season
        
        if filters.teams:
            team_conditions = []
            for team in filters.teams:
                team_conditions.append({"team_name": {"$regex": team, "$options": "i"}})
            if team_conditions:
                query["$or"] = team_conditions
        
        if filters.referee:
            query["referee"] = {"$regex": filters.referee, "$options": "i"}
        
        # Get matches
        matches = await db.team_matches.find(query, {"_id": 0}).to_list(10000)
        
        if not matches:
            raise HTTPException(status_code=404, detail="No matches found with given filters")
        
        # Convert to DataFrame
        df = pd.DataFrame([{k: v for k, v in match.items() if k != "_id"} for match in matches])
        
        # Create CSV
        output = io.StringIO()
        df.to_csv(output, index=False)
        csv_data = output.getvalue()
        output.close()
        
        # Return as streaming response
        def generate():
            yield csv_data
        
        return StreamingResponse(
            generate(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=fbref_team_matches.csv"}
        )
        
    except Exception as e:
        logger.error(f"Export error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/seasons")
async def get_available_seasons():
    """Get list of available seasons"""
    try:
        seasons = await db.team_matches.distinct("season")
        return {"seasons": sorted(seasons, reverse=True)}
    except Exception as e:
        logger.error(f"Error getting seasons: {e}")
        return {"seasons": ["2023-24"]}  # Default fallback

@api_router.get("/teams")
async def get_available_teams():
    """Get list of available teams"""
    try:
        teams = await db.team_matches.distinct("team_name")
        return {"teams": sorted(teams)}
    except Exception as e:
        logger.error(f"Error getting teams: {e}")
        return {"teams": []}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
    scraper.cleanup()
