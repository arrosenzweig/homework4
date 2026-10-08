"""
Regenerate the front end's catalogue artefacts from the local data pack.

The data pack — `data/campus_customs.db` and `data/products/*.jpg` — is
distributed separately and is not in the repository. Two things derived from it
are therefore also git-ignored:

    frontend/src/data/products.json   the catalogue snapshot the pages read
    frontend/public/products/*.jpg    the product photographs

This script rebuilds both. Run it once after placing the data pack, before
starting the front end.

From the hw4/ directory:

    python backend/export_catalogue.py
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import tools  # noqa: E402  (needs the path set above)

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "campus_customs.db"
IMAGE_SRC = BASE_DIR / "data" / "products"
JSON_DEST = BASE_DIR / "frontend" / "src" / "data" / "products.json"
IMAGE_DEST = BASE_DIR / "frontend" / "public" / "products"


def main() -> int:
    if not DB_PATH.exists():
        print(f"ERROR: database not found at {DB_PATH}", file=sys.stderr)
        print("Place the data pack in hw4/data/ first.", file=sys.stderr)
        return 1

    catalogue = tools.load_catalogue(DB_PATH)

    rows = [
        {
            "id": p["id"],
            "name": p["name"],
            "garmentType": p["garmentType"],
            "category": p["category"],
            "description": p["description"],
            "colors": p["colors"],
            "tags": p["tags"],
            "image": p["image"],
            "price": p["price"],
            "stock": p["stock"],
            "totalStock": p["totalStock"],
            "collection": p.get("collection"),
            "collectionType": p.get("collection_type"),
        }
        for p in catalogue
    ]

    JSON_DEST.parent.mkdir(parents=True, exist_ok=True)
    JSON_DEST.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {JSON_DEST.relative_to(BASE_DIR)} ({len(rows)} products)")

    if not IMAGE_SRC.is_dir():
        print(f"WARNING: no image folder at {IMAGE_SRC}; product photos will be missing")
        return 0

    IMAGE_DEST.mkdir(parents=True, exist_ok=True)
    copied = 0
    missing = []
    for product in catalogue:
        name = Path(product["image"]).name
        src = IMAGE_SRC / name
        if src.exists():
            shutil.copy2(src, IMAGE_DEST / name)
            copied += 1
        else:
            missing.append(name)

    print(f"copied {copied} images to {IMAGE_DEST.relative_to(BASE_DIR)}")
    if missing:
        print(f"WARNING: {len(missing)} images missing from the data pack: {missing[:5]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
