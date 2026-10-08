"""
The Campus Customs shopping agent.

Built with Pydantic AI. Three things are assembled here:

  1. The model      - reached through the Portkey gateway, which speaks the
                      OpenAI chat-completions protocol
  2. The prompt     - read from prompts/prompt.md at import time, never inlined
                      in Python, so the shop's voice can be edited without
                      touching code
  3. The tools      - thin wrappers over tools.py that hand each call the
                      database path from the run's dependencies

The agent is created once at import and reused for every request.
"""

from __future__ import annotations

import functools
import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, ParamSpec, TypeVar
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai import Agent, RunContext
from pydantic_ai.usage import UsageLimits
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

import audit
import tools
from models import (
    AgentReply,
    CategorySummary,
    ChatDeps,
    CollectionSummary,
    NotFound,
    PageContext,
    ProductDetail,
    SearchResults,
    ShopperIdentity,
    SizeAvailability,
    StockBySize,
)

# --------------------------------------------------------------------------
# Paths — all resolved from this file, never from the working directory, so
# `uvicorn main:app` from backend/ and `uvicorn backend.main:app` from HW 4/
# both find the same prompt and database.
# --------------------------------------------------------------------------

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent
PROMPT_PATH = BACKEND_DIR / "prompts" / "prompt.md"
DB_PATH = PROJECT_DIR / "data" / "campus_customs.db"

# PORTKEY_API_KEY lives in the repository root .env, two levels up.
load_dotenv(PROJECT_DIR.parent / ".env")
load_dotenv(PROJECT_DIR / ".env")

PORTKEY_BASE_URL = os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1")
PORTKEY_API_KEY = os.getenv("PORTKEY_API_KEY")

# The gateway pins the deployment, so this string is a label for logs and the
# /api/chat response rather than a routing decision.
MODEL_NAME = os.getenv("CHAT_MODEL", "gpt-5.6-luna")

# --------------------------------------------------------------------------
# Loop ceilings — the guard against a runaway agent.
#
# A tool-calling agent decides for itself how many times to go round the loop.
# A confused one can call tools indefinitely, and every pass is a billed
# request. These are hard stops enforced by Pydantic AI, not suggestions in
# the prompt: when a limit is hit the run raises and the turn ends.
# --------------------------------------------------------------------------

MAX_MODEL_REQUESTS = 8      # round trips to the model in one turn
MAX_TOOL_CALLS = 12         # tool invocations in one turn
MAX_TOTAL_TOKENS = 60_000   # prompt + completion tokens in one turn

USAGE_LIMITS = UsageLimits(
    request_limit=MAX_MODEL_REQUESTS,
    tool_calls_limit=MAX_TOOL_CALLS,
    total_tokens_limit=MAX_TOTAL_TOKENS,
)


def load_prompt() -> str:
    """Read the system prompt from disk."""
    if not PROMPT_PATH.exists():
        raise FileNotFoundError(f"system prompt not found at {PROMPT_PATH}")
    return PROMPT_PATH.read_text(encoding="utf-8")


def build_model() -> OpenAIChatModel:
    """
    Point Pydantic AI at Portkey.

    Portkey is OpenAI-compatible, so the OpenAI model class works unchanged; only
    the base URL and the auth header differ. The key is sent as `x-portkey-api-key`.
    """
    if not PORTKEY_API_KEY:
        raise RuntimeError(
            "PORTKEY_API_KEY is not set. Add it to the repository root .env file."
        )

    # Portkey authenticates on its own `x-portkey-api-key` header rather than the
    # standard Authorization bearer, so build the OpenAI client explicitly with
    # that default header and hand it to the provider.
    client = AsyncOpenAI(
        base_url=PORTKEY_BASE_URL,
        api_key=PORTKEY_API_KEY,
        default_headers={"x-portkey-api-key": PORTKEY_API_KEY},
    )
    return OpenAIChatModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))


agent = Agent(
    build_model(),
    deps_type=ChatDeps,
    output_type=AgentReply,
    system_prompt=load_prompt(),
    retries=2,
)


# --------------------------------------------------------------------------
# Tools
#
# Docstrings and signatures are what the model sees, so they are written for
# the model, not for a Python reader.
#
# Each one is wrapped by `audited`, which times the call and appends a record
# to the audit trail. The wrapper is transparent to the model: it does not
# change the signature the agent sees or the value it receives.
# --------------------------------------------------------------------------

_P = ParamSpec("_P")
_R = TypeVar("_R")


def audited(fn: Callable[_P, _R]) -> Callable[_P, _R]:
    """Time a tool call and log it against the run that made it."""

    @functools.wraps(fn)
    def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _R:
        ctx = args[0] if args else None
        run_id = getattr(getattr(ctx, "deps", None), "run_id", None) or "unknown"
        started = time.perf_counter()
        try:
            result = fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 - record the failure, then re-raise
            audit.write(
                "tool.error",
                run_id=run_id,
                tool=fn.__name__,
                error=str(exc)[:200],
                duration_ms=round((time.perf_counter() - started) * 1000, 1),
            )
            raise
        audit.tool_called(
            run_id,
            fn.__name__,
            dict(kwargs),
            result,
            (time.perf_counter() - started) * 1000,
        )
        return result

    return wrapper


@agent.tool
@audited
def search_catalogue(
    ctx: RunContext[ChatDeps],
    query: str | None = None,
    category: str | None = None,
    collection: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    size: str | None = None,
    in_stock_only: bool = True,
) -> SearchResults:
    """
    Search the Campus Customs catalogue. Use this for any question about what we
    carry, what it costs, or what is available.

    Free text is matched against the product name, description, category, search
    tags and colors.

    Args:
        query: Free text — a sport, residential college, color, occasion, garment,
            or anything from the product description.
        category: One of Crewnecks, Hoodies, T-Shirts, Quarter-Zips, Jackets, Long Sleeves.
        collection: A Yale residential college or graduate school, e.g. "Saybrook",
            "Grace Hopper", "School of Nursing", "Law". Use this whenever a shopper
            names their college or school — it is far more reliable than putting the
            name in `query`. Call `collections` if you need the exact list.
        min_price: Only products at or above this price in dollars.
        max_price: Only products at or below this price in dollars.
        size: One of XS, S, M, L, XL, XXL. Returns only products with that size
            actually on the shelf — use it when a shopper names their size.
        in_stock_only: Leave True unless the shopper asks about something sold out.

    Returns up to 6 products with real prices and the sizes currently in stock,
    plus total_matches so you know whether there were more. If total_matches is 0,
    we do not carry it — say so rather than suggesting a substitute as if it matched.
    """
    return tools.search_products(
        ctx.deps.db_path,
        query=query,
        category=category,
        collection=collection,
        min_price=min_price,
        max_price=max_price,
        size=size,
        in_stock_only=in_stock_only,
    )


@agent.tool
@audited
def product_details(ctx: RunContext[ChatDeps], product_id: str) -> ProductDetail | NotFound:
    """
    Everything about one product: full description, exact price, colors, and the
    quantity on hand in every size.

    Call this before answering a specific question about one item. Never describe
    a product's price or fabric from memory.

    Args:
        product_id: An id from a previous search, e.g. "yale-dad-hoodie".

    Returns a NotFound with found=false if no product has that id.
    """
    return tools.get_product_details(ctx.deps.db_path, product_id)


@agent.tool
@audited
def stock_for_product(
    ctx: RunContext[ChatDeps], product_id: str, size: str | None = None
) -> StockBySize | SizeAvailability | NotFound:
    """
    Check how many units we have. This is the only way to answer a stock question.

    Args:
        product_id: An id from a previous search.
        size: Optional — one of XS, S, M, L, XL, XXL. Omit to get every size.

    With a size, returns the exact quantity, whether it is available, and which
    other sizes are left if that one is gone. Without a size, returns the count
    for all six sizes and a sold_out flag. A quantity of 0 means out of stock:
    say so plainly.
    """
    return tools.check_stock(ctx.deps.db_path, product_id, size)


@agent.tool
@audited
def categories(ctx: RunContext[ChatDeps]) -> list[CategorySummary]:
    """
    The categories we sell, with how many products each holds, how many are in
    stock, and the real price range for each.

    Good for opening questions like "what do you have?" or "what's cheapest?".
    """
    return tools.list_categories(ctx.deps.db_path)


@agent.tool
@audited
def collections(ctx: RunContext[ChatDeps]) -> list[CollectionSummary]:
    """
    The Yale residential colleges and graduate or professional schools we carry
    gear for, with how many products each has and its price range.

    Use this when a shopper asks what colleges or schools you stock, or when you
    need the exact label for a college or school before searching. A college or
    school with no products will not appear here — if theirs is missing, we do
    not carry it, and you should say so plainly.
    """
    return tools.list_collections(ctx.deps.db_path)


@agent.tool
@audited
def who_am_i(ctx: RunContext[ChatDeps]) -> ShopperIdentity:
    """
    Who you are talking to.

    Returns the shopper's first name, full name and email when they are signed
    in, or signed_in=false for a guest. Use the first name to greet them warmly
    once — do not repeat it in every reply, and never read their email back to
    them unless they ask what address is on the account.
    """
    deps = ctx.deps
    if not deps.signed_in:
        return ShopperIdentity(
            signed_in=False,
            note=(
                "This shopper is browsing as a guest. Help them normally. Do not ask "
                "them to log in unless they ask about saving anything."
            ),
        )
    return ShopperIdentity(
        signed_in=True,
        first_name=deps.user_first_name,
        name=deps.user_name,
        email=deps.user_email,
        note=(
            "Signed-in shopper. You may greet them by first name. Do not state their "
            "email unless they ask. You cannot see their orders — only their name and "
            "email are available to you."
        ),
    )


@agent.tool
@audited
def current_page(ctx: RunContext[ChatDeps]) -> PageContext:
    """
    What the shopper is looking at on the website right now.

    Call this when a message uses words like "this", "it", "this one", or
    "these" without naming a product. On a product detail page, product_id is
    the item on screen — pass it to product_details or stock_for_product to
    answer about it. On the products page, category and search_query say how
    the grid is filtered, and visible_product_ids lists what is on screen in
    order, so "the third one" can be resolved.
    """
    return ctx.deps.page or PageContext()


# --------------------------------------------------------------------------
# Entry point used by the API
# --------------------------------------------------------------------------


def build_conversation(message: str, history: list[tuple[str, str]]) -> str:
    """
    Flatten prior turns into the prompt.

    Pydantic AI can replay typed message history, but the browser sends plain
    role/content pairs, so the simplest faithful thing is to prepend a short
    transcript. Only the last few turns are kept to bound prompt growth.
    """
    if not history:
        return message

    recent = history[-6:]
    lines = [f"{'Shopper' if role == 'user' else 'You'}: {content}" for role, content in recent]
    transcript = "\n".join(lines)
    return f"Earlier in this conversation:\n{transcript}\n\nShopper: {message}"


async def run_agent(
    message: str,
    history: list[tuple[str, str]] | None = None,
    deps: ChatDeps | None = None,
) -> AgentReply:
    """
    Run one turn and return the model's structured reply.

    `deps` carries identity, page context and the audit run id into the tools.
    When omitted the agent runs as an anonymous shopper with no page context,
    which is what a direct API call or a test gets.

    The run is bounded by USAGE_LIMITS. Hitting a ceiling raises, which the
    caller records as a `usage_limit` stop reason — a runaway loop ends as a
    logged refusal rather than an open-ended bill.
    """
    deps = deps or ChatDeps(db_path=DB_PATH)
    if not deps.run_id:
        deps.run_id = audit.new_run_id()

    prompt = build_conversation(message, history or [])
    result = await agent.run(prompt, deps=deps, usage_limits=USAGE_LIMITS)
    return result


def reply_of(result: Any) -> AgentReply:
    """The structured output from a run result."""
    return result.output
