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
from datetime import datetime, date
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

# Season management utilities
def get_current_season() -> str:
    """Get the current football season based on date logic
    2024-25 season is current until August 1st 2025, then 2025-26 becomes current
    """
    today = date.today()
    year = today.year
    month = today.month
    
    if month >= 8:  # August onwards starts new season
        return f"{year}-{str(year + 1)[-2:]}"
    else:  # January-July is previous season
        return f"{year - 1}-{str(year)[-2:]}"

def is_current_season(season: str) -> bool:
    """Check if given season is the current active season"""
    return season == get_current_season()

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
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
            
            # For ARM64 systems, use system chrome
            service = Service("/usr/bin/chromedriver")
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.wait = WebDriverWait(self.driver, 10)
            
            logger.info("ChromeDriver setup successful for ARM64")
            return True
            
        except Exception as e:
            logger.error(f"ChromeDriver setup failed: {e}")
            return False
        
    def cleanup(self):
        """Clean up driver resources"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
    
    def get_season_fixtures_url(self, season: str) -> str:
        """Get the fixtures URL for a specific season with current season logic"""
        if is_current_season(season):
            # Current season uses different URL structure
            return "https://fbref.com/en/comps/9/schedule/Premier-League-Scores-and-Fixtures"
        else:
            # Historical seasons use versioned URL structure
            return f"https://fbref.com/en/comps/9/{season}/schedule/Premier-League-Scores-and-Fixtures"
    
    def extract_season_fixtures(self, season: str) -> List[SeasonFixture]:
        """Extract all fixtures from a season (both completed and upcoming)"""
        try:
            fixtures_url = self.get_season_fixtures_url(season)
            logger.info(f"Fetching fixtures from: {fixtures_url} (Current season: {is_current_season(season)})")
            
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

# Global scraper instance
scraper = FBrefScraperV2()

# Enhanced API Routes
@api_router.get("/")
async def root():
    return {
        "message": "FBref Enhanced Multi-Season Team & Player Analytics Scraper API v2",
        "status": "running",
        "current_season": get_current_season(),
        "features": [
            "155+ statistical fields per match",
            "Multi-season scraping capability", 
            "Team-focused analysis",
            "Real-time progress tracking",
            "Comprehensive CSV export"
        ]
    }

@api_router.get("/teams")
async def get_teams():
    """Get list of available teams from the database"""
    try:
        # Get distinct team names from team_matches collection
        team_names = await db.team_matches.distinct("team_name")
        
        # Default Premier League teams if no data exists
        default_teams = [
            "Arsenal", "Aston Villa", "Bournemouth", "Brentford", "Brighton", 
            "Burnley", "Chelsea", "Crystal Palace", "Everton", "Fulham",
            "Liverpool", "Luton Town", "Manchester City", "Manchester United", 
            "Newcastle United", "Nottingham Forest", "Sheffield United", 
            "Tottenham", "West Ham", "Wolves"
        ]
        
        teams = team_names if team_names else default_teams
        
        return {
            "teams": sorted(teams),
            "total_teams": len(teams),
            "data_source": "database" if team_names else "default"
        }
        
    except Exception as e:
        logger.error(f"Error getting teams: {e}")
        # Return default teams on error
        default_teams = [
            "Arsenal", "Aston Villa", "Bournemouth", "Brentford", "Brighton", 
            "Burnley", "Chelsea", "Crystal Palace", "Everton", "Fulham",
            "Liverpool", "Luton Town", "Manchester City", "Manchester United", 
            "Newcastle United", "Nottingham Forest", "Sheffield United", 
            "Tottenham", "West Ham", "Wolves"
        ]
        return {
            "teams": sorted(default_teams),
            "total_teams": len(default_teams),
            "data_source": "default"
        }

@api_router.get("/available-teams/{season}")
async def get_available_teams_for_season(season: str):
    """Get teams that have data for a specific season"""
    try:
        team_names = await db.team_matches.distinct("team_name", {"season": season})
        
        return {
            "season": season,
            "teams": sorted(team_names),
            "total_teams": len(team_names)
        }
        
    except Exception as e:
        logger.error(f"Error getting teams for season {season}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/team-matches")
async def get_team_matches(season: Optional[str] = None, team: Optional[str] = None):
    """Get team match data with optional filtering"""
    try:
        query = {}
        if season:
            query["season"] = season
        if team:
            query["team_name"] = team
            
        matches = await db.team_matches.find(query, {"_id": 0}).to_list(1000)
        
        return {
            "matches": matches,
            "total_matches": len(matches),
            "filters": {"season": season, "team": team}
        }
        
    except Exception as e:
        logger.error(f"Error getting team matches: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/player-matches")
async def get_player_matches(season: Optional[str] = None, team: Optional[str] = None, player: Optional[str] = None):
    """Get player match data with optional filtering"""
    try:
        query = {}
        if season:
            query["season"] = season
        if team:
            query["team_name"] = team
        if player:
            query["player_name"] = player
            
        matches = await db.player_matches.find(query, {"_id": 0}).to_list(1000)
        
        return {
            "matches": matches,
            "total_matches": len(matches),
            "filters": {"season": season, "team": team, "player": player}
        }
        
    except Exception as e:
        logger.error(f"Error getting player matches: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/export-team-csv")
async def export_team_csv(filter_request: FilterRequest):
    """Export team match data as CSV"""
    try:
        query = {}
        if filter_request.seasons:
            query["season"] = {"$in": filter_request.seasons}
        if filter_request.teams:
            query["team_name"] = {"$in": filter_request.teams}
        if filter_request.referee:
            query["referee"] = filter_request.referee
        
        matches = await db.team_matches.find(query, {"_id": 0}).to_list(None)
        
        if not matches:
            raise HTTPException(status_code=404, detail="No team match data found")
        
        # Convert to DataFrame
        df = pd.DataFrame(matches)
        
        # Create CSV
        output = io.StringIO()
        df.to_csv(output, index=False)
        output.seek(0)
        
        # Create filename with current timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"team_matches_{timestamp}.csv"
        
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode('utf-8')),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(f"Error exporting team CSV: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/export-player-csv")
async def export_player_csv(filter_request: FilterRequest):
    """Export player match data as CSV"""
    try:
        query = {}
        if filter_request.seasons:
            query["season"] = {"$in": filter_request.seasons}
        if filter_request.teams:
            query["team_name"] = {"$in": filter_request.teams}
        
        matches = await db.player_matches.find(query, {"_id": 0}).to_list(None)
        
        if not matches:
            raise HTTPException(status_code=404, detail="No player match data found")
        
        # Convert to DataFrame
        df = pd.DataFrame(matches)
        
        # Create CSV
        output = io.StringIO()
        df.to_csv(output, index=False)
        output.seek(0)
        
        # Create filename with current timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"player_matches_{timestamp}.csv"
        
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode('utf-8')),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(f"Error exporting player CSV: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/database-schema")
async def get_database_schema():
    """Get comprehensive database schema information"""
    return {
        "team_match_data": {
            "description": "Comprehensive team statistics per match with 80+ fields",
            "total_fields": "80+",
            "categories": [
                "Basic match info (7 fields)",
                "Match result (2 fields)", 
                "Officials (5 fields)",
                "Summary stats (12 fields)",
                "Advanced shooting (7 fields)",
                "Passing stats (10 fields)",
                "Advanced passing (10 fields)",
                "Defensive stats (10 fields)",
                "Pressure stats (5 fields)",
                "Goalkeeper stats (5 fields)",
                "Possession stats (6 fields)",
                "Advanced possession (6 fields)",
                "Set piece stats (5 fields)",
                "Miscellaneous (7 fields)",
                "Opponent context (4 fields)"
            ]
        },
        "player_match_data": {
            "description": "Individual player statistics per match with 75+ fields",
            "total_fields": "75+",
            "categories": [
                "Basic player info (11 fields)",
                "Playing time (2 fields)",
                "Performance (8 fields)",
                "Advanced shooting (7 fields)",
                "Passing (4 fields)",
                "Advanced passing (9 fields)",
                "Defense (6 fields)",
                "Advanced defense (7 fields)",
                "Possession (5 fields)",
                "Advanced possession (9 fields)",
                "Discipline (4 fields)",
                "Advanced metrics (2 fields)",
                "Goalkeeper specific (9 fields)"
            ]
        },
        "seasons_info": {
            "current_season": get_current_season(),
            "supported_seasons": ["2024-25", "2023-24", "2022-23", "2021-22", "2020-21", "2019-20"],
            "season_logic": "2024-25 is current until August 1st 2025, then 2025-26 becomes current"
        }
    }

# Include the router in the main app
app.include_router(api_router)

# Configure CORS
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
