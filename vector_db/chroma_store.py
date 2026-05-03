"""
chroma_store.py
---------------
Embeds customer reviews using sentence-transformers and stores them in ChromaDB.
Provides semantic search: find reviews most similar to a query phrase.
"""
import hashlib
import json
from pathlib import Path

import pandas as pd

from utils.config import DATA_PROCESSED_PATH, CHROMA_PATH
from utils.logger import get_logger

logger = get_logger("vector_db")

# Lazy imports (heavy libraries only loaded when needed)
_chroma_client = None
_collection    = None
_embedder      = None
COLLECTION_NAME = "brand_reviews"


def _get_embedder():
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading embedding model (all-MiniLM-L6-v2)...")
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedder


def _get_client():
    global _chroma_client
    if _chroma_client is None:
        import chromadb
        CHROMA_PATH.mkdir(parents=True, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    return _chroma_client


def _get_collection():
    global _collection
    if _collection is None:
        client = _get_client()
        _collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def _doc_id(asin: str, body: str) -> str:
    key = f"{asin}_{body[:80]}"
    return hashlib.md5(key.encode()).hexdigest()


# ── Indexing ──────────────────────────────────────────────────────────────────

def index_reviews(reviews_df: pd.DataFrame, batch_size: int = 128) -> int:
    """Embed and upsert all reviews into Chroma. Returns number of docs indexed."""
    col      = _get_collection()
    embedder = _get_embedder()

    docs, metas, ids = [], [], []
    for _, row in reviews_df.iterrows():
        body = str(row.get("body", "")).strip()
        if not body:
            continue
        doc_id = _doc_id(str(row.get("asin", "")), body)
        docs.append(body)
        metas.append({
            "brand":   str(row.get("brand", "")),
            "asin":    str(row.get("asin", "")),
            "rating":  float(row.get("rating", 0)),
            "label":   str(row.get("sentiment_label", "neutral")),
        })
        ids.append(doc_id)

    if not docs:
        logger.warning("No documents to index.")
        return 0

    # Batch embed
    total = 0
    for i in range(0, len(docs), batch_size):
        batch_docs  = docs[i: i + batch_size]
        batch_metas = metas[i: i + batch_size]
        batch_ids   = ids[i: i + batch_size]

        embeddings = embedder.encode(batch_docs, show_progress_bar=False).tolist()
        col.upsert(
            documents=batch_docs,
            embeddings=embeddings,
            metadatas=batch_metas,
            ids=batch_ids,
        )
        total += len(batch_docs)
        logger.info(f"Indexed {total}/{len(docs)} reviews...")

    logger.info(f"Chroma index: {col.count()} total documents")
    return total


# ── Querying ──────────────────────────────────────────────────────────────────

def query_reviews(
    query: str,
    brand: str | None = None,
    n_results: int = 10,
    sentiment: str | None = None,
) -> list[dict]:
    """
    Semantic search over review corpus.
    Returns list of {body, brand, asin, rating, label, distance}.
    """
    col      = _get_collection()
    embedder = _get_embedder()

    if col.count() == 0:
        logger.warning("Chroma collection is empty. Index reviews first.")
        return []

    query_vec = embedder.encode([query]).tolist()
    where: dict = {}
    if brand:
        where["brand"] = {"$eq": brand}
    if sentiment:
        where["label"] = {"$eq": sentiment}

    kwargs = dict(
        query_embeddings=query_vec,
        n_results=min(n_results, col.count()),
    )
    if where:
        kwargs["where"] = where

    results = col.query(**kwargs)

    output = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        output.append({
            "body":     doc,
            "brand":    meta.get("brand", ""),
            "asin":     meta.get("asin", ""),
            "rating":   meta.get("rating", 0),
            "label":    meta.get("label", "neutral"),
            "distance": round(dist, 4),
        })

    return output


def get_collection_stats() -> dict:
    col = _get_collection()
    return {
        "total_documents": col.count(),
        "collection_name": COLLECTION_NAME,
        "path": str(CHROMA_PATH),
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def run_indexing() -> int:
    reviews_path = DATA_PROCESSED_PATH / "reviews.csv"
    if not reviews_path.exists():
        raise FileNotFoundError("reviews.csv not found. Run cleaning first.")

    reviews_df = pd.read_csv(reviews_path)
    n = index_reviews(reviews_df)
    logger.info(f"Indexed {n} reviews into ChromaDB at {CHROMA_PATH}")
    return n


if __name__ == "__main__":
    run_indexing()
    # Quick test query
    results = query_reviews("wheels breaking after one trip", n_results=5)
    for r in results:
        print(f"[{r['brand']}] {r['body'][:100]}...")
