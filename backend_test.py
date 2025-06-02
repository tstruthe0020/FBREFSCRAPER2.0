#!/usr/bin/env python3
import requests
import time
import json
import os
from dotenv import load_dotenv
import pandas as pd
from io import StringIO
import unittest
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables from frontend .env file to get the backend URL
# For local testing, use the local URL
API_URL = "http://localhost:8001/api"
logger.info(f"Using API URL: {API_URL}")

class FBrefScraperAPITest(unittest.TestCase):
    """Test suite for the FBref Scraper API"""
    
    def setUp(self):
        """Setup for tests"""
        self.api_url = API_URL
        logger.info(f"Using API URL: {self.api_url}")
    
    def test_01_api_root(self):
        """Test API root endpoint"""
        logger.info("Testing API root endpoint...")
        response = requests.get(f"{self.api_url}/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("message", data)
        logger.info(f"API root response: {data}")
    
    def test_02_single_season_scraping(self):
        """Test single season scraping endpoint"""
        logger.info("Testing single season scraping...")
        
        # Start scraping for 2024-25 season
        response = requests.post(f"{self.api_url}/scrape-season/2024-25")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("status_id", data)
        status_id = data["status_id"]
        logger.info(f"Started scraping with status ID: {status_id}")
        
        # Monitor scraping progress
        max_checks = 10
        checks = 0
        completed = False
        
        while checks < max_checks and not completed:
            time.sleep(5)  # Wait 5 seconds between checks
            status_response = requests.get(f"{self.api_url}/scraping-status/{status_id}")
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                logger.info(f"Scraping status: {status_data['status']}, Matches scraped: {status_data.get('matches_scraped', 0)}/{status_data.get('total_matches', 0)}")
                
                if status_data["status"] in ["completed", "failed"]:
                    completed = True
                    if status_data["status"] == "failed":
                        logger.error(f"Scraping failed with errors: {status_data.get('errors', [])}")
                    else:
                        logger.info(f"Scraping completed successfully. Scraped {status_data.get('matches_scraped', 0)} matches.")
            else:
                logger.error(f"Failed to get scraping status: {status_response.status_code}")
            
            checks += 1
        
        # Verify data was scraped
        if completed:
            matches_response = requests.get(f"{self.api_url}/team-matches", params={"season": "2024-25"})
            self.assertEqual(matches_response.status_code, 200)
            matches = matches_response.json()
            
            if matches:
                logger.info(f"Found {len(matches)} team matches for 2024-25 season")
                
                # Verify team match data structure
                sample_match = matches[0]
                self.assertIn("team_name", sample_match)
                self.assertIn("match_date", sample_match)
                self.assertIn("home_team", sample_match)
                self.assertIn("away_team", sample_match)
                
                # Verify comprehensive stats extraction
                stats_fields = [
                    "possession", "shots", "shots_on_target", "expected_goals", 
                    "corners", "crosses", "touches", "fouls_committed", 
                    "yellow_cards", "red_cards", "passes_completed", "passes_attempted",
                    "passing_accuracy", "progressive_passes", "tackles", "interceptions",
                    "blocks", "clearances", "aerials_won", "dribbles_completed",
                    "progressive_carries"
                ]
                
                for field in stats_fields:
                    self.assertIn(field, sample_match, f"Missing field: {field}")
                
                logger.info("Team match data structure verified successfully")
            else:
                logger.warning("No matches found for 2024-25 season")
    
    def test_03_multi_season_scraping(self):
        """Test multi-season scraping endpoint"""
        logger.info("Testing multi-season scraping...")
        
        # Start multi-season scraping
        payload = {
            "seasons": ["2024-25", "2023-24"],
            "target_team": None  # Test without team filter first
        }
        
        response = requests.post(f"{self.api_url}/scrape-team-multi-season", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("status_id", data)
        status_id = data["status_id"]
        logger.info(f"Started multi-season scraping with status ID: {status_id}")
        
        # Monitor scraping progress
        max_checks = 10
        checks = 0
        completed = False
        
        while checks < max_checks and not completed:
            time.sleep(5)  # Wait 5 seconds between checks
            status_response = requests.get(f"{self.api_url}/scraping-status/{status_id}")
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                logger.info(f"Multi-season scraping status: {status_data['status']}, Seasons: {status_data.get('completed_seasons', 0)}/{status_data.get('total_seasons', 0)}")
                
                if status_data["status"] in ["completed", "failed"]:
                    completed = True
                    if status_data["status"] == "failed":
                        logger.error(f"Multi-season scraping failed with errors: {status_data.get('errors', [])}")
                    else:
                        logger.info(f"Multi-season scraping completed successfully.")
            else:
                logger.error(f"Failed to get multi-season scraping status: {status_response.status_code}")
            
            checks += 1
    
    def test_04_team_focused_scraping(self):
        """Test team-focused scraping endpoint"""
        logger.info("Testing team-focused scraping...")
        
        # First, get available teams from 2024-25 season
        teams_response = requests.get(f"{self.api_url}/available-teams/2024-25")
        
        if teams_response.status_code == 200:
            teams_data = teams_response.json()
            teams = teams_data.get("teams", [])
            
            if teams:
                target_team = teams[0]  # Use the first team
                logger.info(f"Using target team: {target_team}")
                
                # Start team-focused scraping
                payload = {
                    "seasons": ["2024-25"],
                    "target_team": target_team
                }
                
                response = requests.post(f"{self.api_url}/scrape-team-multi-season", json=payload)
                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertIn("status_id", data)
                status_id = data["status_id"]
                logger.info(f"Started team-focused scraping with status ID: {status_id}")
                
                # Monitor scraping progress
                max_checks = 10
                checks = 0
                completed = False
                
                while checks < max_checks and not completed:
                    time.sleep(5)  # Wait 5 seconds between checks
                    status_response = requests.get(f"{self.api_url}/scraping-status/{status_id}")
                    
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        logger.info(f"Team-focused scraping status: {status_data['status']}, Matches: {status_data.get('matches_scraped', 0)}/{status_data.get('total_matches', 0)}")
                        
                        if status_data["status"] in ["completed", "failed"]:
                            completed = True
                            if status_data["status"] == "failed":
                                logger.error(f"Team-focused scraping failed with errors: {status_data.get('errors', [])}")
                            else:
                                logger.info(f"Team-focused scraping completed successfully.")
                    else:
                        logger.error(f"Failed to get team-focused scraping status: {status_response.status_code}")
                    
                    checks += 1
                
                # Verify team-specific data was scraped
                if completed:
                    matches_response = requests.get(f"{self.api_url}/team-matches", params={"season": "2024-25", "team": target_team})
                    self.assertEqual(matches_response.status_code, 200)
                    matches = matches_response.json()
                    
                    if matches:
                        logger.info(f"Found {len(matches)} matches for team {target_team} in 2024-25 season")
                        
                        # Verify all matches are for the target team
                        for match in matches:
                            self.assertEqual(match["team_name"], target_team)
                        
                        logger.info("Team-focused scraping verified successfully")
                    else:
                        logger.warning(f"No matches found for team {target_team} in 2024-25 season")
            else:
                logger.warning("No teams available for 2024-25 season")
        else:
            logger.error(f"Failed to get available teams: {teams_response.status_code}")
    
    def test_05_data_retrieval_endpoints(self):
        """Test data retrieval endpoints"""
        logger.info("Testing data retrieval endpoints...")
        
        # Test available seasons endpoint
        seasons_response = requests.get(f"{self.api_url}/seasons")
        self.assertEqual(seasons_response.status_code, 200)
        seasons_data = seasons_response.json()
        self.assertIn("seasons", seasons_data)
        logger.info(f"Available seasons: {seasons_data['seasons']}")
        
        # Test available teams endpoint
        teams_response = requests.get(f"{self.api_url}/teams")
        self.assertEqual(teams_response.status_code, 200)
        teams_data = teams_response.json()
        self.assertIn("teams", teams_data)
        logger.info(f"Found {len(teams_data['teams'])} teams")
        
        # Test team-matches endpoint with filtering
        if seasons_data['seasons']:
            season = seasons_data['seasons'][0]
            matches_response = requests.get(f"{self.api_url}/team-matches", params={"season": season})
            self.assertEqual(matches_response.status_code, 200)
            matches = matches_response.json()
            logger.info(f"Found {len(matches)} matches for season {season}")
            
            # Test team stats endpoint if teams are available
            if teams_data['teams']:
                team = teams_data['teams'][0]
                stats_response = requests.get(f"{self.api_url}/team-stats/{team}", params={"season": season})
                
                if stats_response.status_code == 200:
                    stats_data = stats_response.json()
                    logger.info(f"Team stats for {team}: Matches: {stats_data['total_matches']}, Wins: {stats_data['wins']}")
                else:
                    logger.warning(f"No stats found for team {team} in season {season}")
    
    def test_06_csv_export(self):
        """Test CSV export functionality"""
        logger.info("Testing CSV export...")
        
        # Get available seasons and teams
        seasons_response = requests.get(f"{self.api_url}/seasons")
        teams_response = requests.get(f"{self.api_url}/teams")
        
        if seasons_response.status_code == 200 and teams_response.status_code == 200:
            seasons_data = seasons_response.json()
            teams_data = teams_response.json()
            
            if seasons_data['seasons'] and teams_data['teams']:
                # Create export request
                payload = {
                    "seasons": [seasons_data['seasons'][0]],
                    "teams": [teams_data['teams'][0]]
                }
                
                export_response = requests.post(f"{self.api_url}/export-team-csv", json=payload)
                self.assertEqual(export_response.status_code, 200)
                
                # Verify CSV content
                csv_content = export_response.content.decode('utf-8')
                df = pd.read_csv(StringIO(csv_content))
                
                logger.info(f"CSV export successful. Rows: {len(df)}, Columns: {len(df.columns)}")
                logger.info(f"CSV columns: {df.columns.tolist()[:10]}...")  # Show first 10 columns
            else:
                logger.warning("No seasons or teams available for CSV export test")
        else:
            logger.error("Failed to get seasons or teams for CSV export test")

def run_individual_test(test_name):
    """Run a single test and print detailed output"""
    logger.info(f"Running test: {test_name}")
    test = FBrefScraperAPITest(test_name)
    result = unittest.TextTestRunner(verbosity=2).run(test)
    logger.info(f"Test {test_name} completed with {'success' if result.wasSuccessful() else 'failure'}")
    return result.wasSuccessful()

if __name__ == "__main__":
    # Run just the API root test first
    test_name = 'test_01_api_root'
    print(f"\n{'='*80}")
    print(f"Running test: {test_name}")
    print(f"{'='*80}")
    result = run_individual_test(test_name)
    print(f"\n{'='*50}\n")
    
    print(f"Test result: {'✅ PASS' if result else '❌ FAIL'}")
    sys.exit(0 if result else 1)