#!/usr/bin/env python3
"""
Test script to debug Playwright fixture extraction - TEST CORRECT FIXTURES URL
"""
import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

async def test_correct_fixtures_url():
    """Test fixture extraction from correct fixtures page"""
    print("🔍 Testing CORRECT fixtures URL...")
    
    playwright = None
    browser = None
    page = None
    
    try:
        # Setup Playwright
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Try current season fixtures URL (this should have schedule)
        test_url = "https://fbref.com/en/comps/9/2023-24/schedule/Premier-League-Scores-and-Fixtures"
        print(f"📡 Navigating to 2023-24 season: {test_url}")
        
        # Navigate to page
        await page.goto(test_url, wait_until='networkidle')
        print("✅ Page loaded successfully")
        
        # Get page title
        title = await page.title()
        print(f"📄 Page title: {title}")
        
        # Get page content
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Find all tables
        tables = soup.find_all('table')
        print(f"📊 Found {len(tables)} tables on page")
        
        # Look for fixture/schedule specific content
        schedule_table = None
        match_links_found = 0
        
        for i, table in enumerate(tables):
            table_id = table.get('id', f'no-id-{i}')
            rows = table.find_all('tr')
            
            # Check if this table has match links
            links_in_table = 0
            for row in rows:
                links = row.find_all('a')
                for link in links:
                    href = link.get('href', '')
                    if '/matches/' in href:
                        links_in_table += 1
                        match_links_found += 1
                        if match_links_found <= 3:  # Show first few examples
                            print(f"        🔗 MATCH LINK: https://fbref.com{href}")
            
            if links_in_table > 0:
                print(f"  ✅ Table {i} (ID: {table_id}) has {links_in_table} match links")
                schedule_table = table
                
                # Show sample rows
                print(f"    Sample rows from schedule table:")
                for row_idx, row in enumerate(rows[:5]):
                    cells = row.find_all(['td', 'th'])
                    cell_texts = [cell.get_text(strip=True)[:20] for cell in cells[:8]]
                    print(f"      Row {row_idx}: {cell_texts}")
            else:
                print(f"  ❌ Table {i} (ID: {table_id}) has {len(rows)} rows but no match links")
        
        print(f"\n📋 SUMMARY:")
        print(f"   Total match links found: {match_links_found}")
        print(f"   Schedule table found: {'YES' if schedule_table else 'NO'}")
        
        print("✅ Correct fixtures URL test completed")
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        
    finally:
        # Cleanup
        if page:
            await page.close()
        if browser:
            await browser.close()
        if playwright:
            await playwright.stop()

if __name__ == "__main__":
    asyncio.run(test_correct_fixtures_url())