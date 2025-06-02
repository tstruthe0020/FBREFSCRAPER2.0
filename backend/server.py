from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
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
from webdriver_manager.core.os_manager import ChromeType
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

# Enhanced Pydantic Models
class SeasonFixture(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    season: str
    match_date: str
    home_team: str
    away_team: str
    match_url: str
    scraped_at: datetime = Field(default_factory=datetime.utcnow)

class TeamMatchData(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    match_date: str
    season: str
    home_team: str
    away_team: str
    team_name: str  # The team we're analyzing
    is_home: bool   # True if team_name is playing at home
    
    # Match result
    team_score: int = 0
    opponent_score: int = 0
    
    # Stadium and officials
    stadium: str = ""
    referee: str = ""
    assistant_referees: List[str] = []
    fourth_official: str = ""
    var_referee: str = ""
    
    # Summary Stats
    possession: float = 0.0
    shots: int = 0
    shots_on_target: int = 0
    expected_goals: float = 0.0
    corners: int = 0
    crosses: int = 0
    touches: int = 0
    fouls_committed: int = 0
    fouls_drawn: int = 0
    yellow_cards: int = 0
    red_cards: int = 0
    offsides: int = 0
    
    # Advanced Shooting Stats
    shots_penalty_area: int = 0
    shots_outside_penalty_area: int = 0
    shots_free_kicks: int = 0
    shots_foot: int = 0
    shots_head: int = 0
    goals_penalty: int = 0
    goals_free_kicks: int = 0
    
    # Passing Stats
    passes_completed: int = 0
    passes_attempted: int = 0
    passing_accuracy: float = 0.0
    short_passes_completed: int = 0
    short_passes_attempted: int = 0
    medium_passes_completed: int = 0
    medium_passes_attempted: int = 0
    long_passes_completed: int = 0
    long_passes_attempted: int = 0
    progressive_passes: int = 0
    
    # Advanced Passing Stats
    passes_key: int = 0  # Key passes leading to shots
    passes_final_third: int = 0  # Passes into final third
    passes_penalty_area: int = 0  # Passes into penalty area
    passes_under_pressure: int = 0  # Passes under pressure
    passes_switches: int = 0  # Switch passes
    passes_live: int = 0  # Live ball passes
    passes_dead: int = 0  # Dead ball passes
    passes_free_kicks: int = 0  # Free kick passes
    passes_through_balls: int = 0  # Through balls
    passes_corners: int = 0  # Corner kicks taken
    
    # Defensive Stats
    tackles: int = 0
    tackles_won: int = 0
    tackles_def_3rd: int = 0
    tackles_mid_3rd: int = 0
    tackles_att_3rd: int = 0
    interceptions: int = 0
    blocks: int = 0
    clearances: int = 0
    aerials_won: int = 0
    aerials_lost: int = 0
    
    # Pressure Stats
    pressures: int = 0  # Times applying pressure
    pressures_successful: int = 0  # Successful pressures
    pressures_def_3rd: int = 0  # Pressures in defensive third
    pressures_mid_3rd: int = 0  # Pressures in middle third
    pressures_att_3rd: int = 0  # Pressures in attacking third
    
    # Goalkeeper Stats (if applicable)
    saves: int = 0
    save_percentage: float = 0.0
    goals_against: int = 0
    clean_sheet: bool = False
    expected_goals_against: float = 0.0
    
    # Possession Stats
    dribbles_completed: int = 0
    dribbles_attempted: int = 0
    dribble_success_rate: float = 0.0
    progressive_carries: int = 0
    carries_into_final_third: int = 0
    carries_into_penalty_area: int = 0
    
    # Advanced Possession Stats
    carries_total_distance: float = 0.0  # Total carrying distance
    carries_progressive_distance: float = 0.0  # Progressive carrying distance
    touches_def_3rd: int = 0  # Touches in defensive third
    touches_mid_3rd: int = 0  # Touches in middle third
    touches_att_3rd: int = 0  # Touches in attacking third
    touches_penalty_area: int = 0  # Touches in penalty area
    
    # Set Piece Stats
    corners_taken: int = 0
    free_kicks_taken: int = 0
    penalties_taken: int = 0
    penalties_scored: int = 0
    penalties_missed: int = 0
    
    # Miscellaneous Stats
    goal_kicks: int = 0
    throw_ins: int = 0
    long_balls: int = 0
    sca: int = 0  # Shot Creating Actions
    gca: int = 0  # Goal Creating Actions
    recoveries: int = 0  # Ball recoveries
    own_goals: int = 0  # Own goals
    
    # Opponent's key stats for context
    opponent_possession: float = 0.0
    opponent_shots: int = 0
    opponent_shots_on_target: int = 0
    opponent_expected_goals: float = 0.0
    
    match_url: str = ""
    scraped_at: datetime = Field(default_factory=datetime.utcnow)

class PlayerMatchData(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    match_date: str
    season: str
    home_team: str
    away_team: str
    team_name: str
    player_name: str
    player_number: int = 0
    nation: str = ""
    position: str = ""
    age: str = ""
    
    # Playing time
    minutes_played: int = 0
    started: bool = False
    
    # Performance
    goals: int = 0
    assists: int = 0
    penalty_goals: int = 0
    penalty_attempts: int = 0
    shots: int = 0
    shots_on_target: int = 0
    expected_goals: float = 0.0
    expected_assists: float = 0.0
    
    # Advanced Shooting Stats
    shots_penalty_area: int = 0
    shots_outside_penalty_area: int = 0
    shots_left_foot: int = 0
    shots_right_foot: int = 0
    shots_head: int = 0
    shots_free_kicks: int = 0
    goals_per_shot: float = 0.0
    
    # Passing
    passes_completed: int = 0
    passes_attempted: int = 0
    passing_accuracy: float = 0.0
    progressive_passes: int = 0
    
    # Advanced Passing Stats
    passes_short: int = 0
    passes_medium: int = 0
    passes_long: int = 0
    passes_key: int = 0  # Key passes leading to shots
    passes_final_third: int = 0  # Passes into final third
    passes_penalty_area: int = 0  # Passes into penalty area
    passes_under_pressure: int = 0  # Passes under pressure
    pass_targets: int = 0  # Times targeted for passes
    pass_targets_completed: int = 0  # Successful pass receptions
    
    # Defense
    tackles: int = 0
    interceptions: int = 0
    blocks: int = 0
    clearances: int = 0
    aerials_won: int = 0
    aerials_lost: int = 0
    
    # Advanced Defense Stats
    tackles_def_3rd: int = 0
    tackles_mid_3rd: int = 0
    tackles_att_3rd: int = 0
    tackles_dribbled_past: int = 0
    pressures: int = 0  # Pressure applications
    pressures_successful: int = 0  # Successful pressures
    errors_leading_to_shot: int = 0  # Errors leading to opponent shot
    
    # Possession
    touches: int = 0
    dribbles_completed: int = 0
    dribbles_attempted: int = 0
    carries: int = 0
    progressive_carries: int = 0
    
    # Advanced Possession Stats
    touches_def_3rd: int = 0  # Touches in defensive third
    touches_mid_3rd: int = 0  # Touches in middle third
    touches_att_3rd: int = 0  # Touches in attacking third
    touches_penalty_area: int = 0  # Touches in penalty area
    dribbles_take_on: int = 0  # Take-on attempts
    carries_distance: float = 0.0  # Total carry distance
    carries_progressive_distance: float = 0.0  # Progressive carry distance
    miscontrols: int = 0  # Miscontrols
    dispossessed: int = 0  # Times dispossessed
    
    # Discipline
    yellow_cards: int = 0
    red_cards: int = 0
    fouls_committed: int = 0
    fouls_drawn: int = 0
    
    # Advanced metrics
    sca: int = 0  # Shot Creating Actions
    gca: int = 0  # Goal Creating Actions
    
    # Goalkeeper Specific Stats (when applicable)
    saves_penalty_area: int = 0
    saves_free_kicks: int = 0
    saves_corners: int = 0
    saves_crosses: int = 0
    punches: int = 0
    keeper_sweeper_actions: int = 0
    passes_goal_kicks: int = 0
    passes_launches_pct: float = 0.0  # Percentage of long launches
    pass_length_avg: float = 0.0  # Average pass length
    
    match_url: str = ""
    scraped_at: datetime = Field(default_factory=datetime.utcnow)

class MultiSeasonScrapeRequest(BaseModel):
    seasons: List[str]  # e.g., ["2023-24", "2022-23", "2021-22"]
    target_team: Optional[str] = None  # If specified, only scrape this team's matches

class ScrapingStatus(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: str  # "running", "completed", "failed"
    request_type: str = "single_season"  # "single_season", "multi_season", "team_focused"
    seasons: List[str] = []
    target_team: Optional[str] = None
    
    # Progress tracking
    total_seasons: int = 0
    completed_seasons: int = 0
    current_season: str = ""
    fixtures_found: int = 0
    matches_scraped: int = 0
    total_matches: int = 0
    current_match: str = ""
    
    errors: List[str] = []
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

class FilterRequest(BaseModel):
    seasons: Optional[List[str]] = []
    teams: Optional[List[str]] = []
    referee: Optional[str] = None

class FBrefScraperV2:
    def __init__(self):
        self.driver = None
        self.wait = None
        
    def setup_driver(self):
        """Setup Chrome driver with headless options for ARM64"""
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-software-rasterizer")
            chrome_options.add_argument("--disable-background-timer-throttling")
            chrome_options.add_argument("--disable-backgrounding-occluded-windows")
            chrome_options.add_argument("--disable-renderer-backgrounding")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36")
            
            # Try to use Chrome directly without specifying binary location
            self.driver = webdriver.Chrome(options=chrome_options)
            self.wait = WebDriverWait(self.driver, 15)
            logger.info("Chrome driver setup successful using default Chrome")
            return True
        except Exception as e:
            logger.error(f"Failed to setup Chrome driver: {e}")
            try:
                # Fallback to use Chromium
                chrome_options = Options()
                chrome_options.add_argument("--headless")
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                chrome_options.add_argument("--disable-gpu")
                chrome_options.add_argument("--disable-software-rasterizer")
                chrome_options.add_argument("--window-size=1920,1080")
                chrome_options.binary_location = "/usr/bin/chromium"
                
                self.driver = webdriver.Chrome(options=chrome_options)
                self.wait = WebDriverWait(self.driver, 15)
                logger.info("Chrome driver setup successful with Chromium")
                return True
            except Exception as e2:
                logger.error(f"Fallback Chrome driver setup also failed: {e2}")
                return False
    
    def get_season_fixtures_url(self, season: str) -> str:
        """Get the fixtures URL for a specific season"""
        if season == "2024-25":
            return "https://fbref.com/en/comps/9/schedule/Premier-League-Scores-and-Fixtures"
        else:
            return f"https://fbref.com/en/comps/9/{season}/schedule/Premier-League-Scores-and-Fixtures"
    
    def extract_season_fixtures(self, season: str) -> List[SeasonFixture]:
        """Extract all fixtures from a season (both completed and upcoming)"""
        try:
            fixtures_url = self.get_season_fixtures_url(season)
            logger.info(f"Fetching fixtures from: {fixtures_url}")
            
            self.driver.get(fixtures_url)
            time.sleep(5)
            
            fixtures = []
            
            # Find fixture table
            tables = self.driver.find_elements(By.TAG_NAME, "table")
            fixture_table = None
            
            for table in tables:
                table_id = table.get_attribute("id") or ""
                if "sched" in table_id.lower() or "fixture" in table_id.lower():
                    fixture_table = table
                    break
            
            if not fixture_table:
                # Try to find the main fixtures table by looking for rows with match data
                for table in tables:
                    rows = table.find_elements(By.TAG_NAME, "tr")
                    if len(rows) > 10:  # Likely the fixtures table
                        fixture_table = table
                        break
            
            if fixture_table:
                rows = fixture_table.find_elements(By.TAG_NAME, "tr")
                
                for row in rows[1:]:  # Skip header
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 6:  # Minimum columns for a valid fixture
                        try:
                            # Extract date, teams, and match URL
                            date_cell = cells[1] if len(cells) > 1 else cells[0]
                            match_date = date_cell.text.strip()
                            
                            # Find team names and match links
                            links = row.find_elements(By.TAG_NAME, "a")
                            match_url = None
                            teams = []
                            
                            for link in links:
                                href = link.get_attribute("href")
                                text = link.text.strip()
                                
                                # Check if this is a match URL
                                if href and "/en/matches/" in href and len(href.split("/")) > 5:
                                    match_url = href
                                    
                                # Collect team names from links
                                if href and "/en/squads/" in href and text:
                                    teams.append(text)
                            
                            # If we didn't get teams from links, try to extract from cells
                            if len(teams) < 2:
                                for cell in cells:
                                    cell_text = cell.text.strip()
                                    if cell_text and len(cell_text) > 2:
                                        # This could be a team name
                                        if cell_text not in ['vs', 'v', '-'] and not cell_text.isdigit():
                                            teams.append(cell_text)
                            
                            if len(teams) >= 2 and match_url:
                                fixture = SeasonFixture(
                                    season=season,
                                    match_date=match_date,
                                    home_team=teams[0],
                                    away_team=teams[1],
                                    match_url=match_url
                                )
                                fixtures.append(fixture)
                                
                        except Exception as e:
                            logger.warning(f"Error parsing fixture row: {e}")
                            continue
            
            logger.info(f"Found {len(fixtures)} fixtures for season {season}")
            return fixtures
            
        except Exception as e:
            logger.error(f"Error extracting fixtures for season {season}: {e}")
            return []
    
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
            # Extract team names and score from the scorebox
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
    
    def extract_comprehensive_team_stats(self, soup: BeautifulSoup, team_name: str) -> Dict[str, Any]:
        """Extract comprehensive statistics for a specific team from all available tables"""
        stats = {}
        
        try:
            # Normalize team name for table IDs (replace spaces and special chars)
            team_id = team_name.replace(" ", "_").replace("'", "").replace("-", "_")
            
            # Define the statistics tables we want to extract
            stat_tables = {
                'summary': f'stats_summary_{team_id}',
                'passing': f'stats_passing_{team_id}',
                'passing_types': f'stats_passing_types_{team_id}',
                'defense': f'stats_defense_{team_id}',
                'possession': f'stats_possession_{team_id}',
                'misc': f'stats_misc_{team_id}',
                'keeper': f'stats_keeper_{team_id}'
            }
            
            # Extract from each statistics table
            for stat_type, table_id in stat_tables.items():
                table = soup.find("table", {"id": table_id})
                if table:
                    self._extract_team_stats_from_table(table, stats, stat_type)
            
            # Also check for alternate naming conventions
            alternate_team_id = team_name.replace(" ", "-").replace("'", "")
            for stat_type in ['summary', 'passing', 'defense', 'misc']:
                alt_table_id = f'stats_{stat_type}_{alternate_team_id}'
                table = soup.find("table", {"id": alt_table_id})
                if table:
                    self._extract_team_stats_from_table(table, stats, stat_type)
            
            # Extract from general team stats if specific tables not found
            if not stats:
                self._extract_from_general_tables(soup, team_name, stats)
                
        except Exception as e:
            logger.error(f"Error extracting comprehensive stats for {team_name}: {e}")
        
        return stats
    
    def _extract_team_stats_from_table(self, table, stats: Dict, stat_type: str):
        """Extract statistics from a specific table"""
        try:
            # Find the team's row in the table (usually the last row with data)
            rows = table.find_all("tr")
            team_row = None
            
            for row in rows:
                if row.find("th") and "Total" in row.get_text():
                    team_row = row
                    break
            
            if not team_row and len(rows) > 1:
                # Take the last data row if no "Total" row found
                team_row = rows[-1]
            
            if team_row:
                cells = team_row.find_all(["td", "th"])
                self._parse_team_row_by_stat_type(cells, stats, stat_type)
                
        except Exception as e:
            logger.error(f"Error extracting from {stat_type} table: {e}")
    
    def _parse_team_row_by_stat_type(self, cells, stats: Dict, stat_type: str):
        """Parse team row data based on statistics type"""
        try:
            if stat_type == 'summary':
                # Summary stats: possession, shots, fouls, cards, etc.
                for cell in cells:
                    data_stat = cell.get("data-stat", "")
                    value = cell.get_text().strip()
                    
                    if data_stat == "possession":
                        stats["possession"] = self._parse_percentage(value)
                    elif data_stat == "shots_total":
                        stats["shots"] = self._parse_int(value)
                    elif data_stat == "shots_on_target":
                        stats["shots_on_target"] = self._parse_int(value)
                    elif data_stat == "xg":
                        stats["expected_goals"] = self._parse_float(value)
                    elif data_stat == "corners":
                        stats["corners"] = self._parse_int(value)
                    elif data_stat == "crosses":
                        stats["crosses"] = self._parse_int(value)
                    elif data_stat == "touches":
                        stats["touches"] = self._parse_int(value)
                    elif data_stat == "fouls":
                        stats["fouls_committed"] = self._parse_int(value)
                    elif data_stat == "cards_yellow":
                        stats["yellow_cards"] = self._parse_int(value)
                    elif data_stat == "cards_red":
                        stats["red_cards"] = self._parse_int(value)
                    elif data_stat == "offsides":
                        stats["offsides"] = self._parse_int(value)
                    # Advanced shooting stats
                    elif data_stat == "shots_penalty_area":
                        stats["shots_penalty_area"] = self._parse_int(value)
                    elif data_stat == "shots_outside_penalty_area":
                        stats["shots_outside_penalty_area"] = self._parse_int(value)
                    elif data_stat == "shots_free_kicks":
                        stats["shots_free_kicks"] = self._parse_int(value)
                    elif data_stat == "shots_foot":
                        stats["shots_foot"] = self._parse_int(value)
                    elif data_stat == "shots_head":
                        stats["shots_head"] = self._parse_int(value)
                    elif data_stat == "goals_penalty":
                        stats["goals_penalty"] = self._parse_int(value)
                    elif data_stat == "goals_free_kicks":
                        stats["goals_free_kicks"] = self._parse_int(value)
            
            elif stat_type == 'passing':
                # Passing stats: completed, attempted, accuracy, progressive passes
                for cell in cells:
                    data_stat = cell.get("data-stat", "")
                    value = cell.get_text().strip()
                    
                    if data_stat == "passes_completed":
                        stats["passes_completed"] = self._parse_int(value)
                    elif data_stat == "passes":
                        stats["passes_attempted"] = self._parse_int(value)
                    elif data_stat == "passes_pct":
                        stats["passing_accuracy"] = self._parse_float(value)
                    elif data_stat == "passes_progressive":
                        stats["progressive_passes"] = self._parse_int(value)
                    elif data_stat == "passes_completed_short":
                        stats["short_passes_completed"] = self._parse_int(value)
                    elif data_stat == "passes_short":
                        stats["short_passes_attempted"] = self._parse_int(value)
                    elif data_stat == "passes_completed_medium":
                        stats["medium_passes_completed"] = self._parse_int(value)
                    elif data_stat == "passes_medium":
                        stats["medium_passes_attempted"] = self._parse_int(value)
                    elif data_stat == "passes_completed_long":
                        stats["long_passes_completed"] = self._parse_int(value)
                    elif data_stat == "passes_long":
                        stats["long_passes_attempted"] = self._parse_int(value)
                    # Advanced passing stats
                    elif data_stat == "passes_key":
                        stats["passes_key"] = self._parse_int(value)
                    elif data_stat == "passes_final_third":
                        stats["passes_final_third"] = self._parse_int(value)
                    elif data_stat == "passes_penalty_area":
                        stats["passes_penalty_area"] = self._parse_int(value)
                    elif data_stat == "passes_under_pressure":
                        stats["passes_under_pressure"] = self._parse_int(value)
                    elif data_stat == "passes_switches":
                        stats["passes_switches"] = self._parse_int(value)
                    elif data_stat == "passes_live":
                        stats["passes_live"] = self._parse_int(value)
                    elif data_stat == "passes_dead":
                        stats["passes_dead"] = self._parse_int(value)
                    elif data_stat == "passes_free_kicks":
                        stats["passes_free_kicks"] = self._parse_int(value)
                    elif data_stat == "passes_through_balls":
                        stats["passes_through_balls"] = self._parse_int(value)
                    elif data_stat == "passes_corners":
                        stats["passes_corners"] = self._parse_int(value)
            
            elif stat_type == 'defense':
                # Defensive stats: tackles, interceptions, blocks, clearances
                for cell in cells:
                    data_stat = cell.get("data-stat", "")
                    value = cell.get_text().strip()
                    
                    if data_stat == "tackles":
                        stats["tackles"] = self._parse_int(value)
                    elif data_stat == "tackles_won":
                        stats["tackles_won"] = self._parse_int(value)
                    elif data_stat == "tackles_def_3rd":
                        stats["tackles_def_3rd"] = self._parse_int(value)
                    elif data_stat == "tackles_mid_3rd":
                        stats["tackles_mid_3rd"] = self._parse_int(value)
                    elif data_stat == "tackles_att_3rd":
                        stats["tackles_att_3rd"] = self._parse_int(value)
                    elif data_stat == "interceptions":
                        stats["interceptions"] = self._parse_int(value)
                    elif data_stat == "blocks":
                        stats["blocks"] = self._parse_int(value)
                    elif data_stat == "clearances":
                        stats["clearances"] = self._parse_int(value)
                    elif data_stat == "aerials_won":
                        stats["aerials_won"] = self._parse_int(value)
                    elif data_stat == "aerials_lost":
                        stats["aerials_lost"] = self._parse_int(value)
                    # Pressure stats
                    elif data_stat == "pressures":
                        stats["pressures"] = self._parse_int(value)
                    elif data_stat == "pressures_successful":
                        stats["pressures_successful"] = self._parse_int(value)
                    elif data_stat == "pressures_def_3rd":
                        stats["pressures_def_3rd"] = self._parse_int(value)
                    elif data_stat == "pressures_mid_3rd":
                        stats["pressures_mid_3rd"] = self._parse_int(value)
                    elif data_stat == "pressures_att_3rd":
                        stats["pressures_att_3rd"] = self._parse_int(value)
            
            elif stat_type == 'possession':
                # Possession stats: dribbles, carries, progressive actions
                for cell in cells:
                    data_stat = cell.get("data-stat", "")
                    value = cell.get_text().strip()
                    
                    if data_stat == "dribbles_completed":
                        stats["dribbles_completed"] = self._parse_int(value)
                    elif data_stat == "dribbles":
                        stats["dribbles_attempted"] = self._parse_int(value)
                    elif data_stat == "dribbles_completed_pct":
                        stats["dribble_success_rate"] = self._parse_float(value)
                    elif data_stat == "carries_progressive":
                        stats["progressive_carries"] = self._parse_int(value)
                    elif data_stat == "carries_final_third":
                        stats["carries_into_final_third"] = self._parse_int(value)
                    elif data_stat == "carries_penalty_area":
                        stats["carries_into_penalty_area"] = self._parse_int(value)
                    # Advanced possession stats
                    elif data_stat == "carries_total_distance":
                        stats["carries_total_distance"] = self._parse_float(value)
                    elif data_stat == "carries_progressive_distance":
                        stats["carries_progressive_distance"] = self._parse_float(value)
                    elif data_stat == "touches_def_3rd":
                        stats["touches_def_3rd"] = self._parse_int(value)
                    elif data_stat == "touches_mid_3rd":
                        stats["touches_mid_3rd"] = self._parse_int(value)
                    elif data_stat == "touches_att_3rd":
                        stats["touches_att_3rd"] = self._parse_int(value)
                    elif data_stat == "touches_penalty_area":
                        stats["touches_penalty_area"] = self._parse_int(value)
            
            elif stat_type == 'misc':
                # Miscellaneous stats: goal kicks, throw ins, long balls, SCA, GCA
                for cell in cells:
                    data_stat = cell.get("data-stat", "")
                    value = cell.get_text().strip()
                    
                    if data_stat == "goal_kicks":
                        stats["goal_kicks"] = self._parse_int(value)
                    elif data_stat == "throw_ins":
                        stats["throw_ins"] = self._parse_int(value)
                    elif data_stat == "long_balls":
                        stats["long_balls"] = self._parse_int(value)
                    elif data_stat == "sca":
                        stats["sca"] = self._parse_int(value)
                    elif data_stat == "gca":
                        stats["gca"] = self._parse_int(value)
                    # Set piece stats
                    elif data_stat == "corners_taken":
                        stats["corners_taken"] = self._parse_int(value)
                    elif data_stat == "free_kicks_taken":
                        stats["free_kicks_taken"] = self._parse_int(value)
                    elif data_stat == "penalties_taken":
                        stats["penalties_taken"] = self._parse_int(value)
                    elif data_stat == "penalties_scored":
                        stats["penalties_scored"] = self._parse_int(value)
                    elif data_stat == "penalties_missed":
                        stats["penalties_missed"] = self._parse_int(value)
                    # Miscellaneous additions
                    elif data_stat == "recoveries":
                        stats["recoveries"] = self._parse_int(value)
                    elif data_stat == "own_goals":
                        stats["own_goals"] = self._parse_int(value)
            
            elif stat_type == 'keeper':
                # Goalkeeper stats: saves, save percentage, goals against
                for cell in cells:
                    data_stat = cell.get("data-stat", "")
                    value = cell.get_text().strip()
                    
                    if data_stat == "saves":
                        stats["saves"] = self._parse_int(value)
                    elif data_stat == "save_pct":
                        stats["save_percentage"] = self._parse_float(value)
                    elif data_stat == "goals_against":
                        stats["goals_against"] = self._parse_int(value)
                    elif data_stat == "psxg":
                        stats["expected_goals_against"] = self._parse_float(value)
                        
        except Exception as e:
            logger.error(f"Error parsing {stat_type} row: {e}")
    
    def _extract_from_general_tables(self, soup: BeautifulSoup, team_name: str, stats: Dict):
        """Fallback method to extract stats from general tables when specific team tables aren't found"""
        try:
            # Look for any tables that contain team statistics
            for table in soup.find_all("table"):
                table_text = table.get_text().lower()
                
                if team_name.lower() in table_text:
                    # Try to extract basic stats from this table
                    for row in table.find_all("tr"):
                        if team_name.lower() in row.get_text().lower():
                            cells = row.find_all(["td", "th"])
                            for cell in cells:
                                data_stat = cell.get("data-stat", "")
                                value = cell.get_text().strip()
                                
                                # Extract basic stats
                                if data_stat == "possession":
                                    stats["possession"] = self._parse_percentage(value)
                                elif data_stat == "shots_total":
                                    stats["shots"] = self._parse_int(value)
                                elif data_stat == "shots_on_target":
                                    stats["shots_on_target"] = self._parse_int(value)
                                
        except Exception as e:
            logger.error(f"Error in fallback extraction for {team_name}: {e}")
    
    def _parse_int(self, value: str) -> int:
        """Safely parse integer value"""
        try:
            return int(value.replace(",", "").strip())
        except (ValueError, AttributeError):
            return 0
    
    def _parse_float(self, value: str) -> float:
        """Safely parse float value"""
        try:
            return float(value.replace(",", "").strip())
        except (ValueError, AttributeError):
            return 0.0
    
    def _parse_percentage(self, value: str) -> float:
        """Parse percentage value (remove % and convert to float)"""
        try:
            return float(value.replace("%", "").replace(",", "").strip())
        except (ValueError, AttributeError):
            return 0.0
    
    def extract_player_stats(self, soup: BeautifulSoup, team_name: str) -> List[Dict[str, Any]]:
        """Extract individual player statistics for a team"""
        players = []
        
        try:
            # Normalize team name for table IDs
            team_id = team_name.replace(" ", "_").replace("'", "").replace("-", "_")
            
            # Look for player statistics tables
            player_table_ids = [
                f'stats_summary_{team_id}',
                f'stats_passing_{team_id}',
                f'stats_defense_{team_id}',
                f'stats_possession_{team_id}',
                f'stats_misc_{team_id}'
            ]
            
            # Find the main player statistics table (usually summary)
            main_table = None
            for table_id in player_table_ids:
                table = soup.find("table", {"id": table_id})
                if table:
                    main_table = table
                    break
            
            if main_table:
                players = self._extract_players_from_table(main_table, team_name)
            else:
                # Fallback: look for any table containing player data for this team
                players = self._extract_players_fallback(soup, team_name)
                
        except Exception as e:
            logger.error(f"Error extracting player stats for {team_name}: {e}")
        
        return players
    
    def _extract_players_from_table(self, table, team_name: str) -> List[Dict[str, Any]]:
        """Extract player data from a statistics table"""
        players = []
        
        try:
            rows = table.find_all("tr")
            
            # Skip header rows and find player data rows
            for row in rows[1:]:  # Skip header
                cells = row.find_all(["td", "th"])
                if len(cells) < 5:  # Skip rows without enough data
                    continue
                
                player_data = self._parse_player_row(cells, team_name)
                if player_data and player_data.get("player_name"):
                    players.append(player_data)
                    
        except Exception as e:
            logger.error(f"Error extracting players from table for {team_name}: {e}")
        
        return players
    
    def _parse_player_row(self, cells, team_name: str) -> Dict[str, Any]:
        """Parse individual player row data"""
        player_data = {"team_name": team_name}
        
        try:
            for cell in cells:
                data_stat = cell.get("data-stat", "")
                value = cell.get_text().strip()
                
                # Basic player info
                if data_stat == "player":
                    player_data["player_name"] = value
                elif data_stat == "shirtnumber":
                    player_data["player_number"] = self._parse_int(value)
                elif data_stat == "nationality":
                    player_data["nation"] = value
                elif data_stat == "position":
                    player_data["position"] = value
                elif data_stat == "age":
                    player_data["age"] = value
                elif data_stat == "minutes":
                    player_data["minutes_played"] = self._parse_int(value)
                
                # Performance stats
                elif data_stat == "goals":
                    player_data["goals"] = self._parse_int(value)
                elif data_stat == "assists":
                    player_data["assists"] = self._parse_int(value)
                elif data_stat == "pens_made":
                    player_data["penalty_goals"] = self._parse_int(value)
                elif data_stat == "pens_att":
                    player_data["penalty_attempts"] = self._parse_int(value)
                elif data_stat == "shots_total":
                    player_data["shots"] = self._parse_int(value)
                elif data_stat == "shots_on_target":
                    player_data["shots_on_target"] = self._parse_int(value)
                elif data_stat == "xg":
                    player_data["expected_goals"] = self._parse_float(value)
                elif data_stat == "xg_assist":
                    player_data["expected_assists"] = self._parse_float(value)
                
                # Advanced shooting stats
                elif data_stat == "shots_penalty_area":
                    player_data["shots_penalty_area"] = self._parse_int(value)
                elif data_stat == "shots_outside_penalty_area":
                    player_data["shots_outside_penalty_area"] = self._parse_int(value)
                elif data_stat == "shots_left_foot":
                    player_data["shots_left_foot"] = self._parse_int(value)
                elif data_stat == "shots_right_foot":
                    player_data["shots_right_foot"] = self._parse_int(value)
                elif data_stat == "shots_head":
                    player_data["shots_head"] = self._parse_int(value)
                elif data_stat == "shots_free_kicks":
                    player_data["shots_free_kicks"] = self._parse_int(value)
                
                # Passing stats
                elif data_stat == "passes_completed":
                    player_data["passes_completed"] = self._parse_int(value)
                elif data_stat == "passes":
                    player_data["passes_attempted"] = self._parse_int(value)
                elif data_stat == "passes_pct":
                    player_data["passing_accuracy"] = self._parse_float(value)
                elif data_stat == "progressive_passes":
                    player_data["progressive_passes"] = self._parse_int(value)
                
                # Advanced passing stats
                elif data_stat == "passes_short":
                    player_data["passes_short"] = self._parse_int(value)
                elif data_stat == "passes_medium":
                    player_data["passes_medium"] = self._parse_int(value)
                elif data_stat == "passes_long":
                    player_data["passes_long"] = self._parse_int(value)
                elif data_stat == "passes_key":
                    player_data["passes_key"] = self._parse_int(value)
                elif data_stat == "passes_final_third":
                    player_data["passes_final_third"] = self._parse_int(value)
                elif data_stat == "passes_penalty_area":
                    player_data["passes_penalty_area"] = self._parse_int(value)
                elif data_stat == "passes_under_pressure":
                    player_data["passes_under_pressure"] = self._parse_int(value)
                elif data_stat == "pass_targets":
                    player_data["pass_targets"] = self._parse_int(value)
                elif data_stat == "pass_targets_completed":
                    player_data["pass_targets_completed"] = self._parse_int(value)
                
                # Defensive stats
                elif data_stat == "tackles":
                    player_data["tackles"] = self._parse_int(value)
                elif data_stat == "interceptions":
                    player_data["interceptions"] = self._parse_int(value)
                elif data_stat == "blocks":
                    player_data["blocks"] = self._parse_int(value)
                elif data_stat == "clearances":
                    player_data["clearances"] = self._parse_int(value)
                elif data_stat == "aerials_won":
                    player_data["aerials_won"] = self._parse_int(value)
                elif data_stat == "aerials_lost":
                    player_data["aerials_lost"] = self._parse_int(value)
                
                # Advanced defensive stats
                elif data_stat == "tackles_def_3rd":
                    player_data["tackles_def_3rd"] = self._parse_int(value)
                elif data_stat == "tackles_mid_3rd":
                    player_data["tackles_mid_3rd"] = self._parse_int(value)
                elif data_stat == "tackles_att_3rd":
                    player_data["tackles_att_3rd"] = self._parse_int(value)
                elif data_stat == "tackles_dribbled_past":
                    player_data["tackles_dribbled_past"] = self._parse_int(value)
                elif data_stat == "pressures":
                    player_data["pressures"] = self._parse_int(value)
                elif data_stat == "pressures_successful":
                    player_data["pressures_successful"] = self._parse_int(value)
                elif data_stat == "errors_leading_to_shot":
                    player_data["errors_leading_to_shot"] = self._parse_int(value)
                
                # Possession stats
                elif data_stat == "touches":
                    player_data["touches"] = self._parse_int(value)
                elif data_stat == "dribbles_completed":
                    player_data["dribbles_completed"] = self._parse_int(value)
                elif data_stat == "dribbles":
                    player_data["dribbles_attempted"] = self._parse_int(value)
                elif data_stat == "carries":
                    player_data["carries"] = self._parse_int(value)
                elif data_stat == "progressive_carries":
                    player_data["progressive_carries"] = self._parse_int(value)
                
                # Advanced possession stats
                elif data_stat == "touches_def_3rd":
                    player_data["touches_def_3rd"] = self._parse_int(value)
                elif data_stat == "touches_mid_3rd":
                    player_data["touches_mid_3rd"] = self._parse_int(value)
                elif data_stat == "touches_att_3rd":
                    player_data["touches_att_3rd"] = self._parse_int(value)
                elif data_stat == "touches_penalty_area":
                    player_data["touches_penalty_area"] = self._parse_int(value)
                elif data_stat == "dribbles_take_on":
                    player_data["dribbles_take_on"] = self._parse_int(value)
                elif data_stat == "carries_distance":
                    player_data["carries_distance"] = self._parse_float(value)
                elif data_stat == "carries_progressive_distance":
                    player_data["carries_progressive_distance"] = self._parse_float(value)
                elif data_stat == "miscontrols":
                    player_data["miscontrols"] = self._parse_int(value)
                elif data_stat == "dispossessed":
                    player_data["dispossessed"] = self._parse_int(value)
                
                # Discipline
                elif data_stat == "cards_yellow":
                    player_data["yellow_cards"] = self._parse_int(value)
                elif data_stat == "cards_red":
                    player_data["red_cards"] = self._parse_int(value)
                elif data_stat == "fouls":
                    player_data["fouls_committed"] = self._parse_int(value)
                elif data_stat == "fouled":
                    player_data["fouls_drawn"] = self._parse_int(value)
                
                # Advanced metrics
                elif data_stat == "sca":
                    player_data["sca"] = self._parse_int(value)
                elif data_stat == "gca":
                    player_data["gca"] = self._parse_int(value)
                
                # Goalkeeper specific stats
                elif data_stat == "saves_penalty_area":
                    player_data["saves_penalty_area"] = self._parse_int(value)
                elif data_stat == "saves_free_kicks":
                    player_data["saves_free_kicks"] = self._parse_int(value)
                elif data_stat == "saves_corners":
                    player_data["saves_corners"] = self._parse_int(value)
                elif data_stat == "saves_crosses":
                    player_data["saves_crosses"] = self._parse_int(value)
                elif data_stat == "punches":
                    player_data["punches"] = self._parse_int(value)
                elif data_stat == "keeper_sweeper_actions":
                    player_data["keeper_sweeper_actions"] = self._parse_int(value)
                elif data_stat == "passes_goal_kicks":
                    player_data["passes_goal_kicks"] = self._parse_int(value)
                elif data_stat == "passes_launches_pct":
                    player_data["passes_launches_pct"] = self._parse_float(value)
                elif data_stat == "pass_length_avg":
                    player_data["pass_length_avg"] = self._parse_float(value)
                    
        except Exception as e:
            logger.error(f"Error parsing player row: {e}")
        
        return player_data
    
    def _extract_players_fallback(self, soup: BeautifulSoup, team_name: str) -> List[Dict[str, Any]]:
        """Fallback method to extract player data when specific tables aren't found"""
        players = []
        
        try:
            # Look for any tables that might contain player data
            for table in soup.find_all("table"):
                if "player" in table.get_text().lower() and team_name.lower() in str(table):
                    players.extend(self._extract_players_from_table(table, team_name))
                    
        except Exception as e:
            logger.error(f"Error in player fallback extraction for {team_name}: {e}")
        
        return players
    
    def scrape_match_report(self, match_url: str, season: str, target_team: Optional[str] = None) -> List[TeamMatchData]:
        """Scrape a single match report and return comprehensive team-focused data with player stats"""
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
                return []
            
            home_team = metadata["home_team"]
            away_team = metadata["away_team"]
            
            # Extract comprehensive team stats
            home_stats = self.extract_comprehensive_team_stats(soup, home_team)
            away_stats = self.extract_comprehensive_team_stats(soup, away_team)
            
            # Extract player stats for both teams
            home_players = self.extract_player_stats(soup, home_team)
            away_players = self.extract_player_stats(soup, away_team)
            
            result = []
            
            # If target_team is specified, only return data for that team
            teams_to_process = []
            if target_team:
                if target_team.lower() == home_team.lower():
                    teams_to_process = [(home_team, True, home_stats, away_stats, home_players)]
                elif target_team.lower() == away_team.lower():
                    teams_to_process = [(away_team, False, away_stats, home_stats, away_players)]
            else:
                teams_to_process = [
                    (home_team, True, home_stats, away_stats, home_players),
                    (away_team, False, away_stats, home_stats, away_players)
                ]
            
            for team_name, is_home, team_stats, opponent_stats, player_stats in teams_to_process:
                # Create comprehensive team match data
                team_match_data = TeamMatchData(
                    season=season,
                    match_url=match_url,
                    home_team=home_team,
                    away_team=away_team,
                    team_name=team_name,
                    is_home=is_home,
                    team_score=metadata.get("home_score", 0) if is_home else metadata.get("away_score", 0),
                    opponent_score=metadata.get("away_score", 0) if is_home else metadata.get("home_score", 0),
                    match_date=metadata.get("match_date", ""),
                    stadium=metadata.get("stadium", ""),
                    referee=metadata.get("referee", ""),
                    assistant_referees=metadata.get("assistant_referees", []),
                    fourth_official=metadata.get("fourth_official", ""),
                    var_referee=metadata.get("var_referee", ""),
                    
                    # Summary Stats
                    possession=team_stats.get("possession", 0.0),
                    shots=team_stats.get("shots", 0),
                    shots_on_target=team_stats.get("shots_on_target", 0),
                    expected_goals=team_stats.get("expected_goals", 0.0),
                    corners=team_stats.get("corners", 0),
                    crosses=team_stats.get("crosses", 0),
                    touches=team_stats.get("touches", 0),
                    fouls_committed=team_stats.get("fouls_committed", 0),
                    fouls_drawn=team_stats.get("fouls_drawn", 0),
                    yellow_cards=team_stats.get("yellow_cards", 0),
                    red_cards=team_stats.get("red_cards", 0),
                    offsides=team_stats.get("offsides", 0),
                    
                    # Passing Stats
                    passes_completed=team_stats.get("passes_completed", 0),
                    passes_attempted=team_stats.get("passes_attempted", 0),
                    passing_accuracy=team_stats.get("passing_accuracy", 0.0),
                    short_passes_completed=team_stats.get("short_passes_completed", 0),
                    short_passes_attempted=team_stats.get("short_passes_attempted", 0),
                    medium_passes_completed=team_stats.get("medium_passes_completed", 0),
                    medium_passes_attempted=team_stats.get("medium_passes_attempted", 0),
                    long_passes_completed=team_stats.get("long_passes_completed", 0),
                    long_passes_attempted=team_stats.get("long_passes_attempted", 0),
                    progressive_passes=team_stats.get("progressive_passes", 0),
                    
                    # Defensive Stats
                    tackles=team_stats.get("tackles", 0),
                    tackles_won=team_stats.get("tackles_won", 0),
                    tackles_def_3rd=team_stats.get("tackles_def_3rd", 0),
                    tackles_mid_3rd=team_stats.get("tackles_mid_3rd", 0),
                    tackles_att_3rd=team_stats.get("tackles_att_3rd", 0),
                    interceptions=team_stats.get("interceptions", 0),
                    blocks=team_stats.get("blocks", 0),
                    clearances=team_stats.get("clearances", 0),
                    aerials_won=team_stats.get("aerials_won", 0),
                    aerials_lost=team_stats.get("aerials_lost", 0),
                    
                    # Goalkeeper Stats
                    saves=team_stats.get("saves", 0),
                    save_percentage=team_stats.get("save_percentage", 0.0),
                    goals_against=team_stats.get("goals_against", 0),
                    clean_sheet=(metadata.get("away_score", 0) if is_home else metadata.get("home_score", 0)) == 0,
                    expected_goals_against=team_stats.get("expected_goals_against", 0.0),
                    
                    # Possession Stats
                    dribbles_completed=team_stats.get("dribbles_completed", 0),
                    dribbles_attempted=team_stats.get("dribbles_attempted", 0),
                    dribble_success_rate=team_stats.get("dribble_success_rate", 0.0),
                    progressive_carries=team_stats.get("progressive_carries", 0),
                    carries_into_final_third=team_stats.get("carries_into_final_third", 0),
                    carries_into_penalty_area=team_stats.get("carries_into_penalty_area", 0),
                    
                    # Miscellaneous Stats
                    goal_kicks=team_stats.get("goal_kicks", 0),
                    throw_ins=team_stats.get("throw_ins", 0),
                    long_balls=team_stats.get("long_balls", 0),
                    sca=team_stats.get("sca", 0),
                    gca=team_stats.get("gca", 0),
                    
                    # Opponent's key stats for context
                    opponent_possession=opponent_stats.get("possession", 0.0),
                    opponent_shots=opponent_stats.get("shots", 0),
                    opponent_shots_on_target=opponent_stats.get("shots_on_target", 0),
                    opponent_expected_goals=opponent_stats.get("expected_goals", 0.0),
                )
                
                result.append(team_match_data)
                
                # Store player stats separately
                asyncio.create_task(self._store_player_stats(player_stats, metadata, season, match_url))
            
            return result
            
        except Exception as e:
            logger.error(f"Error scraping match {match_url}: {e}")
            return []
    
    async def _store_player_stats(self, player_stats: List[Dict], metadata: Dict, season: str, match_url: str):
        """Store player statistics in the database"""
        try:
            for player_data in player_stats:
                if player_data.get("player_name"):
                    # Create PlayerMatchData object
                    player_match = PlayerMatchData(
                        season=season,
                        match_url=match_url,
                        home_team=metadata.get("home_team", ""),
                        away_team=metadata.get("away_team", ""),
                        team_name=player_data.get("team_name", ""),
                        player_name=player_data.get("player_name", ""),
                        player_number=player_data.get("player_number", 0),
                        nation=player_data.get("nation", ""),
                        position=player_data.get("position", ""),
                        age=player_data.get("age", ""),
                        match_date=metadata.get("match_date", ""),
                        
                        # Playing time
                        minutes_played=player_data.get("minutes_played", 0),
                        started=player_data.get("minutes_played", 0) > 45,  # Assume started if played > 45 mins
                        
                        # Performance
                        goals=player_data.get("goals", 0),
                        assists=player_data.get("assists", 0),
                        penalty_goals=player_data.get("penalty_goals", 0),
                        penalty_attempts=player_data.get("penalty_attempts", 0),
                        shots=player_data.get("shots", 0),
                        shots_on_target=player_data.get("shots_on_target", 0),
                        expected_goals=player_data.get("expected_goals", 0.0),
                        expected_assists=player_data.get("expected_assists", 0.0),
                        
                        # Passing
                        passes_completed=player_data.get("passes_completed", 0),
                        passes_attempted=player_data.get("passes_attempted", 0),
                        passing_accuracy=player_data.get("passing_accuracy", 0.0),
                        progressive_passes=player_data.get("progressive_passes", 0),
                        
                        # Defense
                        tackles=player_data.get("tackles", 0),
                        interceptions=player_data.get("interceptions", 0),
                        blocks=player_data.get("blocks", 0),
                        clearances=player_data.get("clearances", 0),
                        aerials_won=player_data.get("aerials_won", 0),
                        aerials_lost=player_data.get("aerials_lost", 0),
                        
                        # Possession
                        touches=player_data.get("touches", 0),
                        dribbles_completed=player_data.get("dribbles_completed", 0),
                        dribbles_attempted=player_data.get("dribbles_attempted", 0),
                        carries=player_data.get("carries", 0),
                        progressive_carries=player_data.get("progressive_carries", 0),
                        
                        # Discipline
                        yellow_cards=player_data.get("yellow_cards", 0),
                        red_cards=player_data.get("red_cards", 0),
                        fouls_committed=player_data.get("fouls_committed", 0),
                        fouls_drawn=player_data.get("fouls_drawn", 0),
                        
                        # Advanced metrics
                        sca=player_data.get("sca", 0),
                        gca=player_data.get("gca", 0),
                    )
                    
                    # Save to database
                    await db.player_matches.insert_one(player_match.dict())
                    
        except Exception as e:
            logger.error(f"Error storing player stats: {e}")
    
    def cleanup(self):
        """Clean up the driver"""
        if self.driver:
            self.driver.quit()
            self.driver = None

# Global scraper instance
scraper = FBrefScraperV2()

# API Routes
@api_router.get("/")
async def root():
    return {"message": "FBref Match Report Scraper API v2 - Team Focused"}

@api_router.post("/scrape-team-multi-season")
async def start_team_multi_season_scraping(request: MultiSeasonScrapeRequest, background_tasks: BackgroundTasks):
    """Start scraping multiple seasons for a specific team"""
    try:
        # Create scraping status
        status = ScrapingStatus(
            status="running",
            request_type="team_focused" if request.target_team else "multi_season",
            seasons=request.seasons,
            target_team=request.target_team,
            total_seasons=len(request.seasons),
            current_match=f"Starting multi-season scrape for {'team ' + request.target_team if request.target_team else 'all teams'}"
        )
        
        # Save status to database
        await db.scraping_status.insert_one(status.dict())
        
        # Start background scraping task
        background_tasks.add_task(scrape_multi_season_background, request, status.id)
        
        return {"message": f"Started scraping {len(request.seasons)} seasons", "status_id": status.id, "request": request.dict()}
        
    except Exception as e:
        logger.error(f"Error starting multi-season scrape: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/scrape-season/{season}")
async def start_single_season_scraping(season: str, background_tasks: BackgroundTasks):
    """Start scraping a single season's match reports"""
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

async def scrape_multi_season_background(request: MultiSeasonScrapeRequest, status_id: str):
    """Background task to scrape multiple seasons"""
    try:
        # Setup driver
        if not scraper.setup_driver():
            await db.scraping_status.update_one(
                {"id": status_id},
                {"$set": {"status": "failed", "errors": ["Failed to setup Chrome driver"]}}
            )
            return
        
        total_matches_found = 0
        scraped_count = 0
        errors = []
        
        for season_idx, season in enumerate(request.seasons):
            try:
                # Update current season
                await db.scraping_status.update_one(
                    {"id": status_id},
                    {"$set": {"current_season": season}}
                )
                
                # Get match links
                match_links = scraper.extract_match_links(season)
                
                if not match_links:
                    errors.append(f"No match links found for season {season}")
                    continue
                
                # Filter matches for target team if specified
                if request.target_team:
                    # For team-focused scraping, we'll filter during the scraping process
                    # since we need to check the actual match content
                    pass
                
                total_matches_found += len(match_links)
                
                # Update progress
                await db.scraping_status.update_one(
                    {"id": status_id},
                    {"$set": {
                        "total_matches": total_matches_found,
                        "fixtures_found": total_matches_found
                    }}
                )
                
                # Scrape each match
                for match_url in match_links:
                    try:
                        # Update current match
                        await db.scraping_status.update_one(
                            {"id": status_id},
                            {"$set": {"current_match": match_url}}
                        )
                        
                        # Scrape match (with team filter if specified)
                        team_match_data_list = scraper.scrape_match_report(match_url, season, request.target_team)
                        
                        if team_match_data_list:
                            # Save to database
                            for team_match_data in team_match_data_list:
                                await db.team_matches.insert_one(team_match_data.dict())
                            scraped_count += 1
                            
                            # Update progress
                            await db.scraping_status.update_one(
                                {"id": status_id},
                                {"$set": {"matches_scraped": scraped_count}}
                            )
                        else:
                            if request.target_team:
                                # This might be normal if the target team didn't play in this match
                                pass
                            else:
                                errors.append(f"Failed to scrape {match_url}")
                        
                        # Small delay between requests
                        time.sleep(2)
                        
                    except Exception as e:
                        error_msg = f"Error scraping {match_url}: {str(e)}"
                        errors.append(error_msg)
                        logger.error(error_msg)
                
                # Update completed seasons
                await db.scraping_status.update_one(
                    {"id": status_id},
                    {"$set": {"completed_seasons": season_idx + 1}}
                )
                
            except Exception as e:
                error_msg = f"Error processing season {season}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        # Mark as completed
        await db.scraping_status.update_one(
            {"id": status_id},
            {"$set": {
                "status": "completed",
                "completed_at": datetime.utcnow(),
                "errors": errors,
                "completed_seasons": len(request.seasons)
            }}
        )
        
        logger.info(f"Completed multi-season scraping. Scraped {scraped_count} matches with {len(errors)} errors")
        
    except Exception as e:
        logger.error(f"Background scraping error: {e}")
        await db.scraping_status.update_one(
            {"id": status_id},
            {"$set": {"status": "failed", "errors": [str(e)]}}
        )
    finally:
        scraper.cleanup()

async def scrape_season_background(season: str, status_id: str):
    """Background task to scrape all matches in a season"""
    try:
        # Setup driver
        if not scraper.setup_driver():
            await db.scraping_status.update_one(
                {"id": status_id},
                {"$set": {"status": "failed", "errors": ["Failed to setup Chrome driver"]}}
            )
            return
        
        # Get match links
        match_links = scraper.extract_match_links(season)
        
        if not match_links:
            await db.scraping_status.update_one(
                {"id": status_id},
                {"$set": {"status": "failed", "errors": ["No match links found"]}}
            )
            return
        
        # Update total matches
        await db.scraping_status.update_one(
            {"id": status_id},
            {"$set": {
                "total_matches": len(match_links),
                "fixtures_found": len(match_links),
                "current_season": season,
                "total_seasons": 1
            }}
        )
        
        # Scrape each match
        scraped_count = 0
        errors = []
        
        for match_url in match_links:
            try:
                # Update current match
                await db.scraping_status.update_one(
                    {"id": status_id},
                    {"$set": {"current_match": match_url}}
                )
                
                # Scrape match
                team_match_data_list = scraper.scrape_match_report(match_url, season)
                
                if team_match_data_list:
                    # Save both teams' data to database
                    for team_match_data in team_match_data_list:
                        await db.team_matches.insert_one(team_match_data.dict())
                    scraped_count += 1
                    
                    # Update progress
                    await db.scraping_status.update_one(
                        {"id": status_id},
                        {"$set": {
                            "matches_scraped": scraped_count,
                            "completed_seasons": 1 if scraped_count == len(match_links) else 0
                        }}
                    )
                else:
                    errors.append(f"Failed to scrape {match_url}")
                
                # Small delay between requests
                time.sleep(2)
                
            except Exception as e:
                error_msg = f"Error scraping {match_url}: {str(e)}"
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

@api_router.get("/player-matches")
async def get_player_matches(season: Optional[str] = None, team: Optional[str] = None, player: Optional[str] = None):
    """Get scraped player matches with optional filtering"""
    query = {}
    
    if season:
        query["season"] = season
    
    if team:
        query["team_name"] = {"$regex": team, "$options": "i"}
    
    if player:
        query["player_name"] = {"$regex": player, "$options": "i"}
    
    matches = await db.player_matches.find(query, {"_id": 0}).to_list(1000)
    return matches

@api_router.get("/player-stats/{season}")
async def get_player_stats_for_season(season: str, team: Optional[str] = None):
    """Get aggregated player statistics for a season"""
    try:
        query = {"season": season}
        if team:
            query["team_name"] = {"$regex": team, "$options": "i"}
        
        # Aggregation pipeline to get player statistics
        pipeline = [
            {"$match": query},
            {
                "$group": {
                    "_id": "$player_name",
                    "team_name": {"$first": "$team_name"},
                    "position": {"$first": "$position"},
                    "total_minutes": {"$sum": "$minutes_played"},
                    "matches_played": {"$sum": 1},
                    "goals": {"$sum": "$goals"},
                    "assists": {"$sum": "$assists"},
                    "total_shots": {"$sum": "$shots"},
                    "shots_on_target": {"$sum": "$shots_on_target"},
                    "expected_goals": {"$sum": "$expected_goals"},
                    "expected_assists": {"$sum": "$expected_assists"},
                    "passes_completed": {"$sum": "$passes_completed"},
                    "passes_attempted": {"$sum": "$passes_attempted"},
                    "progressive_passes": {"$sum": "$progressive_passes"},
                    "tackles": {"$sum": "$tackles"},
                    "interceptions": {"$sum": "$interceptions"},
                    "yellow_cards": {"$sum": "$yellow_cards"},
                    "red_cards": {"$sum": "$red_cards"}
                }
            },
            {
                "$addFields": {
                    "passing_accuracy": {
                        "$cond": [
                            {"$gt": ["$passes_attempted", 0]},
                            {"$multiply": [{"$divide": ["$passes_completed", "$passes_attempted"]}, 100]},
                            0
                        ]
                    },
                    "shot_accuracy": {
                        "$cond": [
                            {"$gt": ["$total_shots", 0]},
                            {"$multiply": [{"$divide": ["$shots_on_target", "$total_shots"]}, 100]},
                            0
                        ]
                    },
                    "goals_per_game": {
                        "$cond": [
                            {"$gt": ["$matches_played", 0]},
                            {"$divide": ["$goals", "$matches_played"]},
                            0
                        ]
                    }
                }
            },
            {"$sort": {"goals": -1}}
        ]
        
        players = await db.player_matches.aggregate(pipeline).to_list(100)
        return {"players": players, "season": season}
        
    except Exception as e:
        logger.error(f"Error getting player stats for season {season}: {e}")
        return {"players": [], "season": season}

@api_router.post("/export-player-csv")
async def export_player_csv(filters: FilterRequest):
    """Export filtered player match data as CSV"""
    try:
        # Build query
        query = {}
        
        if filters.seasons:
            query["season"] = {"$in": filters.seasons}
        
        if filters.teams:
            query["team_name"] = {"$in": filters.teams}
        
        # Get player matches
        matches = await db.player_matches.find(query, {"_id": 0}).to_list(10000)
        
        if not matches:
            raise HTTPException(status_code=404, detail="No player matches found with given filters")
        
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
            headers={"Content-Disposition": "attachment; filename=fbref_player_matches.csv"}
        )
        
    except Exception as e:
        logger.error(f"Error exporting player CSV: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {e}")

@api_router.get("/database-schema")
async def get_database_schema():
    """Get comprehensive database schema information"""
    return {
        "team_match_data": {
            "description": "Comprehensive team-centric match statistics",
            "total_fields": 80,
            "categories": {
                "basic_info": ["id", "match_date", "season", "home_team", "away_team", "team_name", "is_home"],
                "match_result": ["team_score", "opponent_score"],
                "officials": ["stadium", "referee", "assistant_referees", "fourth_official", "var_referee"],
                "summary_stats": ["possession", "shots", "shots_on_target", "expected_goals", "corners", "crosses", "touches", "fouls_committed", "fouls_drawn", "yellow_cards", "red_cards", "offsides"],
                "advanced_shooting": ["shots_penalty_area", "shots_outside_penalty_area", "shots_free_kicks", "shots_foot", "shots_head", "goals_penalty", "goals_free_kicks"],
                "passing_stats": ["passes_completed", "passes_attempted", "passing_accuracy", "short_passes_completed", "short_passes_attempted", "medium_passes_completed", "medium_passes_attempted", "long_passes_completed", "long_passes_attempted", "progressive_passes"],
                "advanced_passing": ["passes_key", "passes_final_third", "passes_penalty_area", "passes_under_pressure", "passes_switches", "passes_live", "passes_dead", "passes_free_kicks", "passes_through_balls", "passes_corners"],
                "defensive_stats": ["tackles", "tackles_won", "tackles_def_3rd", "tackles_mid_3rd", "tackles_att_3rd", "interceptions", "blocks", "clearances", "aerials_won", "aerials_lost"],
                "pressure_stats": ["pressures", "pressures_successful", "pressures_def_3rd", "pressures_mid_3rd", "pressures_att_3rd"],
                "goalkeeper_stats": ["saves", "save_percentage", "goals_against", "clean_sheet", "expected_goals_against"],
                "possession_stats": ["dribbles_completed", "dribbles_attempted", "dribble_success_rate", "progressive_carries", "carries_into_final_third", "carries_into_penalty_area"],
                "advanced_possession": ["carries_total_distance", "carries_progressive_distance", "touches_def_3rd", "touches_mid_3rd", "touches_att_3rd", "touches_penalty_area"],
                "set_pieces": ["corners_taken", "free_kicks_taken", "penalties_taken", "penalties_scored", "penalties_missed"],
                "miscellaneous": ["goal_kicks", "throw_ins", "long_balls", "sca", "gca", "recoveries", "own_goals"],
                "opponent_context": ["opponent_possession", "opponent_shots", "opponent_shots_on_target", "opponent_expected_goals"]
            }
        },
        "player_match_data": {
            "description": "Comprehensive individual player match statistics",
            "total_fields": 75,
            "categories": {
                "basic_info": ["id", "match_date", "season", "home_team", "away_team", "team_name", "player_name", "player_number", "nation", "position", "age"],
                "playing_time": ["minutes_played", "started"],
                "performance": ["goals", "assists", "penalty_goals", "penalty_attempts", "shots", "shots_on_target", "expected_goals", "expected_assists"],
                "advanced_shooting": ["shots_penalty_area", "shots_outside_penalty_area", "shots_left_foot", "shots_right_foot", "shots_head", "shots_free_kicks", "goals_per_shot"],
                "passing": ["passes_completed", "passes_attempted", "passing_accuracy", "progressive_passes"],
                "advanced_passing": ["passes_short", "passes_medium", "passes_long", "passes_key", "passes_final_third", "passes_penalty_area", "passes_under_pressure", "pass_targets", "pass_targets_completed"],
                "defense": ["tackles", "interceptions", "blocks", "clearances", "aerials_won", "aerials_lost"],
                "advanced_defense": ["tackles_def_3rd", "tackles_mid_3rd", "tackles_att_3rd", "tackles_dribbled_past", "pressures", "pressures_successful", "errors_leading_to_shot"],
                "possession": ["touches", "dribbles_completed", "dribbles_attempted", "carries", "progressive_carries"],
                "advanced_possession": ["touches_def_3rd", "touches_mid_3rd", "touches_att_3rd", "touches_penalty_area", "dribbles_take_on", "carries_distance", "carries_progressive_distance", "miscontrols", "dispossessed"],
                "discipline": ["yellow_cards", "red_cards", "fouls_committed", "fouls_drawn"],
                "advanced_metrics": ["sca", "gca"],
                "goalkeeper_specific": ["saves_penalty_area", "saves_free_kicks", "saves_corners", "saves_crosses", "punches", "keeper_sweeper_actions", "passes_goal_kicks", "passes_launches_pct", "pass_length_avg"]
            }
        },
        "collections": {
            "team_matches": "Team-centric match data for analytics",
            "player_matches": "Individual player match performance data",
            "scraping_status": "Background task progress tracking"
        }
    }

@api_router.get("/available-teams/{season}")
async def get_teams_for_season(season: str):
    """Get list of teams that played in a specific season"""
    try:
        teams = await db.team_matches.distinct("team_name", {"season": season})
        return {"teams": sorted(teams)}
    except Exception as e:
        logger.error(f"Error getting teams for season {season}: {e}")
        return {"teams": []}

@api_router.post("/export-team-csv")
async def export_team_csv(filters: FilterRequest):
    """Export filtered team match data as CSV"""
    try:
        # Build query
        query = {}
        
        if filters.seasons:
            query["season"] = {"$in": filters.seasons}
        
        if filters.teams:
            query["team_name"] = {"$in": filters.teams}
        
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
        return {"seasons": ["2024-25"]}  # Default fallback

@api_router.get("/team-matches")
async def get_team_matches(season: Optional[str] = None, team: Optional[str] = None):
    """Get scraped team matches with optional filtering"""
    try:
        query = {}
        if season:
            query["season"] = season
        if team:
            query["team_name"] = team
            
        matches = await db.team_matches.find(query, {"_id": 0}).to_list(1000)
        return matches
    except Exception as e:
        logger.error(f"Error getting team matches: {e}")
        return []

@api_router.get("/teams")
async def get_available_teams():
    """Get list of available teams"""
    try:
        teams = await db.team_matches.distinct("team_name")
        return {"teams": sorted(teams)}
    except Exception as e:
        logger.error(f"Error getting teams: {e}")
        return {"teams": []}

@api_router.get("/team-stats/{team_name}")
async def get_team_statistics(team_name: str, season: Optional[str] = None):
    """Get aggregated statistics for a specific team"""
    try:
        query = {"team_name": {"$regex": team_name, "$options": "i"}}
        if season:
            query["season"] = season
        
        matches = await db.team_matches.find(query, {"_id": 0}).to_list(1000)
        
        if not matches:
            raise HTTPException(status_code=404, detail="No matches found for this team")
        
        # Calculate aggregated stats
        total_matches = len(matches)
        wins = sum(1 for m in matches if m["team_score"] > m["opponent_score"])
        draws = sum(1 for m in matches if m["team_score"] == m["opponent_score"])
        losses = total_matches - wins - draws
        
        # Average stats
        avg_stats = {
            "possession": sum(m["possession"] for m in matches) / total_matches,
            "shots": sum(m["shots"] for m in matches) / total_matches,
            "shots_on_target": sum(m["shots_on_target"] for m in matches) / total_matches,
            "expected_goals": sum(m["expected_goals"] for m in matches) / total_matches,
        }
        
        return {
            "team_name": team_name,
            "season": season,
            "total_matches": total_matches,
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "win_percentage": (wins / total_matches) * 100,
            "average_stats": avg_stats,
            "matches": matches
        }
        
    except Exception as e:
        logger.error(f"Error getting team stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
