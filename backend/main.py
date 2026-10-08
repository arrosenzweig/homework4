"""
Campus Customs backend.

Serves the product catalogue, product images, accounts and the shopping agent
for the React front end in frontend/.

Run from the backend/ directory:

    uvicorn main:app --reload --port 8000

Endpoints:
    GET  /api/health                 service + catalogue status
    GET  /api/products               full catalogue (optional ?category=&q=&in_stock=)
    GET  /api/products/{product_id}  one product
    GET  /api/categories             normalized category list
    GET  /api/collections            residential colleges + graduate schools
    GET  /products/{filename}        product image (static files)

    POST /api/auth/signup            create an account
    POST /api/auth/login             exchange email + password for a session token
    POST /api/auth/logout            revoke the current session token
    GET  /api/auth/me                the signed-in user

    POST /api/chat                   send a message to the shopping agent
    GET  /api/chat/history           saved conversation for the signed-in shopper
    DELETE /api/chat/history         clear it
"""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import audit
import limits
import tools
from agent import DB_PATH as AGENT_DB_PATH  # noqa: F401  (same file; keeps paths honest)
from agent import (
    MAX_MODEL_REQUESTS,
    MAX_TOOL_CALLS,
    MAX_TOTAL_TOKENS,
    MODEL_NAME,
    PROMPT_PATH,
    reply_of,
    run_agent,
)
from auth import (
    hash_password,
    needs_rehash,
    new_session_token,
    normalize_email,
    validate_signup,
    verify_password,
)
from models import ChatDeps, ChatHistory, ChatRequest, ChatResponse, ChatTurn

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "campus_customs.db"
IMAGE_DIR = BASE_DIR / "data" / "products"

SIZES = ["XS", "S", "M", "L", "XL", "XXL"]

logger = logging.getLogger("campus_customs")

app = FastAPI(title="Campus Customs API", version="0.1.0")

# The Vite dev server runs on a different origin, so the browser needs CORS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if IMAGE_DIR.is_dir():
    app.mount("/products", StaticFiles(directory=IMAGE_DIR), name="products")


def connect() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise HTTPException(status_code=500, detail=f"database not found at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_auth_tables() -> None:
    """Session storage. The users table already ships with the seed database."""
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                token      TEXT PRIMARY KEY,
                user_id    INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


if DB_PATH.exists():
    init_auth_tables()


def normalize_category(garment_type: str) -> str:
    """Delegates to tools.normalize_category so the agent and the REST API agree."""
    return tools.normalize_category(garment_type)


def load_products() -> list[dict[str, Any]]:
    """Full catalogue joined with inventory. Single definition lives in tools.py."""
    if not DB_PATH.exists():
        raise HTTPException(status_code=500, detail=f"database not found at {DB_PATH}")
    return tools.load_catalogue(DB_PATH)


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "database": str(DB_PATH),
        "database_found": DB_PATH.exists(),
        "images_found": IMAGE_DIR.is_dir(),
        "products": len(load_products()) if DB_PATH.exists() else 0,
    }


@app.get("/api/products")
def list_products(
    category: str | None = Query(None, description="Normalized category, e.g. Hoodies"),
    collection: str | None = Query(None, description="Residential college or graduate school"),
    q: str | None = Query(None, description="Free-text search over name, description, tags, colors"),
    in_stock: bool = Query(False, description="Only products with at least one unit on hand"),
) -> list[dict[str, Any]]:
    products = load_products()

    if category and category != "All":
        products = [p for p in products if p["category"] == category]

    if collection:
        wanted = collection.strip().lower()
        products = [p for p in products if p.get("collection") and wanted in p["collection"].lower()]

    if in_stock:
        products = [p for p in products if p["totalStock"] > 0]

    if q:
        needle = q.lower()
        products = [
            p
            for p in products
            if needle in p["name"].lower()
            or needle in p["description"].lower()
            or any(needle in t.lower() for t in p["tags"])
            or any(needle in c.lower() for c in p["colors"])
        ]

    return products


@app.get("/api/collections")
def list_collections() -> list[dict[str, Any]]:
    """Residential colleges and graduate schools that have products."""
    return [c.model_dump() for c in tools.list_collections(DB_PATH)]


@app.get("/api/categories")
def list_categories() -> list[str]:
    return sorted({p["category"] for p in load_products()})


@app.get("/api/products/{product_id}")
def get_product(product_id: str) -> dict[str, Any]:
    for p in load_products():
        if p["id"] == product_id:
            return p
    raise HTTPException(status_code=404, detail=f"no product with id {product_id!r}")


# --------------------------------------------------------------------------
# Authentication
# --------------------------------------------------------------------------


class SignupRequest(BaseModel):
    firstName: str
    lastName: str
    email: str
    password: str
    confirmPassword: str


class LoginRequest(BaseModel):
    email: str
    password: str


class PublicUser(BaseModel):
    """What we are willing to send to the browser. Never the password hash."""

    id: int
    firstName: str | None
    lastName: str | None
    name: str
    email: str
    createdAt: str


class AuthResponse(BaseModel):
    token: str
    user: PublicUser


def to_public_user(row: sqlite3.Row) -> PublicUser:
    return PublicUser(
        id=row["id"],
        firstName=row["first_name"],
        lastName=row["last_name"],
        name=row["name"],
        email=row["email"],
        createdAt=row["created_at"],
    )


def current_user(authorization: str | None = Header(default=None)) -> sqlite3.Row:
    """Resolve the Bearer token on the request to a user row, or 401."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Not signed in.")
    token = authorization.split(" ", 1)[1].strip()

    conn = connect()
    try:
        row = conn.execute(
            """
            SELECT users.* FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.token = ?
            """,
            (token,),
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        raise HTTPException(status_code=401, detail="Session expired. Please log in again.")
    return row


@app.post("/api/auth/signup", response_model=AuthResponse, status_code=201)
def signup(body: SignupRequest) -> AuthResponse:
    error = validate_signup(
        body.firstName, body.lastName, body.email, body.password, body.confirmPassword
    )
    if error:
        raise HTTPException(status_code=400, detail=error)

    email = normalize_email(body.email)
    first = body.firstName.strip()
    last = body.lastName.strip()

    conn = connect()
    try:
        taken = conn.execute("SELECT 1 FROM users WHERE lower(email) = ?", (email,)).fetchone()
        if taken:
            raise HTTPException(status_code=409, detail="An account with that email already exists.")

        cursor = conn.execute(
            """
            INSERT INTO users (name, email, password_hash, first_name, last_name, created_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
            """,
            (f"{first} {last}", email, hash_password(body.password), first, last),
        )
        user_id = cursor.lastrowid

        token = new_session_token()
        conn.execute("INSERT INTO sessions (token, user_id) VALUES (?, ?)", (token, user_id))
        conn.commit()

        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return AuthResponse(token=token, user=to_public_user(row))
    finally:
        conn.close()


@app.post("/api/auth/login", response_model=AuthResponse)
def login(body: LoginRequest) -> AuthResponse:
    email = normalize_email(body.email)

    conn = connect()
    try:
        row = conn.execute("SELECT * FROM users WHERE lower(email) = ?", (email,)).fetchone()

        # One message for both "no such email" and "wrong password", so the
        # response cannot be used to find out which addresses are registered.
        if row is None or not verify_password(body.password, row["password_hash"]):
            raise HTTPException(status_code=401, detail="Incorrect email or password.")

        # Transparently upgrade credentials stored with older parameters.
        if needs_rehash(row["password_hash"]):
            conn.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (hash_password(body.password), row["id"]),
            )

        token = new_session_token()
        conn.execute("INSERT INTO sessions (token, user_id) VALUES (?, ?)", (token, row["id"]))
        conn.commit()

        return AuthResponse(token=token, user=to_public_user(row))
    finally:
        conn.close()


@app.post("/api/auth/logout", status_code=204)
def logout(authorization: str | None = Header(default=None)) -> None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return
    token = authorization.split(" ", 1)[1].strip()
    conn = connect()
    try:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
    finally:
        conn.close()


@app.get("/api/auth/me", response_model=PublicUser)
def me(user: sqlite3.Row = Depends(current_user)) -> PublicUser:
    return to_public_user(user)


# --------------------------------------------------------------------------
# Chat
# --------------------------------------------------------------------------


def optional_user(authorization: str | None = Header(default=None)) -> sqlite3.Row | None:
    """
    Resolve the caller if they sent a valid session token, else None.

    Unlike `current_user` this never raises: chat is open to guests, so a missing
    or stale token just means "not signed in" rather than an error.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        return None

    conn = connect()
    try:
        return conn.execute(
            """
            SELECT users.* FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.token = ?
            """,
            (token,),
        ).fetchone()
    finally:
        conn.close()


def save_turn(
    user_id: int,
    role: str,
    content: str,
    products: list[Any] | None = None,
) -> None:
    """
    Append one turn to chat_messages.

    Only called for signed-in shoppers — a guest's conversation is never written
    to the database. `products_json` stores the cards shown with an assistant
    turn so the thread can be restored exactly as it looked.
    """
    payload = None
    if products:
        payload = json.dumps([p.model_dump() for p in products])

    conn = connect()
    try:
        conn.execute(
            """
            INSERT INTO chat_messages (user_id, role, content, products_json, created_at)
            VALUES (?, ?, ?, ?, datetime('now'))
            """,
            (user_id, role, content, payload),
        )
        conn.commit()
    finally:
        conn.close()


@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    request: Request,
    response: Response,
    user: sqlite3.Row | None = Depends(optional_user),
) -> ChatResponse:
    """
    One turn with the shopping agent.

    The agent returns prose plus a list of product ids. The ids are hydrated here,
    from SQLite, into full product cards — so the name, price and stock the shopper
    sees always come from the database rather than from the model.

    Signed-in shoppers have both turns written to chat_messages. Guests may chat
    freely; nothing is recorded.
    """
    message = body.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    run_id = audit.new_run_id()
    started = audit.turn_started(
        run_id, message, user["id"] if user else None, body.page
    )

    # Every turn costs a gateway call, so cap how fast one shopper can spend them.
    key = limits.caller_key(
        user["id"] if user else None,
        request.client.host if request.client else None,
    )
    allowed, retry_after = limits.chat_limiter.check(key)
    if not allowed:
        logger.info("chat rate limit hit for %s", key)
        audit.turn_finished(run_id, started, "rate_limited", error=f"retry_after={retry_after}s")
        raise HTTPException(
            status_code=429,
            detail=(
                "You have sent a lot of messages in a short time. "
                f"Give it about {retry_after} seconds and try again."
            ),
            headers={"Retry-After": str(retry_after)},
        )
    response.headers["X-RateLimit-Limit"] = str(limits.MAX_TURNS)

    history = [(turn.role, turn.content) for turn in body.history]

    deps = ChatDeps(
        db_path=DB_PATH,
        user_id=user["id"] if user else None,
        user_name=user["name"] if user else None,
        user_first_name=(user["first_name"] or (user["name"] or "").split(" ")[0])
        if user
        else None,
        user_email=user["email"] if user else None,
        page=body.page,
        run_id=run_id,
    )

    try:
        # Bound the wait. Without this a stalled gateway leaves the widget
        # spinning indefinitely with no way out but a page reload.
        result = await asyncio.wait_for(
            run_agent(message, history, deps=deps),
            timeout=limits.AGENT_TIMEOUT_SECONDS,
        )
        reply = reply_of(result)
    except (asyncio.TimeoutError, TimeoutError):
        logger.warning("chat turn timed out after %ss", limits.AGENT_TIMEOUT_SECONDS)
        audit.turn_finished(run_id, started, "timeout")
        raise HTTPException(
            status_code=504,
            detail=(
                "That took longer than expected and I had to stop waiting. "
                "Please try asking again."
            ),
        ) from None
    except Exception as exc:  # noqa: BLE001 - the widget must stay usable
        text = str(exc)
        logger.warning("chat turn failed: %s", text)

        # A usage ceiling was hit — the loop ran away and was stopped.
        if "UsageLimit" in type(exc).__name__ or "limit" in text.lower() and "token" in text.lower():
            audit.turn_finished(run_id, started, "usage_limit", error=text)
            return ChatResponse(
                reply=(
                    "That question took me further than I can go in one step. "
                    "Could you narrow it down a little?"
                ),
                products=[],
                model=MODEL_NAME,
            )

        # The upstream provider runs its own content filter and rejects some
        # inputs with a 400. That is a refusal, not an outage, so answer in
        # character rather than showing the shopper a broken widget.
        if "content_filter" in text or "content management policy" in text:
            audit.turn_finished(run_id, started, "content_filter", error=text)
            return ChatResponse(
                reply=(
                    "I am not able to help with that one. If you tell me what you are "
                    "shopping for, I can point you to something from the shop."
                ),
                products=[],
                model=MODEL_NAME,
            )

        # Anything else is a genuine failure. Keep provider internals server-side.
        audit.turn_finished(run_id, started, "error", error=text)
        raise HTTPException(
            status_code=502,
            detail="The assistant is unavailable right now. Please try again in a moment.",
        ) from exc

    cards = tools.cards_for_ids(DB_PATH, reply.product_ids)

    audit.turn_finished(
        run_id,
        started,
        "completed",
        reply=reply.message,
        product_ids=[c.id for c in cards],
        usage=getattr(result, 'usage', None),
    )

    if user is not None:
        save_turn(user["id"], "user", message)
        save_turn(user["id"], "assistant", reply.message, cards)

    return ChatResponse(
        reply=reply.message,
        products=cards,
        model=MODEL_NAME,
    )


@app.get("/api/chat/info")
def chat_info() -> dict[str, Any]:
    """Where the agent's configuration came from. Useful for the write-up and debugging."""
    return {
        "model": MODEL_NAME,
        "prompt_file": str(PROMPT_PATH),
        "prompt_bytes": PROMPT_PATH.stat().st_size if PROMPT_PATH.exists() else 0,
        "tools": [
            "search_catalogue",
            "product_details",
            "stock_for_product",
            "categories",
            "collections",
            "who_am_i",
            "current_page",
        ],
        "limits": {
            "max_model_requests_per_turn": MAX_MODEL_REQUESTS,
            "max_tool_calls_per_turn": MAX_TOOL_CALLS,
            "max_total_tokens_per_turn": MAX_TOTAL_TOKENS,
            "agent_timeout_seconds": limits.AGENT_TIMEOUT_SECONDS,
            "turns_per_window": limits.MAX_TURNS,
            "window_seconds": limits.WINDOW_SECONDS,
            "max_search_results": tools.MAX_SEARCH_RESULTS,
        },
        "audit_trail": str(audit.AUDIT_PATH),
    }


@app.get("/api/chat/history", response_model=ChatHistory)
def chat_history(user: sqlite3.Row | None = Depends(optional_user)) -> ChatHistory:
    """
    The signed-in shopper's saved conversation, oldest first.

    Guests get an empty thread and `saved: false` — nothing was ever recorded
    for them, so there is nothing to return.
    """
    if user is None:
        return ChatHistory(turns=[], saved=False)

    conn = connect()
    try:
        rows = conn.execute(
            """
            SELECT role, content, products_json, created_at
            FROM chat_messages
            WHERE user_id = ?
            ORDER BY id ASC
            LIMIT 100
            """,
            (user["id"],),
        ).fetchall()
    finally:
        conn.close()

    turns = []
    for row in rows:
        products = []
        if row["products_json"]:
            try:
                raw = json.loads(row["products_json"])
                # Old seed rows store the catalogue shape; rebuild cards from the
                # live database by id so a restored thread shows current prices.
                ids = [p.get("product_id") or p.get("id") for p in raw if isinstance(p, dict)]
                products = tools.cards_for_ids(DB_PATH, [i for i in ids if i], limit=6)
            except (ValueError, TypeError):
                products = []

        turns.append(
            ChatTurn(
                role=row["role"],
                content=row["content"],
                products=products,
                created_at=row["created_at"],
            )
        )

    return ChatHistory(turns=turns, saved=True)


@app.delete("/api/chat/history", status_code=204)
def clear_chat_history(user: sqlite3.Row = Depends(current_user)) -> None:
    """Delete the signed-in shopper's saved conversation."""
    conn = connect()
    try:
        conn.execute("DELETE FROM chat_messages WHERE user_id = ?", (user["id"],))
        conn.commit()
    finally:
        conn.close()
