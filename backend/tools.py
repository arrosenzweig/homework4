"""
Tools the shopping agent can call, plus the catalogue reads the API shares with them.

Every tool reads SQLite directly. Nothing here takes free-form SQL from the
model — the agent chooses a category, a search term or a product id, and these
functions build the query. That keeps the model away from the database itself.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import collections_map
import search_terms
from models import (
    CategorySummary,
    CollectionSummary,
    NotFound,
    ProductCard,
    ProductDetail,
    ProductSummary,
    SearchResults,
    SizeAvailability,
    StockBySize,
)

SIZES = ["XS", "S", "M", "L", "XL", "XXL"]

CATEGORIES = ["Crewnecks", "Hoodies", "T-Shirts", "Quarter-Zips", "Jackets", "Long Sleeves"]


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def normalize_category(garment_type: str) -> str:
    """
    catalogue.garment_type holds 22 inconsistent labels for 102 products
    (casing varies, and 'hoodie' / 'pullover hoodie' / 'hooded sweatshirt'
    are the same thing to a shopper). Collapse them into browseable buckets.
    """
    g = garment_type.lower().strip()
    if "bomber" in g or "fleece jacket" in g or g == "jacket":
        return "Jackets"
    if "quarter-zip" in g:
        return "Quarter-Zips"
    if "hood" in g:
        return "Hoodies"
    if "crewneck" in g or "mockneck" in g:
        return "Crewnecks"
    if "t-shirt" in g or "tee" in g:
        return "T-Shirts"
    if "long-sleeve" in g or "performance" in g:
        return "Long Sleeves"
    return "Other"


def load_catalogue(db_path: Path) -> list[dict[str, Any]]:
    """Full catalogue joined with inventory. Used by both the REST API and the tools."""
    conn = connect(db_path)
    try:
        stock: dict[str, dict[str, int]] = {}
        for row in conn.execute("SELECT product_id, size, quantity FROM inventory"):
            stock.setdefault(row["product_id"], {})[row["size"]] = row["quantity"]

        products = []
        for row in conn.execute("SELECT * FROM catalogue ORDER BY name"):
            pid = row["product_id"]
            by_size = {s: stock.get(pid, {}).get(s, 0) for s in SIZES}
            product = {
                "id": pid,
                "name": row["name"],
                "garmentType": row["garment_type"],
                "category": normalize_category(row["garment_type"]),
                "description": row["description"],
                "colors": json.loads(row["colors"]),
                "tags": json.loads(row["search_tags"]),
                "image": "/" + row["image_file_path"],
                "price": row["price"],
                "stock": by_size,
                "totalStock": sum(by_size.values()),
            }
            collection, collection_type = collections_map.classify(product)
            product["collection"] = collection
            product["collection_type"] = collection_type
            products.append(product)
        return products
    finally:
        conn.close()


def to_card(p: dict[str, Any]) -> ProductCard:
    return ProductCard(
        id=p["id"],
        name=p["name"],
        category=p["category"],
        garment_type=p["garmentType"],
        description=p["description"],
        price=p["price"],
        image=p["image"],
        colors=p["colors"],
        sizes_in_stock=[s for s, q in p["stock"].items() if q > 0],
        total_stock=p["totalStock"],
        collection=p.get("collection"),
        collection_type=p.get("collection_type"),
    )


def cards_for_ids(db_path: Path, ids: list[str], limit: int = 6) -> list[ProductCard]:
    """
    Hydrate the ids the model chose into real product cards.

    Unknown ids are dropped rather than raising: if the model hallucinates an id,
    the shopper simply sees one fewer card instead of an error page.
    """
    by_id = {p["id"]: p for p in load_catalogue(db_path)}
    cards = []
    for pid in ids[:limit]:
        product = by_id.get(pid)
        if product is not None:
            cards.append(to_card(product))
    return cards


# --------------------------------------------------------------------------
# Agent tools
# --------------------------------------------------------------------------
#
# Each returns a typed model from models.py. The payloads are deliberately
# small — everything returned here is fed back into the model as context.
#
# Every price and quantity in these responses is read from SQLite on the spot.
# No value is cached, defaulted, or computed from anything but the database.

MAX_SEARCH_RESULTS = 6
DESCRIPTION_SNIPPET = 180


def _sizes_in_stock(stock: dict[str, int]) -> list[str]:
    """Preserve XS..XXL order rather than dict insertion order."""
    return [s for s in SIZES if stock.get(s, 0) > 0]


def search_products(
    db_path: Path,
    query: str | None = None,
    category: str | None = None,
    collection: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    size: str | None = None,
    in_stock_only: bool = True,
    limit: int = MAX_SEARCH_RESULTS,
) -> SearchResults:
    """
    Search the catalogue by free text, category, price band, and size availability.

    Free text is matched against name, description, category, search_tags and
    colors — see harness.md for why those five fields and not others.
    """
    products = load_catalogue(db_path)

    if category and category.lower() != "all":
        wanted = category.strip().lower()
        products = [p for p in products if p["category"].lower() == wanted]

    if collection:
        # Substring match so "Saybrook" finds "Saybrook College" and "Nursing"
        # finds "School of Nursing", without the caller knowing the exact label.
        wanted = collection.strip().lower()
        products = [
            p
            for p in products
            if p.get("collection") and wanted in p["collection"].lower()
        ]

    if min_price is not None:
        products = [p for p in products if p["price"] >= min_price]

    if max_price is not None:
        products = [p for p in products if p["price"] <= max_price]

    # A size filter is a stock question. How it is applied depends on whether the
    # shopper named a product.
    #
    # Browsing ("anything in XXL under $40") -> filter strictly; they only want
    # things they can buy.
    #
    # Naming a product ("is the Baseball crewneck in XL?") -> do NOT filter. If the
    # named product were dropped for being out of stock in that size, the only
    # results left would be *other* products, and the honest answer "no" would turn
    # into "yes, here is this other one". Instead keep every match, annotate it with
    # the true quantity in that size, and sort the available ones first.
    size_key = size.strip().upper() if size else None

    if size_key and not query:
        products = [p for p in products if p["stock"].get(size_key, 0) > 0]
    elif in_stock_only and not size_key:
        products = [p for p in products if p["totalStock"] > 0]

    if query:
        needle = query.strip().lower()
        # Normalize before matching: fold spelling variants and plurals onto the
        # catalogue's vocabulary, drop filler, and rescue typos. Without this,
        # "grey" and "hoodei" returned nothing from a shop full of matches.
        vocabulary = search_terms.build_vocabulary(products) if products else set()
        terms = search_terms.normalize_query(query, vocabulary)

        # If normalization removed everything (e.g. "do you have any?"), there is
        # nothing to search on — fall back to the raw words rather than matching all.
        if not terms:
            terms = [t for t in needle.split() if len(t) >= search_terms.MIN_TERM_LENGTH]

        # The full-phrase bonus should use the normalized phrase too.
        needle = " ".join(terms) if terms else needle

        def score(p: dict[str, Any]) -> int:
            # Weighted so a name match outranks a stray word in a tag list.
            name = p["name"].lower()
            tags = " ".join(p["tags"]).lower()
            colors = " ".join(p["colors"]).lower()
            body = f'{p["description"]} {p["category"]}'.lower()

            total = 0
            if needle in name:
                total += 50
            if needle in tags or needle in body or needle in colors:
                total += 20
            for t in terms:
                if t in name:
                    total += 8
                if t in tags:
                    total += 4
                if t in body:
                    total += 3
                if t in colors:
                    total += 3
            return total

        scored = [(score(p), p) for p in products]
        # Relevance leads. Availability only breaks ties, so the product the
        # shopper actually named always outranks a loosely-related item that
        # happens to be in stock — otherwise an exact match with 0 units gets
        # buried and the honest "no" never reaches them.
        if size_key:
            products = [
                p
                for sc, p in sorted(
                    scored, key=lambda sp: (-sp[0], -(sp[1]["stock"].get(size_key, 0) > 0))
                )
                if sc > 0
            ]
        else:
            products = [p for sc, p in sorted(scored, key=lambda sp: -sp[0]) if sc > 0]

    total = len(products)
    hits = products[:limit]

    note = None
    if total == 0:
        note = (
            "No products in the catalogue match that. Do not suggest anything here; "
            "say we do not carry it and offer a different search."
        )
    elif size_key and any(p["stock"].get(size_key, 0) == 0 for p in hits):
        note = (
            f"Some of these have 0 in {size_key} (see requested_size_quantity). "
            f"If the shopper asked about a specific product in {size_key} and its "
            "quantity is 0, tell them it is out of stock in that size."
        )
    elif total > len(hits):
        note = f"Showing {len(hits)} of {total} matches."

    return SearchResults(
        results=[
            ProductSummary(
                id=p["id"],
                name=p["name"],
                category=p["category"],
                price=p["price"],
                colors=p["colors"],
                sizes_in_stock=_sizes_in_stock(p["stock"]),
                in_stock=p["totalStock"] > 0,
                description=p["description"][:DESCRIPTION_SNIPPET],
                collection=p.get("collection"),
                collection_type=p.get("collection_type"),
                requested_size=size_key,
                requested_size_quantity=(
                    p["stock"].get(size_key, 0) if size_key else None
                ),
            )
            for p in hits
        ],
        total_matches=total,
        returned=len(hits),
        note=note,
    )


def get_product_details(db_path: Path, product_id: str) -> ProductDetail | NotFound:
    """Everything known about one product, including per-size stock."""
    for p in load_catalogue(db_path):
        if p["id"] == product_id:
            return ProductDetail(
                id=p["id"],
                name=p["name"],
                category=p["category"],
                garment_type=p["garmentType"],
                description=p["description"],
                price=p["price"],
                colors=p["colors"],
                tags=p["tags"],
                image=p["image"],
                stock=p["stock"],
                sizes_in_stock=_sizes_in_stock(p["stock"]),
                total_stock=p["totalStock"],
                in_stock=p["totalStock"] > 0,
                collection=p.get("collection"),
                collection_type=p.get("collection_type"),
            )
    return NotFound(
        product_id=product_id,
        message=(
            f"No product with id {product_id!r}. Do not describe it or guess a price; "
            "search the catalogue instead."
        ),
    )


def check_stock(
    db_path: Path, product_id: str, size: str | None = None
) -> StockBySize | SizeAvailability | NotFound:
    """Availability for a product, optionally narrowed to one size."""
    for p in load_catalogue(db_path):
        if p["id"] == product_id:
            available = _sizes_in_stock(p["stock"])

            if size:
                key = size.strip().upper()
                qty = p["stock"].get(key, 0)
                return SizeAvailability(
                    product_id=p["id"],
                    name=p["name"],
                    size=key,
                    quantity=qty,
                    available=qty > 0,
                    alternative_sizes=[s for s in available if s != key] if qty == 0 else [],
                )

            return StockBySize(
                product_id=p["id"],
                name=p["name"],
                stock=p["stock"],
                sizes_in_stock=available,
                total_stock=p["totalStock"],
                sold_out=p["totalStock"] == 0,
            )

    return NotFound(
        product_id=product_id,
        message=f"No product with id {product_id!r}. Do not state a quantity for it.",
    )


def list_categories(db_path: Path) -> list[CategorySummary]:
    """Category names with how many products each holds and the price range."""
    products = load_catalogue(db_path)
    out = []
    for cat in CATEGORIES:
        items = [p for p in products if p["category"] == cat]
        if not items:
            continue
        prices = [p["price"] for p in items]
        out.append(
            CategorySummary(
                category=cat,
                count=len(items),
                in_stock=sum(1 for p in items if p["totalStock"] > 0),
                price_from=min(prices),
                price_to=max(prices),
            )
        )
    return out


def list_collections(db_path: Path) -> list[CollectionSummary]:
    """Residential colleges and graduate schools that have products behind them."""
    products = load_catalogue(db_path)
    grouped = collections_map.all_collections(products)

    out: list[CollectionSummary] = []
    for kind, names in grouped.items():
        for name in names:
            items = [p for p in products if p.get("collection") == name]
            if not items:
                continue
            prices = [p["price"] for p in items]
            out.append(
                CollectionSummary(
                    collection=name,
                    collection_type=kind,
                    count=len(items),
                    in_stock=sum(1 for p in items if p["totalStock"] > 0),
                    price_from=min(prices),
                    price_to=max(prices),
                )
            )
    return out
