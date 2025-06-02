#!/usr/bin/env python3
"""
Quick test script to verify FBref scraping functionality
"""

import sys
import os
sys.path.append('/app/backend')

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time

def test_fbref_access():
    """Test basic access to FBref and find match reports"""
    
    # Setup Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.binary_location = "/usr/bin/chromium"
    
    driver = None
    try:
        # Initialize driver with service
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=chrome_options)
        print("✅ Chrome driver initialized successfully")
        
        # Test URL for 2023-24 season
        url = "https://fbref.com/en/comps/9/2023-24/schedule/Premier-League-Scores-and-Fixtures"
        print(f"🔍 Accessing: {url}")
        
        driver.get(url)
        time.sleep(5)
        
        # Get page title
        title = driver.title
        print(f"📄 Page title: {title}")
        
        # Look for match report links with different possible text variations
        possible_link_texts = ["Match Report", "Report", "match report"]
        
        for link_text in possible_link_texts:
            links = driver.find_elements(By.LINK_TEXT, link_text)
            print(f"🔗 Found {len(links)} links with text '{link_text}'")
            
            if links:
                # Print first few link URLs
                for i, link in enumerate(links[:3]):
                    href = link.get_attribute("href")
                    print(f"   {i+1}. {href}")
                break
        
        # Also try partial link text
        partial_links = driver.find_elements(By.PARTIAL_LINK_TEXT, "Report")
        print(f"🔗 Found {len(partial_links)} links containing 'Report'")
        
        # Look for any links that contain "matches" in the href
        all_links = driver.find_elements(By.TAG_NAME, "a")
        match_links = []
        result_links = []
        
        for link in all_links:
            href = link.get_attribute("href")
            link_text = link.text.strip()
            
            if href:
                # Look for actual match result links
                if "/en/matches/" in href and len(href.split("/")) > 5:
                    match_links.append((href, link_text))
                # Also look for result or score links
                elif "result" in link_text.lower() or "score" in link_text.lower():
                    result_links.append((href, link_text))
        
        print(f"🎯 Found {len(match_links)} actual match links:")
        for i, (link, text) in enumerate(match_links[:5]):
            print(f"   {i+1}. Text: '{text}' | URL: {link}")
        
        print(f"🎯 Found {len(result_links)} result/score links:")
        for i, (link, text) in enumerate(result_links[:5]):
            print(f"   {i+1}. Text: '{text}' | URL: {link}")
        
        print("\n🔍 Analyzing page structure for fixtures...")
        
        # Look for fixture tables
        tables = driver.find_elements(By.TAG_NAME, "table")
        for i, table in enumerate(tables):
            table_id = table.get_attribute("id") or f"table_{i}"
            if "fixture" in table_id.lower() or "schedule" in table_id.lower():
                print(f"📋 Found fixture table: {table_id}")
                
                # Look at the first few rows to understand structure
                rows = table.find_elements(By.TAG_NAME, "tr")[:5]
                for j, row in enumerate(rows):
                    cells = row.find_elements(By.TAG_NAME, "td") + row.find_elements(By.TAG_NAME, "th")
                    cell_texts = [cell.text.strip() for cell in cells[:6]]  # First 6 columns
                    print(f"   Row {j}: {cell_texts}")
                    
                    # Look for links in this row
                    links_in_row = row.find_elements(By.TAG_NAME, "a")
                    for link in links_in_row:
                        href = link.get_attribute("href")
                        text = link.text.strip()
                        if href and "/en/matches/" in href and text:
                            print(f"      🔗 Link found: '{text}' -> {href}")
        
        # Test scraping one specific match if we found any
        if match_links:
            print(f"\n🧪 Testing scrape of first match: {match_links[0][0]}")
            test_match_scrape(driver, match_links[0][0])
        
        print("\n✅ Basic access test completed")
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if driver:
            driver.quit()

def test_match_scrape(driver, match_url):
    """Test scraping a specific match report"""
    try:
        print(f"🔍 Loading match: {match_url}")
        driver.get(match_url)
        time.sleep(5)
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Try to extract basic metadata
        print("📊 Extracting match data...")
        
        # Look for scorebox
        scorebox = soup.find("div", {"class": "scorebox"})
        if scorebox:
            print("✅ Found scorebox")
            
            # Try to find team names
            teams = scorebox.find_all("div", {"itemprop": "name"})
            if teams:
                print(f"⚽ Teams found: {[team.get_text().strip() for team in teams]}")
            
            # Try to find scores
            scores = scorebox.find_all("div", {"class": "score"})
            if scores:
                print(f"🥅 Scores found: {[score.get_text().strip() for score in scores]}")
        else:
            print("❌ No scorebox found")
        
        # Look for any tables with stats
        tables = soup.find_all("table")
        print(f"📋 Found {len(tables)} tables on the page")
        
        # Look for specific stat tables
        stat_tables = []
        for table in tables:
            table_id = table.get("id", "")
            if "stats_" in table_id:
                stat_tables.append(table_id)
        
        if stat_tables:
            print(f"📈 Stat tables found: {stat_tables}")
        else:
            print("❌ No stat tables found with 'stats_' in ID")
        
        print("✅ Match scrape test completed")
        
    except Exception as e:
        print(f"❌ Error during match scrape: {e}")

if __name__ == "__main__":
    test_fbref_access()