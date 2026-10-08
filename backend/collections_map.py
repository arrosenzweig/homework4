"""
A second way to browse the catalogue: by Yale residential college or by
graduate and professional school.

`garment_type` answers "what kind of clothing is this". It does not answer the
question a lot of Yale shoppers actually arrive with — "what do you have for
Saybrook?" or "my daughter just started at the School of Nursing". Those are
affiliation questions, and the affiliation is buried in the product name,
description and tags where only free-text search could reach it.

This module reads that affiliation out into a structured field, so it can drive
a filter, a browse page, and an agent tool argument.

The two dimensions are independent: a Benjamin Franklin quarter-zip is in the
Quarter-Zips category *and* the Benjamin Franklin College collection.
"""

from __future__ import annotations

import re
from typing import Any

RESIDENTIAL_COLLEGE = "Residential College"
GRADUATE_SCHOOL = "Graduate & Professional School"

# Yale's fourteen residential colleges. Listed in full even where the catalogue
# currently carries nothing, so a new product is categorized the day it is added
# rather than the day someone remembers to update this file.
COLLEGES: list[str] = [
    "Benjamin Franklin",
    "Berkeley",
    "Branford",
    "Davenport",
    "Ezra Stiles",
    "Grace Hopper",
    "Jonathan Edwards",
    "Morse",
    "Pauli Murray",
    "Pierson",
    "Saybrook",
    "Silliman",
    "Timothy Dwight",
    "Trumbull",
]

# Graduate and professional schools, as the shop labels them. Each entry maps a
# display name to the patterns that identify it in product text.
SCHOOLS: dict[str, list[str]] = {
    "School of Architecture": [r"school of architecture", r"architecture school"],
    "School of Art": [r"school of art\b", r"art school"],
    "Divinity School": [r"divinity school", r"school of divinity"],
    "David Geffen School of Drama": [r"school of drama", r"drama school"],
    "School of Engineering & Applied Science": [
        r"school of engineering",
        r"engineering school",
        r"seas\b",
    ],
    "School of the Environment": [
        r"school of the environment",
        r"forest school",
        r"environment school",
    ],
    "Jackson School of Global Affairs": [r"jackson school", r"school of global affairs"],
    "Yale Law School": [r"law school", r"school of law"],
    "School of Management": [r"school of management", r"\bsom\b", r"management school"],
    "School of Medicine": [r"school of medicine", r"medical school"],
    "School of Music": [r"school of music", r"music school"],
    "School of Nursing": [r"school of nursing", r"nursing school"],
    "School of Public Health": [r"school of public health", r"public health school"],
    "Graduate School of Arts & Sciences": [r"graduate school of arts", r"\bgsas\b"],
}


def _searchable(product: dict[str, Any]) -> str:
    return " ".join(
        [
            product.get("name", ""),
            product.get("description", ""),
            " ".join(product.get("tags", [])),
            product.get("id", "").replace("-", " "),
        ]
    ).lower()


def classify(product: dict[str, Any]) -> tuple[str | None, str | None]:
    """
    Return (collection, collection_type) for a product, or (None, None).

    Schools are checked first. "Grace Hopper College" and the "School of
    Engineering" never collide, but checking the more specific multi-word
    school patterns first avoids a bare college name inside a longer school
    name claiming the product.
    """
    text = _searchable(product)

    for name, patterns in SCHOOLS.items():
        for pattern in patterns:
            if re.search(pattern, text):
                return name, GRADUATE_SCHOOL

    for college in COLLEGES:
        # Word-boundary match so "Morse" does not fire on "Morse code" in some
        # unrelated description, and "Art" style short names stay safe.
        if re.search(rf"\b{re.escape(college.lower())}\b", text):
            return f"{college} College", RESIDENTIAL_COLLEGE

    return None, None


def all_collections(products: list[dict[str, Any]]) -> dict[str, list[str]]:
    """
    Collections that actually have products, grouped by type.

    Only non-empty collections are returned — a filter listing a college with
    nothing behind it sends shoppers to an empty page.
    """
    grouped: dict[str, list[str]] = {RESIDENTIAL_COLLEGE: [], GRADUATE_SCHOOL: []}
    for product in products:
        name = product.get("collection")
        kind = product.get("collection_type")
        if name and kind in grouped and name not in grouped[kind]:
            grouped[kind].append(name)
    for kind in grouped:
        grouped[kind].sort()
    return grouped
