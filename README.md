# 🇱🇧 Wardrops — Lebanon Price Tracker

Tracks price drops on OLX Lebanon listings since the start of the war (March 1, 2026).

**Live dashboard:** [karimdaoui.github.io/lb-real-estate](https://karimdaoui.github.io/lb-real-estate/)

## What it tracks

- **Real Estate** — Apartments, villas, land, chalets, commercial, buildings
- **Cars** — All car listings on OLX Lebanon

Both sections share the same dashboard with tabs to switch between them.

## How it works

- Scrapers run twice daily (8AM + 8PM Beirut time) via GitHub Actions
- Baseline prices are locked from March 1, 2026 (start of the war)
- Each run compares current prices to the baseline and detects drops
- Dashboard reads the drops feeds and renders them with filters and sorting

## Files

- `olx_scraper.py` — Real estate scraper
- `olx_scraper_cars.py` — Car scraper
- `index.html` — Dashboard with Real Estate / Cars tabs
- `drops_feed.json` — Real estate price drops
- `drops_feed_cars.json` — Car price drops

## Running locally

```
pip install requests
python olx_scraper.py
python olx_scraper_cars.py
```
