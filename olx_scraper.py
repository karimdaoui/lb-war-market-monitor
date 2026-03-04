"""
OLX Lebanon Real Estate Scraper
================================
Scrapes Beirut property listings from OLX Lebanon daily.
Tracks price history and detects price drops.

Usage:
  pip install requests beautifulsoup4
  python olx_scraper.py

Run daily via cron:
  0 8 * * * cd /path/to/project && python olx_scraper.py

Output:
  - listings_db.json     → full database of all listings + price history
  - drops_feed.json      → current active price drops (for the dashboard)
"""

import requests
from bs4 import BeautifulSoup
import json
import os
import time
import random
from datetime import datetime, timedelta
from urllib.parse import urljoin

# ── Config ──────────────────────────────────────────────────────────
BASE_URL = "https://www.olx.com.lb"
SEARCH_URLS = [
    # Beirut apartments for sale
    "/en/properties/apartments-duplex-for-sale/beirut_g/",
    # Beirut houses/villas for sale
    "/en/properties/houses-villas-for-sale/beirut_g/",
    # Beirut land for sale
    "/en/properties/land-for-sale/beirut_g/",
    # Beirut chalets
    "/en/properties/chalets-for-sale/beirut_g/",
    # Mount Lebanon (extend coverage)
    "/en/properties/apartments-duplex-for-sale/mount-lebanon_g/",
    "/en/properties/houses-villas-for-sale/mount-lebanon_g/",
]

MAX_PAGES_PER_CATEGORY = 10  # pages to scrape per category
DB_FILE = "listings_db.json"
DROPS_FILE = "drops_feed.json"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
}

# Rate limiting
MIN_DELAY = 2  # seconds between requests
MAX_DELAY = 5


# ── Database ────────────────────────────────────────────────────────
def load_db():
    """Load existing listings database."""
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_db(db):
    """Save listings database."""
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


def save_drops(drops):
    """Save drops feed for the dashboard."""
    with open(DROPS_FILE, "w", encoding="utf-8") as f:
        json.dump(drops, f, ensure_ascii=False, indent=2)


# ── Scraping ────────────────────────────────────────────────────────
def fetch_page(url):
    """Fetch a page with rate limiting and error handling."""
    time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        print(f"  ✗ Failed to fetch {url}: {e}")
        return None


def parse_listing_card(card):
    """
    Parse a single listing card from OLX search results.
    
    NOTE: OLX frequently changes their HTML structure.
    You may need to inspect the page and update selectors.
    Below are common patterns — adjust as needed.
    """
    listing = {}

    try:
        # Listing URL and ID
        link_el = card.find("a", href=True)
        if not link_el:
            return None
        listing["url"] = urljoin(BASE_URL, link_el["href"])
        # Extract OLX listing ID from URL (usually the numeric part)
        url_parts = link_el["href"].rstrip("/").split("-")
        listing["id"] = url_parts[-1] if url_parts else link_el["href"]

        # Title
        title_el = card.find("h2") or card.find("h3") or card.find(class_=lambda c: c and "title" in c.lower() if c else False)
        listing["title"] = title_el.get_text(strip=True) if title_el else "Unknown"

        # Price — OLX Lebanon shows prices in USD or LBP
        price_el = card.find(class_=lambda c: c and "price" in c.lower() if c else False)
        if not price_el:
            price_el = card.find("span", string=lambda s: s and ("$" in s or "USD" in s or "LBP" in s) if s else False)
        
        if price_el:
            price_text = price_el.get_text(strip=True)
            listing["price_raw"] = price_text
            listing["price_usd"] = parse_price(price_text)
        else:
            listing["price_usd"] = None
            listing["price_raw"] = "N/A"

        # Location
        location_el = card.find(class_=lambda c: c and "location" in c.lower() if c else False)
        listing["location"] = location_el.get_text(strip=True) if location_el else ""

        # Property type (inferred from category URL or title)
        title_lower = listing["title"].lower()
        if any(w in title_lower for w in ["villa", "house", "بيت"]):
            listing["type"] = "Villa"
        elif any(w in title_lower for w in ["penthouse", "بنتهاوس"]):
            listing["type"] = "Penthouse"
        elif any(w in title_lower for w in ["chalet", "شاليه"]):
            listing["type"] = "Chalet"
        elif any(w in title_lower for w in ["land", "أرض"]):
            listing["type"] = "Land"
        elif any(w in title_lower for w in ["duplex", "دوبلكس"]):
            listing["type"] = "Duplex"
        else:
            listing["type"] = "Apartment"

        # Extract area (sqm) if mentioned in title
        import re
        sqm_match = re.search(r'(\d+)\s*(?:sqm|m²|m2|متر)', title_lower)
        listing["sqm"] = int(sqm_match.group(1)) if sqm_match else None

        return listing

    except Exception as e:
        print(f"  ✗ Error parsing card: {e}")
        return None


def parse_price(price_text):
    """
    Parse price string to USD integer.
    OLX Lebanon prices are usually in USD.
    Handles: "$250,000", "250000 USD", "250,000$", etc.
    """
    import re
    if not price_text:
        return None
    
    # Remove non-numeric except commas and dots
    cleaned = re.sub(r'[^\d,.]', '', price_text)
    cleaned = cleaned.replace(",", "")
    
    try:
        price = int(float(cleaned))
        # Sanity check — skip if too low (probably LBP or error)
        if price < 5000:
            return None
        return price
    except (ValueError, TypeError):
        return None


def scrape_category(category_url):
    """Scrape all pages of a single category."""
    listings = []
    
    for page in range(1, MAX_PAGES_PER_CATEGORY + 1):
        url = urljoin(BASE_URL, category_url)
        if page > 1:
            url = url.rstrip("/") + f"/?page={page}"
        
        print(f"  Fetching page {page}: {url}")
        html = fetch_page(url)
        if not html:
            break
        
        soup = BeautifulSoup(html, "html.parser")
        
        # Find listing cards — adjust selector based on current OLX structure
        # Common patterns: <li> with data-aut-id, <div> with listing class
        cards = soup.find_all("li", {"data-aut-id": "itemBox"})
        if not cards:
            cards = soup.find_all("div", class_=lambda c: c and "listing" in c.lower() if c else False)
        if not cards:
            # Fallback: look for article tags or any container with links
            cards = soup.find_all("article")
        
        if not cards:
            print(f"  → No listings found on page {page}, stopping.")
            break
        
        for card in cards:
            listing = parse_listing_card(card)
            if listing and listing.get("price_usd"):
                listings.append(listing)
        
        print(f"  → Found {len(cards)} cards, {len(listings)} valid listings so far")
        
        # Check if there's a next page
        next_btn = soup.find("a", string=lambda s: s and "next" in s.lower() if s else False)
        if not next_btn and page > 1:
            break
    
    return listings


# ── Price Tracking ──────────────────────────────────────────────────
def update_database(db, new_listings):
    """
    Update database with new scraped listings.
    Track price changes over time.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    updated = 0
    new = 0
    drops = 0

    for listing in new_listings:
        lid = listing["id"]
        
        if lid in db:
            # Existing listing — check for price change
            existing = db[lid]
            old_price = existing["current_price"]
            new_price = listing["price_usd"]
            
            if new_price and old_price and new_price != old_price:
                # Record price change
                existing["price_history"].append({
                    "price": new_price,
                    "date": today,
                })
                existing["current_price"] = new_price
                existing["last_updated"] = today
                
                if new_price < old_price:
                    existing["drop_usd"] = existing["original_price"] - new_price
                    existing["drop_pct"] = round(
                        (existing["original_price"] - new_price) / existing["original_price"] * 100, 1
                    )
                    existing["last_drop_date"] = today
                    drops += 1
                
                updated += 1
            
            # Update metadata that might change
            existing["title"] = listing["title"]
            existing["url"] = listing["url"]
            existing["last_seen"] = today
        
        else:
            # New listing
            db[lid] = {
                "id": lid,
                "title": listing["title"],
                "url": listing["url"],
                "type": listing["type"],
                "location": listing["location"],
                "sqm": listing.get("sqm"),
                "original_price": listing["price_usd"],
                "current_price": listing["price_usd"],
                "price_raw": listing["price_raw"],
                "price_history": [{"price": listing["price_usd"], "date": today}],
                "first_seen": today,
                "last_seen": today,
                "last_updated": today,
                "drop_usd": 0,
                "drop_pct": 0,
                "last_drop_date": None,
            }
            new += 1

    return new, updated, drops


def generate_drops_feed(db):
    """
    Generate the drops feed JSON consumed by the dashboard.
    Only includes listings with actual price drops.
    """
    drops = []
    
    for lid, listing in db.items():
        if listing["drop_usd"] > 0:
            drops.append({
                "id": listing["id"],
                "title": listing["title"],
                "url": listing["url"],
                "type": listing["type"],
                "location": listing["location"],
                "sqm": listing.get("sqm"),
                "original_price": listing["original_price"],
                "current_price": listing["current_price"],
                "drop_usd": listing["drop_usd"],
                "drop_pct": listing["drop_pct"],
                "last_drop_date": listing["last_drop_date"],
                "first_seen": listing["first_seen"],
                "price_history": listing["price_history"],
            })
    
    # Sort by biggest percentage drop
    drops.sort(key=lambda x: x["drop_pct"], reverse=True)
    
    # Add summary stats
    feed = {
        "generated_at": datetime.now().isoformat(),
        "total_tracked": len(db),
        "total_drops": len(drops),
        "avg_drop_pct": round(
            sum(d["drop_pct"] for d in drops) / len(drops), 1
        ) if drops else 0,
        "biggest_drop_usd": max((d["drop_usd"] for d in drops), default=0),
        "drops": drops,
    }
    
    return feed


# ── Main ────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  OLX Lebanon Real Estate Scraper")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    db = load_db()
    print(f"\n📦 Loaded database: {len(db)} existing listings\n")
    
    all_listings = []
    
    for cat_url in SEARCH_URLS:
        print(f"\n🔍 Scraping: {cat_url}")
        listings = scrape_category(cat_url)
        all_listings.extend(listings)
        print(f"  ✓ Got {len(listings)} listings from this category")
    
    print(f"\n📊 Total scraped: {len(all_listings)} listings")
    
    # Deduplicate by ID
    seen = set()
    unique = []
    for l in all_listings:
        if l["id"] not in seen:
            seen.add(l["id"])
            unique.append(l)
    
    print(f"📊 Unique listings: {len(unique)}")
    
    # Update database
    new, updated, drops = update_database(db, unique)
    print(f"\n✅ Results:")
    print(f"   New listings:     {new}")
    print(f"   Price changes:    {updated}")
    print(f"   Price drops:      {drops}")
    
    # Save
    save_db(db)
    print(f"\n💾 Saved database: {len(db)} total listings → {DB_FILE}")
    
    # Generate drops feed
    feed = generate_drops_feed(db)
    save_drops(feed)
    print(f"📡 Generated drops feed: {feed['total_drops']} drops → {DROPS_FILE}")
    
    # Mark stale listings (not seen in 7+ days)
    today = datetime.now()
    stale = 0
    for lid, listing in db.items():
        last_seen = datetime.strptime(listing["last_seen"], "%Y-%m-%d")
        if (today - last_seen).days > 7:
            listing["stale"] = True
            stale += 1
    
    if stale:
        print(f"⚠️  {stale} listings not seen in 7+ days (possibly sold/removed)")
        save_db(db)
    
    print(f"\n{'=' * 60}")
    print(f"  Done! Dashboard data ready.")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
