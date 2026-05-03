import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── API Keys ──────────────────────────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
LLM_PROVIDER   = os.getenv("LLM_PROVIDER", "openai")   # "openai" | "gemini"
LLM_MODEL      = os.getenv("LLM_MODEL", "gpt-4o-mini")

# ── Brands & Search ───────────────────────────────────────────────────────────
BRANDS = [
    "Safari",
    "Skybags",
    "American Tourister",
    "VIP",
    "Aristocrat",
    "Nasher Miles",
]

BRAND_SEARCH_QUERIES = {
    "Safari":             "Safari luggage trolley bag Amazon India",
    "Skybags":            "Skybags trolley luggage bag Amazon India",
    "American Tourister": "American Tourister luggage trolley Amazon India",
    "VIP":                "VIP trolley bag luggage Amazon India",
    "Aristocrat":         "Aristocrat trolley luggage bag Amazon India",
    "Nasher Miles":       "Nasher Miles luggage trolley bag Amazon India",
}

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR            = Path(__file__).resolve().parent.parent
DATA_RAW_PATH       = BASE_DIR / "data" / "raw"
DATA_PROCESSED_PATH = BASE_DIR / "data" / "processed"
CHROMA_PATH         = BASE_DIR / "data" / "chroma_db"

DATA_RAW_PATH.mkdir(parents=True, exist_ok=True)
DATA_PROCESSED_PATH.mkdir(parents=True, exist_ok=True)
CHROMA_PATH.mkdir(parents=True, exist_ok=True)

# ── Scraper Limits ────────────────────────────────────────────────────────────
AMAZON_BASE_URL      = "https://www.amazon.in"
PRODUCTS_PER_BRAND   = 12
REVIEWS_PER_PRODUCT  = 10
MAX_REVIEW_PAGES     = 5

# ── Aspect Keywords ───────────────────────────────────────────────────────────
ASPECT_KEYWORDS = {
    "wheels":     ["wheel", "wheels", "rolling", "rolls", "spinner", "caster", "glide"],
    "handle":     ["handle", "handles", "grip", "telescopic", "pull", "extendable"],
    "zipper":     ["zipper", "zip", "zippers", "closure", "lock", "locking"],
    "material":   ["material", "fabric", "polycarbonate", "abs", "hard shell",
                   "soft shell", "hard case", "texture", "scratch"],
    "durability": ["durable", "durability", "sturdy", "strong", "broken", "cracked",
                   "damaged", "fell apart", "quality", "build"],
    "size":       ["size", "spacious", "capacity", "fits", "cabin", "check-in",
                   "compartment", "large", "small", "space"],
    "weight":     ["weight", "lightweight", "heavy", "light", "kg", "grams"],
}

# ── Sentiment Thresholds ──────────────────────────────────────────────────────
SENTIMENT_POSITIVE_THRESHOLD = 0.05
SENTIMENT_NEGATIVE_THRESHOLD = -0.05

# ── API ───────────────────────────────────────────────────────────────────────
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
