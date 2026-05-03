"""
Playwright based scraper for Amazon India luggage product listings and reviews.
Handles anti-bot measures with random delays, realistic headers, and retry logic.
Falls back to sample data if scraping fails consistently.
"""
import asyncio
import json
import random
import re
from pathlib import Path

from playwright.async_api import async_playwright, Page, TimeoutError as PWTimeout

from utils.config import (
    AMAZON_BASE_URL, BRANDS, BRAND_SEARCH_QUERIES,
    DATA_RAW_PATH, PRODUCTS_PER_BRAND, MAX_REVIEW_PAGES,
)
from utils.logger import get_logger

logger = get_logger("scraper")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _delay(lo: float = 1.5, hi: float = 4.0):
    await asyncio.sleep(random.uniform(lo, hi))


def _parse_price(text: str) -> float:
    cleaned = re.sub(r"[₹,\s\u20b9]", "", text or "")
    try:
        return round(float(cleaned), 2)
    except ValueError:
        return 0.0


def _parse_rating(text: str) -> float:
    m = re.search(r"(\d+\.?\d*)\s*out\s*of\s*5", text or "")
    if m:
        return float(m.group(1))
    m = re.search(r"(\d+\.?\d*)", text or "")
    return float(m.group(1)) if m else 0.0


def _parse_int(text: str) -> int:
    cleaned = re.sub(r"[,\s]", "", text or "")
    m = re.search(r"(\d+)", cleaned)
    return int(m.group(1)) if m else 0


def _parse_discount(text: str) -> float:
    m = re.search(r"(\d+)\s*%", text or "")
    return float(m.group(1)) if m else 0.0


async def _is_captcha(page: Page) -> bool:
    content = await page.content()
    return any(kw in content for kw in ["Type the characters", "Enter the characters", "robot"])


# ── Search page scraper ───────────────────────────────────────────────────────

async def _scrape_search_page(page: Page, brand: str, query: str) -> list[dict]:
    products: list[dict] = []

    try:
        # ✅ Step 1: Go to homepage (not search URL)
        await page.goto("https://www.amazon.in", wait_until="domcontentloaded")
        await asyncio.sleep(random.uniform(3, 5))

        # ✅ Step 2: Wait for search box
        search_box = await page.wait_for_selector("input#twotabsearchtextbox", timeout=15000)

        # ✅ Step 3: Clear + type like human
        await search_box.click()
        await asyncio.sleep(random.uniform(0.5, 1.2))

        await search_box.fill("")  # clear if needed

        for char in query:
            await search_box.type(char, delay=random.randint(80, 150))  # human typing
        await asyncio.sleep(random.uniform(0.5, 1.5))

        # ✅ Step 4: Press Enter
        await page.keyboard.press("Enter")

        await page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(random.uniform(3, 6))

        # ✅ Step 5: Human scroll
        for _ in range(3):
            await page.mouse.wheel(0, random.randint(300, 700))
            await asyncio.sleep(random.uniform(1, 2))

        # 🔍 CAPTCHA check
        if await _is_captcha(page):
            logger.warning(f"CAPTCHA detected for {brand}. Waiting for manual solve...")
            await page.wait_for_timeout(25000)  # give time to solve manually

        items = await page.query_selector_all('[data-component-type="s-search-result"]')
        logger.info(f"{brand} — found {len(items)} raw cards on search page")

        for item in items:
            try:
                asin = await item.get_attribute("data-asin") or ""
                if not asin:
                    continue

                title_el = await item.query_selector("h2 a span")
                title    = (await title_el.inner_text()).strip() if title_el else ""

                link_el  = await item.query_selector("h2 a")
                href     = await link_el.get_attribute("href") if link_el else ""
                url_prod = f"{AMAZON_BASE_URL}{href}" if href else ""

                # Selling price (first offscreen price = current price)
                price = 0.0

                price_el = await item.query_selector(".a-price .a-offscreen")
                if price_el:
                    price = _parse_price(await price_el.inner_text())

                # fallback
                if price == 0:
                    alt_price = await item.query_selector(".a-price-whole")
                    if alt_price:
                        price = _parse_price(await alt_price.inner_text())
                        
                # MRP (struck-through price)
                mrp_el = await item.query_selector(".a-price.a-text-price .a-offscreen")
                mrp    = _parse_price(await mrp_el.inner_text()) if mrp_el else price

                # Ensure MRP >= price
                if mrp < price:
                    mrp = price

                # Discount badge
                disc_el   = await item.query_selector(".a-color-price")
                disc_text = await disc_el.inner_text() if disc_el else ""
                disc_pct  = _parse_discount(disc_text)
                if not disc_pct and mrp > price > 0:
                    disc_pct = round((1 - price / mrp) * 100, 1)

                # Rating
                rat_el   = await item.query_selector(".a-icon-alt")
                rat_text = await rat_el.inner_text() if rat_el else ""
                rating   = _parse_rating(rat_text)

                # Review count
                rev_el   = await item.query_selector('[aria-label*="ratings"]')
                rev_text = await rev_el.get_attribute("aria-label") if rev_el else ""
                rev_cnt  = _parse_int(rev_text)

                if not title:
                    continue

                # allow missing price (fallback later)
                if price == 0 and mrp > 0:
                    price = mrp

                products.append({
                    "asin":          asin,
                    "brand":         brand,
                    "title":         title,
                    "url":           url_prod,
                    "price":         price,
                    "mrp":           mrp,
                    "discount_pct":  disc_pct,
                    "rating":        rating,
                    "review_count":  rev_cnt,
                })

                if len(products) >= PRODUCTS_PER_BRAND:
                    break

            except Exception as exc:
                logger.debug(f"Card parse error: {exc}")

        return products

    except PWTimeout:
        logger.error(f"Timeout loading search page for {brand}")
        return []
    except Exception as exc:
        logger.error(f"Search page error for {brand}: {exc}")
        return []


# ── Review page scraper ───────────────────────────────────────────────────────

async def _scrape_reviews(page: Page, product: dict) -> list[dict]:
    reviews: list[dict] = []

    if not product.get("url"):
        return reviews

    try:
        # ✅ Step 1: Open product page
        await page.goto(product["url"], wait_until="domcontentloaded")
        await asyncio.sleep(random.uniform(3, 6))

        # ✅ Step 2: Human-like scroll (very important)
        for _ in range(random.randint(2, 4)):
            await page.mouse.wheel(0, random.randint(400, 900))
            await asyncio.sleep(random.uniform(1, 2))

        # ✅ Step 3: Random mouse movement
        await page.mouse.move(random.randint(100, 600), random.randint(100, 600))

        # CAPTCHA check
        if await _is_captcha(page):
            logger.warning(f"CAPTCHA on product {product['asin']} — waiting manual solve")
            await page.wait_for_timeout(25000)

        # ✅ Step 4: Scroll to reviews section
        try:
            await page.locator("#reviews-medley-footer").scroll_into_view_if_needed()
            await asyncio.sleep(random.uniform(2, 4))
        except:
            pass

        # ✅ Step 5: Click "See all reviews" (human-like)
        see_all = await page.query_selector('[data-hook="see-all-reviews-link-foot"]')
        if see_all:
            await asyncio.sleep(random.uniform(1, 2))
            await see_all.click()
            await page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(random.uniform(3, 5))

        # CAPTCHA again
        if await _is_captcha(page):
            logger.warning(f"CAPTCHA after clicking reviews {product['asin']}")
            await page.wait_for_timeout(25000)

        # ✅ Step 6: Extract reviews with slow pagination
        for _pg in range(MAX_REVIEW_PAGES):

            # human scroll inside reviews page
            for _ in range(random.randint(2, 3)):
                await page.mouse.wheel(0, random.randint(300, 700))
                await asyncio.sleep(random.uniform(1, 2))

            rev_els = await page.query_selector_all('[data-hook="review"]')

            for rev_el in rev_els:
                try:
                    t_spans = await rev_el.query_selector_all('[data-hook="review-title"] span')
                    rev_title = ""
                    for sp in t_spans:
                        txt = (await sp.inner_text()).strip()
                        if txt and "out of 5" not in txt:
                            rev_title = txt
                            break

                    body_el = await rev_el.query_selector('[data-hook="review-body"] span')
                    body = (await body_el.inner_text()).strip() if body_el else ""

                    rat_el = await rev_el.query_selector('[data-hook="review-star-rating"] .a-icon-alt')
                    rat_txt = await rat_el.inner_text() if rat_el else ""
                    rating = _parse_rating(rat_txt)

                    if not body:
                        continue

                    reviews.append({
                        "asin": product["asin"],
                        "brand": product["brand"],
                        "product_title": product["title"],
                        "title": rev_title,
                        "body": body,
                        "rating": rating,
                    })

                except Exception as exc:
                    logger.debug(f"Review parse error: {exc}")

            # ✅ Step 7: Human-like pagination
            next_btn = await page.query_selector(".a-pagination .a-last:not(.a-disabled) a")

            if next_btn:
                await asyncio.sleep(random.uniform(2, 4))

                # move mouse before clicking
                await page.mouse.move(random.randint(200, 800), random.randint(200, 600))
                await asyncio.sleep(random.uniform(0.5, 1.5))

                await next_btn.click()
                await page.wait_for_load_state("domcontentloaded")
                await asyncio.sleep(random.uniform(3, 6))
            else:
                break

        logger.info(f"{product['asin']} — scraped {len(reviews)} reviews")
        return reviews

    except Exception as exc:
        logger.error(f"Review scrape error {product['asin']}: {exc}")
        return reviews


# ── Main entry point ──────────────────────────────────────────────────────────

async def run_scraper(brands: list[str] | None = None):
    if brands is None:
        brands = BRANDS

    DATA_RAW_PATH.mkdir(parents=True, exist_ok=True)
    all_data: dict = {}

    async with async_playwright() as pw:

        # Use persistent context (IMPORTANT)
        context = await pw.chromium.launch_persistent_context(
            user_data_dir="user_data",   # stores cookies/session
            headless=False,              # MUST be False
            args=[
                "--start-maximized",
                "--disable-blink-features=AutomationControlled",
            ],
            viewport=None,
            locale="en-IN",
        )

        # Mask automation
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
        )

        page = context.pages[0] if context.pages else await context.new_page()

        # Warm-up browsing (VERY IMPORTANT)
        await page.goto("https://www.google.com")
        await asyncio.sleep(random.uniform(2, 4))

        for brand in brands:
            logger.info(f"\n{'─'*55}")
            logger.info(f"Brand: {brand}")
            logger.info(f"{'─'*55}")

            # Rotate user-agent per brand
            await context.set_extra_http_headers({
                "User-Agent": random.choice(USER_AGENTS),
                "Accept-Language": "en-IN,en-US;q=0.9,en;q=0.8"
            })

            query = BRAND_SEARCH_QUERIES.get(brand, f"{brand} luggage trolley bag")

            # Human-like delay before search
            await asyncio.sleep(random.uniform(2, 5))

            products = await _scrape_search_page(page, brand, query)

            # Handle CAPTCHA (manual fallback)
            if not products:
                logger.warning(f"No products for {brand}. Check for CAPTCHA manually.")
                await page.wait_for_timeout(20000)  # 20 sec to solve CAPTCHA
                products = await _scrape_search_page(page, brand, query)

            if not products:
                logger.warning(f"Still no data for {brand} — skipping")
                all_data[brand] = {"products": [], "reviews": []}
                continue

            brand_reviews: list[dict] = []

            for product in products:
                # Human delay
                await asyncio.sleep(random.uniform(2, 5))

                # Random mouse movement
                await page.mouse.move(random.randint(100, 500), random.randint(100, 500))

                revs = await _scrape_reviews(page, product)
                brand_reviews.extend(revs)

                if len(brand_reviews) >= 80:
                    logger.info(f"Reached 80 reviews for {brand}, stopping early")
                    break

            all_data[brand] = {"products": products, "reviews": brand_reviews}

            out = DATA_RAW_PATH / f"{brand.lower().replace(' ', '_')}.json"
            out.write_text(json.dumps(all_data[brand], indent=2, ensure_ascii=False))

            logger.info(
                f"Saved: {len(products)} products | {len(brand_reviews)} reviews → {out.name}"
            )

            #  Long pause between brands
            await asyncio.sleep(random.uniform(5, 10))

        await context.close()

    logger.info("\nScraping complete.")
    return all_data

if __name__ == "__main__":
    asyncio.run(run_scraper())
