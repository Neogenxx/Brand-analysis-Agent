"""
sample_data.py
--------------
Generates realistic mock data for all 6 luggage brands.
Used when the scraper has not been run yet.
All values are calibrated to reflect plausible Amazon India market conditions.
"""
import random
import json
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd
import numpy as np

from utils.config import DATA_PROCESSED_PATH, BRANDS

# ── Brand Profiles ─────────────────────────────────────────────────────────────
# Each profile drives the generation of realistic data for that brand.
BRAND_PROFILES = {
    "Safari": {
        "price_range": (2800, 9500),
        "avg_discount": 32,
        "discount_std": 8,
        "avg_rating": 4.2,
        "rating_std": 0.4,
        "sentiment_base": 0.72,
        "review_volume": "high",
        "positive_themes": ["sturdy build", "smooth wheels", "spacious", "good quality"],
        "negative_themes": ["zipper feels cheap", "weight is high", "average handle"],
        "aspect_scores": {
            "wheels": 0.78, "handle": 0.65, "zipper": 0.52,
            "material": 0.80, "durability": 0.82, "size": 0.75, "weight": 0.48,
        },
    },
    "Skybags": {
        "price_range": (1800, 6500),
        "avg_discount": 44,
        "discount_std": 10,
        "avg_rating": 3.9,
        "rating_std": 0.5,
        "sentiment_base": 0.58,
        "review_volume": "very_high",
        "positive_themes": ["good looks", "affordable price", "lightweight"],
        "negative_themes": ["wheels break easily", "zipper issues", "not very durable"],
        "aspect_scores": {
            "wheels": 0.45, "handle": 0.60, "zipper": 0.42,
            "material": 0.55, "durability": 0.50, "size": 0.70, "weight": 0.75,
        },
    },
    "American Tourister": {
        "price_range": (3200, 12000),
        "avg_discount": 28,
        "discount_std": 6,
        "avg_rating": 4.4,
        "rating_std": 0.35,
        "sentiment_base": 0.80,
        "review_volume": "high",
        "positive_themes": ["premium quality", "excellent wheels", "TSA lock", "elegant design"],
        "negative_themes": ["expensive", "heavy", "limited colour options"],
        "aspect_scores": {
            "wheels": 0.88, "handle": 0.82, "zipper": 0.78,
            "material": 0.85, "durability": 0.87, "size": 0.76, "weight": 0.40,
        },
    },
    "VIP": {
        "price_range": (1500, 10000),
        "avg_discount": 36,
        "discount_std": 12,
        "avg_rating": 4.0,
        "rating_std": 0.5,
        "sentiment_base": 0.62,
        "review_volume": "medium",
        "positive_themes": ["value for money", "good brand legacy", "decent build"],
        "negative_themes": ["inconsistent quality", "handle wobbles", "zipper stiff"],
        "aspect_scores": {
            "wheels": 0.62, "handle": 0.55, "zipper": 0.58,
            "material": 0.65, "durability": 0.60, "size": 0.68, "weight": 0.60,
        },
    },
    "Aristocrat": {
        "price_range": (1200, 5500),
        "avg_discount": 40,
        "discount_std": 11,
        "avg_rating": 3.7,
        "rating_std": 0.6,
        "sentiment_base": 0.50,
        "review_volume": "medium",
        "positive_themes": ["budget friendly", "looks good", "lightweight"],
        "negative_themes": ["cheap material", "wheels squeak", "not durable", "zipper broke"],
        "aspect_scores": {
            "wheels": 0.38, "handle": 0.48, "zipper": 0.35,
            "material": 0.42, "durability": 0.40, "size": 0.65, "weight": 0.72,
        },
    },
    "Nasher Miles": {
        "price_range": (2500, 8000),
        "avg_discount": 35,
        "discount_std": 9,
        "avg_rating": 4.1,
        "rating_std": 0.45,
        "sentiment_base": 0.70,
        "review_volume": "medium",
        "positive_themes": ["hardshell is solid", "great value", "smooth roller wheels", "good locks"],
        "negative_themes": ["customer service issues", "interior could be better", "slightly heavy"],
        "aspect_scores": {
            "wheels": 0.75, "handle": 0.68, "zipper": 0.70,
            "material": 0.78, "durability": 0.76, "size": 0.72, "weight": 0.50,
        },
    },
}

REVIEW_TEMPLATES = {
    "positive": [
        "Really happy with this {brand} bag. The wheels roll very smoothly and it looks great.",
        "Excellent quality! The {brand} luggage has sturdy build and good capacity.",
        "Bought this {brand} bag for my trip and absolutely loved it. Great purchase!",
        "The material is top-notch and the zipper feels very solid. {brand} did well here.",
        "Fantastic product! The handle is comfortable and wheels are silent on tiles.",
        "Value for money! Fits cabin size perfectly. Would recommend {brand} to everyone.",
        "Very impressed with the durability. Came back from a 2-week trip, zero damage.",
        "Lightweight yet spacious. This {brand} bag is exactly what I was looking for.",
        "Build quality is excellent. The polycarbonate shell is scratch resistant.",
        "Smooth 360-degree wheels make it a breeze to navigate airports.",
    ],
    "negative": [
        "The zipper started fraying after just 2 uses. Very disappointed with {brand}.",
        "Looks good but the wheels started wobbling after one trip. Not durable at all.",
        "The handle gets stuck while extending. Quality control seems poor for {brand}.",
        "Material feels cheap despite the price. Expected better from {brand}.",
        "One of the wheels broke off within a month. Really bad quality.",
        "Zipper got stuck and damaged clothes. Will not buy {brand} again.",
        "The lock mechanism is flimsy. Anyone can open it without a key.",
        "Too heavy when empty. Add luggage and it's a workout just lifting it.",
        "Interior lining came loose within weeks. Poor finishing from {brand}.",
        "Scratches very easily. Looks old after just one flight.",
    ],
    "neutral": [
        "Decent bag for the price. Nothing exceptional but does the job for {brand}.",
        "Average quality. The {brand} bag is okay for domestic travel.",
        "It's fine. Wheels work, zipper works. No complaints but no wow factor either.",
        "Ordered {brand} bag. Came on time. Product is as described.",
        "Average experience. Would have expected better finishing at this price.",
    ],
}

PRODUCT_TITLES = {
    "Safari": [
        "Safari Polaris 4 Wheel Strolley (55cm) - Cabin",
        "Safari Thorium 75cm Large Trolley Bag",
        "Safari Trek Hardside 65cm Medium Check-In",
        "Safari Zenith Soft Luggage 55cm",
        "Safari Revv 77cm 4 Wheel Large Trolley",
        "Safari Cosmos 68cm Cabin Bag",
        "Safari Fusion 65cm Polycarbonate Trolley",
        "Safari Trio Set (55+65+75) Luggage Set",
        "Safari Glider 79cm Large Strolley",
        "Safari Prisma 55cm Cabin Luggage",
        "Safari Edge Hardshell 68cm Trolley",
        "Safari Air 55cm Lightweight Cabin Bag",
    ],
    "Skybags": [
        "Skybags Ramp Plus 55cm Cabin Trolley",
        "Skybags Bingo Plus 65cm Medium Trolley",
        "Skybags Mint 77cm Large Trolley Bag",
        "Skybags Carbon Hardside 55cm Cabin",
        "Skybags Synco 65cm Soft Trolley",
        "Skybags Oxycheck 79cm Large Bag",
        "Skybags Elan 55cm Spinner Cabin Bag",
        "Skybags Stratus 68cm Polycarbonate",
        "Skybags Helix 2.0 65cm Trolley Bag",
        "Skybags Figo Plus 75cm Large Strolley",
        "Skybags Twister 55cm Carry-On",
        "Skybags Bolt 68cm Trolley Luggage",
    ],
    "American Tourister": [
        "American Tourister Linex Spinner 55cm Cabin",
        "American Tourister Curio 68cm Medium Hardside",
        "American Tourister Trigard 79cm Large Trolley",
        "American Tourister Ivy 55cm Spinner Bag",
        "American Tourister Twister Air 55cm",
        "American Tourister Starvibe 77cm Expandable",
        "American Tourister Polylite 65cm Trolley",
        "American Tourister Lite Ray 55cm Cabin",
        "American Tourister Moonlight 79cm Large",
        "American Tourister Applite 4.0S 55cm",
        "American Tourister Urban Groove 68cm",
        "American Tourister Soundbox 77cm Spinner",
    ],
    "VIP": [
        "VIP Skybolt 55cm Cabin Trolley Bag",
        "VIP Alfa Strolley 65cm Soft Luggage",
        "VIP Saturn Plus 79cm Large Trolley",
        "VIP Blaze 55cm Hardside Cabin Bag",
        "VIP Curve 65cm Polycarbonate Trolley",
        "VIP Odyssey 77cm Large Strolley",
        "VIP Capri 55cm Spinner Cabin",
        "VIP Nova 68cm Lightweight Trolley",
        "VIP Hexagon 65cm 4 Wheel Trolley",
        "VIP Fly 55cm Anti-Theft Cabin Bag",
        "VIP Canto 77cm Hardshell Trolley",
        "VIP Vector 65cm Expandable Bag",
    ],
    "Aristocrat": [
        "Aristocrat Police Plus 55cm Cabin Bag",
        "Aristocrat Kito 65cm Soft Trolley",
        "Aristocrat Matrix 77cm Large Luggage",
        "Aristocrat Nile 55cm Hardside Cabin",
        "Aristocrat Pista 65cm Trolley Bag",
        "Aristocrat Eco 79cm Soft Trolley",
        "Aristocrat Tourer 55cm 4 Wheel Bag",
        "Aristocrat Xcel 68cm Polycarbonate",
        "Aristocrat Cosmic 65cm Spinner",
        "Aristocrat Safari 55cm Cabin Trolley",
        "Aristocrat Marco 77cm Large Trolley",
        "Aristocrat Premier 65cm Strolley",
    ],
    "Nasher Miles": [
        "Nasher Miles Harbin 55cm Cabin Hardside",
        "Nasher Miles Melbourne 65cm Trolley",
        "Nasher Miles Glasgow 77cm Large Bag",
        "Nasher Miles Dublin 55cm Spinner Cabin",
        "Nasher Miles Lisbon 68cm Trolley",
        "Nasher Miles Oslo 79cm Hardside",
        "Nasher Miles Lagos 55cm Cabin Bag",
        "Nasher Miles Cairo 65cm Trolley",
        "Nasher Miles Venice 77cm Large Trolley",
        "Nasher Miles Bristol 55cm Spinner",
        "Nasher Miles Manila 65cm Hardside",
        "Nasher Miles Athens 68cm Trolley Bag",
    ],
}


def _random_date(days_back: int = 730) -> str:
    d = datetime.now() - timedelta(days=random.randint(0, days_back))
    return d.strftime("%d %B %Y")


def generate_products() -> pd.DataFrame:
    random.seed(42)
    np.random.seed(42)
    rows = []
    for brand, profile in BRAND_PROFILES.items():
        lo, hi = profile["price_range"]
        for i, title in enumerate(PRODUCT_TITLES[brand]):
            price = round(random.uniform(lo, hi), -1)
            disc  = max(5, min(70, int(np.random.normal(profile["avg_discount"], profile["discount_std"]))))
            mrp   = round(price / (1 - disc / 100), -1)
            rating = round(min(5, max(1, np.random.normal(profile["avg_rating"], profile["rating_std"]))), 1)
            vol_map = {"low": (50, 300), "medium": (200, 1200), "high": (800, 8000), "very_high": (2000, 20000)}
            rv_lo, rv_hi = vol_map[profile["review_volume"]]
            size = "Cabin (55cm)" if "55" in title else ("Large (77-79cm)" if any(x in title for x in ["77","79"]) else "Medium (65-68cm)")
            rows.append({
                "asin":         f"B0{brand[:2].upper()}{i:04d}",
                "brand":        brand,
                "title":        title,
                "price":        price,
                "mrp":          mrp,
                "discount_pct": disc,
                "rating":       rating,
                "review_count": random.randint(rv_lo, rv_hi),
                "size_category": size,
                "url":          f"https://www.amazon.in/dp/B0{brand[:2].upper()}{i:04d}",
            })
    return pd.DataFrame(rows)


def _pick_review_text(profile: dict, sentiment: str, brand: str) -> str:
    pool = REVIEW_TEMPLATES[sentiment]
    text = random.choice(pool).format(brand=brand)
    # sprinkle in a theme mention
    if sentiment == "positive" and profile["positive_themes"]:
        text += f" The {random.choice(profile['positive_themes'])} really impressed me."
    elif sentiment == "negative" and profile["negative_themes"]:
        text += f" The {random.choice(profile['negative_themes'])} was a letdown."
    return text


def generate_reviews(products_df: pd.DataFrame) -> pd.DataFrame:
    random.seed(7)
    np.random.seed(7)
    rows = []
    for _, product in products_df.iterrows():
        brand   = product["brand"]
        profile = BRAND_PROFILES[brand]
        n_reviews = random.randint(8, 15)
        for _ in range(n_reviews):
            # Sentiment distribution skewed by brand profile
            base = profile["sentiment_base"]
            r = random.random()
            if r < base:
                sentiment = "positive"
                rating = random.choice([4, 5])
            elif r < base + 0.15:
                sentiment = "neutral"
                rating = 3
            else:
                sentiment = "negative"
                rating = random.choice([1, 2])

            body = _pick_review_text(profile, sentiment, brand)
            rows.append({
                "asin":          product["asin"],
                "brand":         brand,
                "product_title": product["title"],
                "body":          body,
                "rating":        rating,
                "date":          _random_date(),
                "verified":      random.random() > 0.15,
                "sentiment_label": sentiment,
                "sentiment_score": round(
                    np.random.normal(0.6 if sentiment == "positive" else (-0.4 if sentiment == "negative" else 0.0), 0.15),
                    3,
                ),
            })
    return pd.DataFrame(rows)


def generate_sentiment(reviews_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for brand in BRANDS:
        profile  = BRAND_PROFILES[brand]
        br       = reviews_df[reviews_df["brand"] == brand]
        pos_pct  = (br["sentiment_label"] == "positive").mean() * 100
        neg_pct  = (br["sentiment_label"] == "negative").mean() * 100
        neu_pct  = (br["sentiment_label"] == "neutral").mean() * 100
        rows.append({
            "brand":           brand,
            "sentiment_score": round(profile["sentiment_base"] * 100, 1),
            "positive_pct":    round(pos_pct, 1),
            "negative_pct":    round(neg_pct, 1),
            "neutral_pct":     round(neu_pct, 1),
            "avg_review_rating": round(br["rating"].mean(), 2),
            "total_reviews":   len(br),
        })
    return pd.DataFrame(rows)


def generate_themes() -> dict:
    themes = {}
    for brand, profile in BRAND_PROFILES.items():
        themes[brand] = {
            "positive": profile["positive_themes"],
            "negative": profile["negative_themes"],
            "aspect_scores": profile["aspect_scores"],
        }
    return themes


def generate_agent_insights(products_df: pd.DataFrame, sentiment_df: pd.DataFrame) -> list:
    """Pre-baked non-obvious insights derived from sample data logic."""
    merged = products_df.groupby("brand").agg(
        avg_price=("price", "mean"),
        avg_discount=("discount_pct", "mean"),
        avg_rating=("rating", "mean"),
        total_products=("asin", "count"),
    ).reset_index().merge(sentiment_df[["brand", "sentiment_score"]], on="brand")

    insights = []

    # Insight 1 — Discount Dependency
    max_disc_brand = merged.loc[merged["avg_discount"].idxmax(), "brand"]
    max_disc_val   = merged["avg_discount"].max()
    insights.append({
        "rank":       1,
        "title":      f"{max_disc_brand} relies heavily on discounts to compete",
        "body":       (
            f"{max_disc_brand} carries an average discount of {max_disc_val:.0f}% — "
            f"the highest across all tracked brands. This suggests it cannot sustain "
            f"demand at listed prices and depends on promotional markdown to drive volume. "
            f"Compare this to American Tourister at just 28% average discount while maintaining "
            f"the highest sentiment score — indicating stronger organic demand."
        ),
        "brands":     [max_disc_brand, "American Tourister"],
        "category":   "Pricing Strategy",
        "confidence": "High",
        "evidence":   f"Avg discount: {max_disc_val:.0f}% vs category avg of {merged['avg_discount'].mean():.0f}%",
    })

    # Insight 2 — Sentiment vs Price Winner
    merged["value_score"] = merged["sentiment_score"] / merged["avg_price"] * 1000
    best_value = merged.loc[merged["value_score"].idxmax(), "brand"]
    best_price = merged.loc[merged["value_score"].idxmax(), "avg_price"]
    best_sent  = merged.loc[merged["value_score"].idxmax(), "sentiment_score"]
    insights.append({
        "rank":       2,
        "title":      f"{best_value} wins best value-for-money in the category",
        "body":       (
            f"{best_value} achieves a sentiment score of {best_sent:.0f}/100 at an average "
            f"price of ₹{best_price:,.0f} — the best sentiment-per-rupee ratio in the category. "
            f"Decision-makers targeting cost-conscious buyers should position against {best_value} "
            f"or study what it does right on durability and wheels to justify its price point."
        ),
        "brands":     [best_value],
        "category":   "Value-for-Money",
        "confidence": "High",
        "evidence":   f"Sentiment/price ratio is {merged.loc[merged['value_score'].idxmax(), 'value_score']:.2f} vs avg {merged['value_score'].mean():.2f}",
    })

    # Insight 3 — Anomaly: high rating but low sentiment (Skybags)
    insights.append({
        "rank":       3,
        "title":      "Skybags' ratings mask underlying quality complaints",
        "body":       (
            "Skybags shows an average star rating of 3.9 — seemingly average — but its review "
            "sentiment analysis reveals a high concentration of durability and wheel complaints "
            "that are often buried under high-volume positive ratings inflated by early purchases. "
            "Aspect-level analysis shows wheel sentiment at only 0.45/1.0, nearly 40% below "
            "category leader American Tourister (0.88). This disconnect between star rating and "
            "actual sentiment is a red flag for long-term brand equity."
        ),
        "brands":     ["Skybags"],
        "category":   "Anomaly Detection",
        "confidence": "Medium",
        "evidence":   "Wheel aspect score: 0.45 | Sentiment score: 58 | Avg rating: 3.9",
    })

    # Insight 4 — Premium Trap
    insights.append({
        "rank":       4,
        "title":      "American Tourister commands premium without the heaviest discounting",
        "body":       (
            "American Tourister is the highest-priced brand (avg ₹6,800) yet uses the lowest "
            "average discount (28%) — the opposite of what commodity brands do. Its 80/100 "
            "sentiment score and 4.4 star rating suggest customers perceive genuine value "
            "rather than being lured by discounts. This is a sustainable premium positioning "
            "that competitors find difficult to replicate without product quality investment."
        ),
        "brands":     ["American Tourister"],
        "category":   "Competitive Position",
        "confidence": "High",
        "evidence":   "Avg price: ₹6,800 | Avg discount: 28% | Sentiment: 80/100",
    })

    # Insight 5 — Aristocrat zipper risk
    insights.append({
        "rank":       5,
        "title":      "Aristocrat faces a zipper quality crisis that reviews confirm",
        "body":       (
            "Across Aristocrat reviews, zipper-related complaints appear in over 30% of "
            "negative reviews — the highest aspect failure rate in the category. With a "
            "zipper sentiment score of just 0.35/1.0, this is a critical product weakness. "
            "Brands like Safari (0.52) and Nasher Miles (0.70) outperform significantly. "
            "For Aristocrat to move upmarket, zipper quality must be addressed first — "
            "it is the primary driver of 1-star and 2-star reviews."
        ),
        "brands":     ["Aristocrat", "Safari", "Nasher Miles"],
        "category":   "Product Quality Risk",
        "confidence": "High",
        "evidence":   "Zipper aspect scores — Aristocrat: 0.35, Safari: 0.52, Nasher Miles: 0.70",
    })

    return insights


def save_sample_data() -> dict:
    """Generate and persist all sample data CSVs and JSONs."""
    print("Generating sample data...")

    products_df  = generate_products()
    reviews_df   = generate_reviews(products_df)
    sentiment_df = generate_sentiment(reviews_df)
    themes_data  = generate_themes()
    insights     = generate_agent_insights(products_df, sentiment_df)

    products_df.to_csv(DATA_PROCESSED_PATH / "products.csv",  index=False)
    reviews_df.to_csv(DATA_PROCESSED_PATH  / "reviews.csv",   index=False)
    sentiment_df.to_csv(DATA_PROCESSED_PATH / "sentiment.csv", index=False)

    with open(DATA_PROCESSED_PATH / "themes.json", "w") as f:
        json.dump(themes_data, f, indent=2)

    with open(DATA_PROCESSED_PATH / "insights.json", "w") as f:
        json.dump(insights, f, indent=2)

    print(f"Sample data saved to {DATA_PROCESSED_PATH}")
    print(f"  Products  : {len(products_df)} rows")
    print(f"  Reviews   : {len(reviews_df)} rows")
    print(f"  Sentiment : {len(sentiment_df)} rows")
    return {
        "products":  products_df,
        "reviews":   reviews_df,
        "sentiment": sentiment_df,
        "themes":    themes_data,
        "insights":  insights,
    }


if __name__ == "__main__":
    save_sample_data()
