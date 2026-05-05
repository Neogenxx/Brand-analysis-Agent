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
TARGET_REVIEWS_PER_PRODUCT = 50
DATA_PATH = Path("data/raw/output.json")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0"
]

REFERERS = [
    "https://www.google.com/",
    "https://www.bing.com/",
    "https://search.yahoo.com/"
]

# ==========================================
# ANTI-DETECTION & HUMAN BEHAVIOR HELPERS
# ==========================================

async def delay(a=3, b=6):
    """Randomized delay to mimic human hesitation."""
    await asyncio.sleep(random.uniform(a, b))

async def human_interaction(page):
    """Simulates erratic human scrolling and curved mouse movements."""
    try:
        # Move mouse in slightly random, non-linear paths
        for _ in range(random.randint(2, 4)):
            x = random.randint(100, 800)
            y = random.randint(100, 600)
            await page.mouse.move(x, y, steps=random.randint(5, 15))
            await asyncio.sleep(random.uniform(0.1, 0.4))
        
        # Scroll down in unequal chunks
        await page.evaluate("window.scrollBy(0, {})".format(random.randint(200, 500)))
        await asyncio.sleep(random.uniform(0.5, 1.5))
        
        # Sometimes scroll slightly back up
        await page.evaluate("window.scrollBy(0, {})".format(random.randint(-150, 100)))
        await asyncio.sleep(random.uniform(0.5, 1.5))
        
        # Final scroll
        await page.evaluate("window.scrollBy(0, {})".format(random.randint(300, 700)))
    except Exception:
        pass # Ignore layout shifts during interaction

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
            await delay(3, 6)
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
    """Hardened extraction logic referencing omkarcloud/amazon-scraper strategies."""
    reviews = []
    if not asin: return []
    
    product_url = f"https://www.amazon.in/dp/{asin}"
    
    page = await context.new_page()
    await apply_stealth(page)
    
    await page.set_extra_http_headers({
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/"
    })

    try:
        # STEP 1: The Bridge Path
        print(f"    → (Bridge Path) Navigating to product page for {asin}...")
        await page.goto(product_url, wait_until="domcontentloaded", timeout=60000)
        await human_interaction(page)
        await handle_block(page)

        # STEP 2: The 'See More' Selection Logic
        see_more_selectors = [
            '[data-hook="see-all-reviews-link-foot"]',
            'a:has-text("See more reviews")',
            'a[href*="product-reviews/"]'
        ]
        
        found_link = False
        for selector in see_more_selectors:
            link = await page.query_selector(selector)
            if link:
                print(f"    → Organic Link Found ({selector}). Clicking...")
                await link.scroll_into_view_if_needed()
                await delay(1, 2)
                await link.click()
                await page.wait_for_load_state("load")
                found_link = True
                break
        
        if not found_link:
            print("    ⚠ Organic link failed. Navigating to reviews URL directly.")
            review_url = f"https://www.amazon.in/product-reviews/{asin}/"
            await page.goto(review_url, wait_until="load", timeout=60000)

        await handle_block(page)

        # STEP 3: Multi-Layer Extraction Loop
        while len(reviews) < TARGET_REVIEWS_PER_PRODUCT:
            # Force a scroll to the bottom to trigger lazy-load scripts
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(3) # Wait for AJAX to finish

            # Redundant Selector Logic
            selectors = [
                '[data-hook="review"]', 
                'div[id^="customer_review-"]', 
                '.a-section.review'
            ]
            
            blocks = []
            for sel in selectors:
                found = await page.query_selector_all(sel)
                if found:
                    blocks = found
                    break 

            if not blocks:
                print("    ⚠ No review blocks detected. Amazon may be rotating IDs.")
                break

            current_batch = []
            for r in blocks:
                body = await r.query_selector('[data-hook="review-body"], .review-text-content, span.a-size-base')
                if body:
                    text = (await body.inner_text()).strip()
                    # Clean the 'Read More' text often included in the inner text
                    text = text.replace("Read more", "").strip()
                    if text and not any(rev['text'] == text for rev in current_batch):
                        current_batch.append({"asin": asin, "text": text})
            
            reviews = current_batch
            print(f"    ✔ Loaded {len(reviews)} reviews so far...")

            if len(reviews) >= TARGET_REVIEWS_PER_PRODUCT:
                break

            # STEP 4: Expansion Button Selection Logic
            expand_btn = await page.query_selector('[data-hook="show-more-button"], .cm-cr-show-more a')
            if expand_btn:
                print("    → Expanding: Clicking 'Show 10 more reviews'...")
                await expand_btn.scroll_into_view_if_needed()
                await delay(2, 4)
                await expand_btn.click()
                await asyncio.sleep(4) 
                await human_interaction(page)
            else:
                print("    🏁 Reached the end of available reviews.")
                break

            if "ap/signin" in page.url:
                print("    🚨 Blocked by Login Wall during expansion! Stopping at current count.")
                break

    except Exception as e:
        print(f"    ⚠ Error during review extraction: {str(e).splitlines()[0]}")
    finally:
        if not page.is_closed():
            await page.close()
                
    return reviews[:TARGET_REVIEWS_PER_PRODUCT]

# ==========================================
# MAIN EXECUTION PIPELINE
# ==========================================

async def run_scraper():
    all_products = []
    all_reviews = []
    
    # Ensure data directory exists
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    async with async_playwright() as p:
        
        for brand in BRANDS:
            print(f"\n{'='*50}\n▶ Extracting Brand: {brand}\n{'='*50}")
            
            # Fresh Context per Brand - completely resets the browser session
            browser = await p.chromium.launch(
                headless=False,
                channel="chrome",
                args=["--disable-blink-features=AutomationControlled"]
            )
            
            # Randomize viewport size per brand
            context = await browser.new_context(
                viewport={'width': random.randint(1280, 1920), 'height': random.randint(800, 1080)}
            )
            
            page = await context.new_page()
            await apply_stealth(page)
            
            await page.set_extra_http_headers({
                "User-Agent": random.choice(USER_AGENTS),
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": random.choice(REFERERS)
            })
            
            search_url = f"{BASE_URL}/s?k={brand.replace(' ', '+')}+trolley+bag"
            await page.goto(search_url, wait_until="domcontentloaded")
            await human_interaction(page)
            await handle_block(page)
            
            products = await extract_products(page, brand)
            
            for product in products:
                # Heavy cooling period to protect the IP
                print(f"  ☕ Cooling down for 15-25 seconds before extracting reviews...")
                await asyncio.sleep(random.uniform(15, 25)) 
                
                p_reviews = await extract_reviews(context, product["asin"])
                
                all_products.append(product)
                all_reviews.extend(p_reviews)
                
                # Save progressively so data isn't lost if blocked
                with open(DATA_PATH, "w", encoding="utf-8") as f:
                    json.dump({"products": all_products, "reviews": all_reviews}, f, indent=2, ensure_ascii=False)

            await page.close()
            await browser.close()
            
            print(f"  🧹 Cleared session. Ready for next brand.")
            await asyncio.sleep(random.uniform(5, 10))

    print(f"\n✔ Success! Scraped {len(all_products)} products and {len(all_reviews)} reviews.")
    print(f"✔ Data saved to: {DATA_PATH.absolute()}")

if __name__ == "__main__":
    asyncio.run(run_scraper())