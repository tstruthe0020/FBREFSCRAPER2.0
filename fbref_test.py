#!/usr/bin/env python3
import sys
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_driver():
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
        
        # Set binary location for Chromium on ARM64 Debian
        chrome_options.binary_location = "/usr/bin/chromium"
        
        # Use system chromedriver path
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=chrome_options)
        logger.info("Chrome driver setup successful on ARM64")
        return driver
    except Exception as e:
        logger.error(f"Failed to setup Chrome driver: {e}")
        try:
            # Fallback without explicit service
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-software-rasterizer")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.binary_location = "/usr/bin/chromium"
            
            driver = webdriver.Chrome(options=chrome_options)
            logger.info("Chrome driver setup successful (fallback)")
            return driver
        except Exception as e2:
            logger.error(f"Fallback Chrome driver setup also failed: {e2}")
            return None

def test_fbref_match_scraping():
    """Test scraping a specific FBref match page"""
    match_url = "https://fbref.com/en/matches/3a6836b4/Burnley-Manchester-City-August-11-2023-Premier-League"
    
    print(f"Testing scraping for match: {match_url}")
    
    # Setup the driver
    driver = setup_driver()
    if not driver:
        print("Failed to set up ChromeDriver. Test cannot continue.")
        return False
    
    try:
        # Navigate to the match page
        print(f"Navigating to {match_url}")
        driver.get(match_url)
        time.sleep(5)  # Wait for page to load
        
        # Get the page source
        page_source = driver.page_source
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # Print the title to verify we're on the right page
        title = soup.title.text if soup.title else "No title found"
        print(f"Page title: {title}")
        
        # Find the scorebox which contains team names and scores
        scorebox = soup.find("div", {"class": "scorebox"})
        if scorebox:
            print("Found scorebox element")
            
            # Extract team names
            teams = scorebox.find_all("div", {"itemprop": "name"})
            if teams and len(teams) >= 2:
                home_team = teams[0].get_text().strip()
                away_team = teams[1].get_text().strip()
                print(f"Teams: {home_team} vs {away_team}")
            else:
                print("Could not find team names in the expected format")
                # Try alternative methods to find team names
                team_divs = scorebox.find_all("div", {"class": "team"})
                if team_divs and len(team_divs) >= 2:
                    for i, team_div in enumerate(team_divs[:2]):
                        team_name_elem = team_div.find("a")
                        if team_name_elem:
                            team_name = team_name_elem.get_text().strip()
                            print(f"Team {i+1}: {team_name}")
            
            # Extract scores
            scores = scorebox.find_all("div", {"class": "score"})
            if scores and len(scores) >= 2:
                home_score = scores[0].get_text().strip()
                away_score = scores[1].get_text().strip()
                print(f"Score: {home_score} - {away_score}")
            else:
                print("Could not find scores in the expected format")
        else:
            print("Could not find scorebox element")
            
            # Try to find any team information
            print("Searching for any team information...")
            team_links = soup.find_all("a", href=lambda href: href and "/en/squads/" in href)
            if team_links:
                print(f"Found {len(team_links)} team links:")
                for link in team_links[:5]:  # Show first 5 only
                    print(f"  - {link.get_text().strip()} ({link['href']})")
            else:
                print("No team links found")
        
        # Find all tables on the page
        tables = soup.find_all("table")
        print(f"Found {len(tables)} tables on the page")
        
        # Print the IDs of the first 10 tables to help identify them
        for i, table in enumerate(tables[:10]):
            table_id = table.get("id", "No ID")
            print(f"Table {i+1} ID: {table_id}")
            
            # If it's a stats table, print some sample data
            if "stats" in table_id.lower():
                print(f"  Sample data from {table_id}:")
                rows = table.find_all("tr")
                if len(rows) > 1:  # Skip header row
                    sample_row = rows[1]
                    cells = sample_row.find_all(["td", "th"])
                    sample_data = [cell.get_text().strip() for cell in cells[:5]]  # First 5 cells
                    print(f"  {sample_data}")
        
        # Take a screenshot for debugging
        screenshot_path = "/tmp/fbref_match.png"
        driver.save_screenshot(screenshot_path)
        print(f"Screenshot saved to {screenshot_path}")
        
        # Close the driver
        driver.quit()
        
        print("Test completed successfully")
        return True
        
    except Exception as e:
        print(f"Error during test: {str(e)}")
        if driver:
            driver.quit()
        return False

if __name__ == "__main__":
    test_fbref_match_scraping()