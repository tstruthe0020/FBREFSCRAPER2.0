#!/usr/bin/env python3
"""
Quick test to see what links are actually on the FBref page
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import re

def quick_test():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.binary_location = "/usr/bin/chromium"
    
    service = Service("/usr/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        url = "https://fbref.com/en/comps/9/2023-24/schedule/Premier-League-Scores-and-Fixtures"
        print(f"Accessing: {url}")
        
        driver.get(url)
        time.sleep(5)
        
        # Look at ALL links and see what we have
        all_links = driver.find_elements(By.TAG_NAME, "a")
        
        print(f"\n🔍 Found {len(all_links)} total links on page")
        
        # Look for patterns in links
        match_links = []
        score_like_links = []
        
        for link in all_links:
            href = link.get_attribute("href")
            text = link.text.strip()
            
            if href and "/en/matches/" in href:
                match_links.append((href, text))
                
                # Check if text could be a score
                if re.search(r'\d.*[–-].*\d', text):
                    score_like_links.append((href, text))
        
        print(f"\n📋 All /en/matches/ links ({len(match_links)}):")
        for i, (href, text) in enumerate(match_links[:20]):
            print(f"   {i+1:2d}. '{text}' -> {href}")
        
        print(f"\n⚽ Score-like links ({len(score_like_links)}):")
        for i, (href, text) in enumerate(score_like_links[:10]):
            print(f"   {i+1:2d}. '{text}' -> {href}")
        
        # Let's also check what tables are on the page
        tables = driver.find_elements(By.TAG_NAME, "table")
        print(f"\n📊 Found {len(tables)} tables:")
        
        for i, table in enumerate(tables[:5]):
            table_id = table.get_attribute("id") or f"no-id-{i}"
            print(f"   Table {i+1}: ID = '{table_id}'")
            
            # Check if this table has match links
            table_links = table.find_elements(By.TAG_NAME, "a")
            match_count = 0
            for link in table_links:
                href = link.get_attribute("href")
                if href and "/en/matches/" in href:
                    match_count += 1
            if match_count > 0:
                print(f"      -> Contains {match_count} match links")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    quick_test()