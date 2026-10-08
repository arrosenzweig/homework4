"""
Shared types for the Campus Customs API and agent.

Three groups live here:

  * Catalogue shapes      - ProductCard, the product payload the front end renders
  * Chat wire shapes      - ChatRequest / ChatResponse, what crosses the network
  * Agent shapes          - AgentReply, the structured output the model must produce,
                            and ChatDeps, what the agent's tools get handed at run time

The split between AgentReply and ChatResponse is deliberate. The model only ever
chooses *which* products to show, by id. The server then looks those ids up in
SQLite and fills in the real name, price and stock. That way a price on screen
always comes from the database and never from the model, so the agent cannot
invent one.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator

# --------------------------------------------------------------------------
# Catalogue
# --------------------------------------------------------------------------


class ProductCard(BaseModel):
    """One product, as the chat widget and product grid render it."""

    id: str
    name: str
    category: str
    garment_type: str
    description: str
    price: float
    image: str
    colors: list[str] = Field(default_factory=list)
    sizes_in_stock: list[str] = Field(
        default_factory=list, description="Sizes with at least one unit on hand"
    )
    total_stock: int = 0
    in_stock: bool = False
    collection: str | None = None
    collection_type: str | None = None
    url: str = Field(
        default="",
        description=(
            "Route to this product's detail page. Sent by the server rather than "
            "built in the browser, so the chat cards and the catalogue grid can "
            "never disagree about where a product lives."
        ),
    )

    @model_validator(mode="after")
    def _fill_derived(self) -> "ProductCard":
        if not self.url:
            self.url = f"/products/{self.id}"
        self.in_stock = self.total_stock > 0
        return self


# --------------------------------------------------------------------------
# Tool return types
#
# Every tool returns one of these rather than a bare dict. Two reasons:
# the model receives a predictable schema instead of guessing at key names,
# and a field that does not exist in the database cannot appear in a payload —
# so there is no slot for an invented price or quantity to travel in.
# --------------------------------------------------------------------------


class ProductSummary(BaseModel):
    """One row in a search result. Deliberately compact: search returns several."""

    id: str
    name: str
    category: str
    price: float = Field(description="Price in USD, straight from catalogue.price")
    colors: list[str] = Field(default_factory=list)
    sizes_in_stock: list[str] = Field(
        default_factory=list, description="Sizes with quantity > 0. Empty means sold out."
    )
    in_stock: bool = Field(description="True if any size has stock")
    description: str = Field(description="Truncated; call product_details for the full text")
    collection: str | None = Field(
        default=None,
        description="Residential college or graduate school this belongs to, if any",
    )
    collection_type: str | None = Field(
        default=None, description="'Residential College' or 'Graduate & Professional School'"
    )
    requested_size: str | None = Field(
        default=None, description="Set only when the search specified a size"
    )
    requested_size_quantity: int | None = Field(
        default=None,
        description=(
            "Units on hand in the requested size. 0 means this product is NOT "
            "available in that size — say so rather than offering a different product."
        ),
    )


class SearchResults(BaseModel):
    """
    Wrapper around search hits.

    `total_matches` and `returned` are separate so the model can tell "nothing
    matched" from "there is more than I showed you", and `note` states the
    empty case in words so it cannot be read as a successful search.
    """

    results: list[ProductSummary] = Field(default_factory=list)
    total_matches: int = 0
    returned: int = 0
    note: str | None = None


class ProductDetail(BaseModel):
    """Everything known about one product, including stock in every size."""

    id: str
    name: str
    category: str
    garment_type: str
    description: str
    price: float
    colors: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    image: str
    stock: dict[str, int] = Field(description="Units on hand, keyed by size")
    sizes_in_stock: list[str] = Field(default_factory=list)
    total_stock: int
    in_stock: bool
    collection: str | None = None
    collection_type: str | None = None


class StockBySize(BaseModel):
    """Per-size availability for a single product."""

    product_id: str
    name: str
    stock: dict[str, int]
    sizes_in_stock: list[str] = Field(default_factory=list)
    total_stock: int
    sold_out: bool = Field(description="True when no size has any units left")


class SizeAvailability(BaseModel):
    """Availability of one product in one specific size."""

    product_id: str
    name: str
    size: str
    quantity: int = Field(description="Units on hand in this size. 0 means out of stock.")
    available: bool
    alternative_sizes: list[str] = Field(
        default_factory=list,
        description="Other sizes still in stock, to offer when the asked-for size is gone",
    )


class CategorySummary(BaseModel):
    """One category, with how much of it we have and what it costs."""

    category: str
    count: int
    in_stock: int = Field(description="How many products in this category have any stock")
    price_from: float
    price_to: float


class CollectionSummary(BaseModel):
    """One residential college or graduate school, with what we carry for it."""

    collection: str
    collection_type: str
    count: int
    in_stock: int
    price_from: float
    price_to: float


class NotFound(BaseModel):
    """Returned instead of null so a miss is explicit rather than an empty response."""

    found: bool = False
    product_id: str
    message: str


# --------------------------------------------------------------------------
# Chat wire format
# --------------------------------------------------------------------------


class ChatTurn(BaseModel):
    """One prior turn, replayed to give the agent conversational memory."""

    role: Literal["user", "assistant"]
    content: str
    products: list[ProductCard] = Field(
        default_factory=list, description="Cards shown with this turn, when restoring history"
    )
    created_at: str | None = None


class PageContext(BaseModel):
    """
    What the shopper is looking at when they send a message.

    Collected by the browser and sent with every turn, so the agent can answer
    "does this come in large?" without the shopper naming the product.
    """

    route: str = Field(default="/", description="Current path, e.g. /products/yale-dad-hoodie")
    page_type: Literal["home", "products", "product_detail", "account", "other"] = "other"
    product_id: str | None = Field(
        default=None, description="Set on a product detail page — the item being viewed"
    )
    product_name: str | None = None
    category: str | None = Field(default=None, description="Active category filter, if any")
    search_query: str | None = Field(default=None, description="Text typed into the grid search")
    visible_product_ids: list[str] = Field(
        default_factory=list,
        description="Up to 12 products currently rendered, so 'the third one' resolves",
    )


class ShopperIdentity(BaseModel):
    """Who the agent is talking to. Returned by the who_am_i tool."""

    signed_in: bool
    first_name: str | None = None
    name: str | None = None
    email: str | None = None
    note: str = Field(
        default="",
        description="Guidance for the agent about what it may do with this identity",
    )


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[ChatTurn] = Field(
        default_factory=list, description="Earlier turns, oldest first"
    )
    page: PageContext | None = Field(
        default=None, description="What the shopper is looking at right now"
    )


class ChatResponse(BaseModel):
    """What the front end receives. `products` is hydrated server-side."""

    reply: str
    products: list[ProductCard] = Field(default_factory=list)
    model: str


# --------------------------------------------------------------------------
# Agent
# --------------------------------------------------------------------------


class AgentReply(BaseModel):
    """
    The structured output the model is required to return.

    Note what is *absent*: no prices, no stock numbers, no product names. The
    model picks ids; the server supplies the facts.
    """

    message: str = Field(description="The reply to show the shopper, in plain prose")
    product_ids: list[str] = Field(
        default_factory=list,
        description=(
            "Ids of products to show as cards beneath the reply, at most 6. "
            "Use only ids returned by a tool in this conversation; never invent one."
        ),
    )


class ChatHistory(BaseModel):
    """Saved conversation returned when a signed-in shopper comes back."""

    turns: list[ChatTurn] = Field(default_factory=list)
    saved: bool = Field(description="False for guests, whose turns are not recorded")


@dataclass
class ChatDeps:
    """
    Handed to every tool call.

    Carries the database path, who is chatting, and what they are looking at —
    the three things a tool might need that are not in the message itself.
    """

    db_path: Path
    user_id: int | None = None
    user_name: str | None = None
    user_first_name: str | None = None
    user_email: str | None = None
    page: PageContext | None = None
    run_id: str = ""

    @property
    def signed_in(self) -> bool:
        return self.user_id is not None
