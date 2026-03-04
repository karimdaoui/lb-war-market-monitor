# 🇱🇧 Panic Selling — Lebanon

Tracks price drops on OLX Lebanon real estate listings daily.

## Quick Setup (GitHub — free hosting)

1. **Create a private GitHub repo**

2. **Add these files to the repo root:**
   ```
   your-repo/
   ├── index.html              ← rename lebanon-panic-selling.html to this
   ├── olx_scraper.py
   └── .github/
       └── workflows/
           └── scrape.yml      ← the workflow file
   ```

3. **Enable GitHub Pages:**
   - Go to repo **Settings → Pages**
   - Under "Source", select **GitHub Actions**

4. **Run it:**
   - Go to **Actions** tab → "Scrape & Deploy" → **Run workflow**
   - Or just wait — it runs automatically every day at 8AM Beirut time

5. **Your dashboard is live at:** `https://yourusername.github.io/your-repo/`

## How it works

- **olx_scraper.py** crawls OLX Lebanon property listings (Beirut + Mount Lebanon)
- It stores every listing's price in `listings_db.json`
- Each day it compares new prices to old ones → detects drops
- Drops are written to `drops_feed.json`
- **index.html** reads `drops_feed.json` and renders the dashboard

## Scraper notes

- OLX changes their HTML structure occasionally — you may need to update the CSS selectors in `parse_listing_card()` after the first run
- To test locally: `pip install requests beautifulsoup4 && python olx_scraper.py`
- Rate limited to 2-5 seconds between requests to be respectful
- Covers: apartments, villas, houses, land, chalets across Beirut & Mount Lebanon

## Customization

- **Add more areas:** Edit `SEARCH_URLS` in the scraper to add Tripoli, Jounieh, etc.
- **Change LBP rate:** Update `LBP_RATE` in the HTML file
- **Scrape frequency:** Edit the cron schedule in `scrape.yml`
