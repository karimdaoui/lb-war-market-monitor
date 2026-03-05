# 🇱🇧 Wardrops — Lebanon Real Estate Price Tracker

Tracks price drops on OLX Lebanon real estate listings since the start of the war (March 1, 2026).

**Live dashboard:** [karimdaoui.github.io/lb-real-estate](https://karimdaoui.github.io/lb-real-estate/)

## How it works

- **olx_scraper.py** crawls OLX Lebanon property listings daily (apartments, villas, land, chalets, commercial, buildings)
- Baseline prices are locked from March 1, 2026 (start of the war)
- Each day it compares current prices to the baseline → detects drops
- Drops are written to `drops_feed.json`
- **index.html** reads `drops_feed.json` and renders the dashboard

## Setup

The scraper runs automatically every day at 8AM Beirut time via GitHub Actions.

To run manually: Go to **Actions** tab → "Scrape & Deploy" → **Run workflow**

## Scraper notes

- OLX Lebanon serves data as JSON in `window.state` — no HTML parsing needed
- To test locally: `pip install requests && python olx_scraper.py`
- Rate limited to 2-4 seconds between requests
- Covers all Lebanon: apartments, villas, land, chalets, commercial, buildings

## Customization

- **Scrape more pages:** Edit `MAX_PAGES_PER_CATEGORY` in the scraper
- **Change LBP rate:** Update `LBP_RATE` in the HTML file
- **Scrape frequency:** Edit the cron schedule in `scrape.yml`
