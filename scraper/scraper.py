import asyncio
import json
import random
import re
from urllib.parse import unquote
from pathlib import Path
from playwright.async_api import async_playwright
from playwright_stealth import stealth

# ==========================================
# CONFIGURATION
# ==========================================
BASE_URL = "https://www.amazon.in"
BRANDS = ["Safari", "Skybags", "American Tourister", "VIP", "Aristocrat"]
MAX_PRODUCTS_PER_BRAND = 10
DATA_PATH = Path("data/raw/output.json")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0"
]

# ==========================================
# ANTI-DETECTION HELPERS
# ==========================================

async def delay(a=2, b=4):
    """Randomized delay to mimic human hesitation."""
    await asyncio.sleep(random.uniform(a, b))

async def apply_stealth(page):
    """Applies stealth and falls back to manual bypass if the module fails."""
    try:
        stealth(page)
    except Exception:
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

async def handle_block(page):
    """Detects CAPTCHAs and pauses the script for manual solving."""
    content = await page.content()
    if "captcha" in content.lower() or "type the characters" in content.lower():
        print("\n" + "="*50)
        print("🚨 CAPTCHA DETECTED! PLEASE SOLVE IN THE BROWSER 🚨")
        print("="*50 + "\n\a") 
        try:
            await page.wait_for_selector("form[action='/errors/validateCaptcha']", state="hidden", timeout=120000)
            print("✔ CAPTCHA solved, resuming...")
            await delay(2, 4)
        except Exception:
            print("❌ Failed to solve CAPTCHA in time.")

# ==========================================
# DATA CLEANING HELPERS
# ==========================================

def clean_price(text):
    if not text: return 0.0
    text = re.sub(r"[₹,\s]", "", text)
    try: return float(text)
    except: return 0.0

def clean_rating(text):
    if not text: return 0.0
    m = re.search(r"(\d+\.?\d*)", text)
    return float(m.group(1)) if m else 0.0

def clean_int(text):
    if not text: return 0
    clean_text = re.sub(r"[,\s\(\)]", "", text)
    return int(clean_text) if clean_text.isdigit() else 0

# ==========================================
# EXTRACTION LOGIC
# ==========================================

async def extract_products(page, brand_name):
    """Extracts products from the search results page."""
    products = []
    cards = await page.query_selector_all('div[data-component-type="s-search-result"]')
    print(f"  Found {len(cards)} potential product cards on page.")
    
    for card in cards:
        if len(products) >= MAX_PRODUCTS_PER_BRAND: break
        try:
            link_el = await card.query_selector("a.a-link-normal.s-line-clamp-2")
            if not link_el: continue
            
            raw_href = await link_el.get_attribute("href")
            if not raw_href: continue

            full_url = f"{BASE_URL}{raw_href}" if raw_href.startswith("/") else raw_href
            decoded_url = unquote(full_url)
            
            asin_match = re.search(r'/dp/([A-Z0-9]{10})', decoded_url)
            asin = asin_match.group(1) if asin_match else None
            
            if not asin: continue

            title_el = await card.query_selector("h2 span")
            price_el = await card.query_selector(".a-price-whole")
            rating_el = await card.query_selector("i.a-icon-star-small .a-icon-alt, i.a-icon-star .a-icon-alt")
            review_el = await card.query_selector("span.a-size-base.s-underline-text")

            products.append({
                "brand": brand_name,
                "asin": asin,
                "title": (await title_el.inner_text()).strip() if title_el else "Unknown",
                "price": clean_price(await price_el.inner_text() if price_el else ""),
                "rating": clean_rating(await rating_el.get_attribute("innerHTML") if rating_el else ""),
                "review_count": clean_int(await review_el.inner_text() if review_el else ""),
                "url": f"https://www.amazon.in/dp/{asin}" 
            })
            print(f"   ✔ Found: {asin}")
        except Exception:
            continue
    return products

async def extract_reviews(context, asin):
    """Directly visits the review page using the ASIN with a retry mechanism."""
    reviews = []
    if not asin: return []
    
    review_url = f"https://www.amazon.in/product-reviews/{asin}/?reviewerType=all_reviews"
    
    for attempt in range(2):
        page = await context.new_page()
        await page.set_extra_http_headers({"User-Agent": random.choice(USER_AGENTS)})
        await apply_stealth(page)

        try:
            print(f"    → Navigating to reviews for {asin} (Attempt {attempt + 1})...")
            await page.goto(review_url, wait_until="commit", timeout=60000)
            await page.wait_for_load_state("domcontentloaded")
            
            if "ap/signin" in page.url:
                print(f"    🚨 REDIRECTED TO LOGIN! Pausing for 15s to let things cool down...")
                await asyncio.sleep(15) 
                return [] 

            await handle_block(page)

            for p in range(2):
                await page.wait_for_selector('[data-hook="review"]', timeout=10000)
                blocks = await page.query_selector_all('[data-hook="review"]')
                
                for r in blocks:
                    body = await r.query_selector('[data-hook="review-body"]')
                    if body:
                        text = await body.inner_text()
                        reviews.append({"asin": asin, "text": text.strip()})

                next_btn = await page.query_selector("li.a-last a")
                if next_btn and len(reviews) < 20:
                    await next_btn.click()
                    await page.wait_for_load_state("domcontentloaded")
                    await delay(3, 5) 
                else:
                    break
            
            break 
            
        except Exception as e:
            if "Timeout" in str(e) and attempt == 1:
                pass
            elif "Timeout" not in str(e):
                print(f"    ⚠ Network interrupted: {str(e).splitlines()[0]}")
                await asyncio.sleep(3) 
        finally:
            if not page.is_closed():
                await page.close()
                
    return reviews

# ==========================================
# MAIN EXECUTION PIPELINE
# ==========================================

async def run_scraper():
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir="user_data",
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )

        all_products = []
        all_reviews = []

        for brand in BRANDS:
            print(f"\n{'='*50}\n▶ Extracting Brand: {brand}\n{'='*50}")
            
            page = await browser.new_page()
            await apply_stealth(page)
            
            search_url = f"{BASE_URL}/s?k={brand.replace(' ', '+')}+trolley+bag"
            await page.goto(search_url, wait_until="domcontentloaded")
            await delay()
            await handle_block(page)
            
            products = await extract_products(page, brand)
            
            for product in products:
                print(f"  ☕ Cooling down for a few seconds...")
                await asyncio.sleep(random.uniform(5, 10)) 
                
                p_reviews = await extract_reviews(browser, product["asin"])
                
                all_products.append(product)
                all_reviews.extend(p_reviews)
                
                DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
                with open(DATA_PATH, "w", encoding="utf-8") as f:
                    json.dump({"products": all_products, "reviews": all_reviews}, f, indent=2, ensure_ascii=False)

            await page.close()

        await browser.close()
        print(f"\n✔ Success! Scraped {len(all_products)} products and {len(all_reviews)} reviews.")
        print(f"✔ Data saved to: {DATA_PATH.absolute()}")

if __name__ == "__main__":
    asyncio.run(run_scraper())