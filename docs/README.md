# Documentation Index

This directory contains comprehensive documentation for the FBref Analytics Platform.

## 📁 **Documentation Files**

### **`fbref-url-structure.md`**
- **Purpose:** Complete FBref URL patterns and season management logic
- **Contains:** Current vs historical season URL structures, testing results, implementation examples
- **Key Info:** Date-based season transitions (August 1st), URL format conversion logic

### **`CHANGELOG.md`**
- **Purpose:** Technical changelog documenting major system changes
- **Contains:** Playwright migration details, breaking changes, performance improvements
- **Key Info:** Browser automation migration from Selenium to Playwright

## 🔗 **Quick Reference**

### **Current Season URL (2024-25)**
```
https://fbref.com/en/comps/9/schedule/Premier-League-Scores-and-Fixtures
```

### **Historical Season URL Pattern**
```
https://fbref.com/en/comps/9/{YYYY-YYYY}/schedule/{YYYY-YYYY}-Premier-League-Scores-and-Fixtures
```

### **Season Transition Logic**
- **Current until August 1st:** Each season remains "current" until August 1st of the following year
- **Example:** 2024-25 is current until August 1, 2025, then 2025-26 becomes current

## 🧰 **Implementation References**

### **Backend URL Construction**
```python
# See: /app/backend/server.py
def get_season_fixtures_url(self, season: str) -> str
def _is_current_season(self, season: str, current_date) -> bool  
def _convert_to_full_season_format(self, season: str) -> str
```

### **Browser Automation**
```python
# Playwright setup (ARM64 compatible)
from playwright.async_api import async_playwright
playwright = await async_playwright().start()
browser = await playwright.chromium.launch(headless=True)
```

## 📊 **Verified Working URLs**

| Season | Type | Status | Match Links |
|--------|------|--------|-------------|
| 2024-25 | Current | ✅ Working | 1,147 |
| 2023-24 | Historical | ✅ Working | 1,198 |
| 2022-23 | Historical | ✅ Pattern Verified | N/A |

---

**Last Updated:** June 2, 2025  
**Next Review:** July 2025 (before new season)