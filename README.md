# HW 4 — Campus Customs

**Yale Bulldog Blue by Campus Customs** — a React + Vite + TypeScript storefront over a
SQLite catalogue, with a FastAPI backend and a Pydantic AI shopping assistant.

AI Foundations, Homework 4.

---

## Repository layout

```
hw4/
├── AI_prompts.md           every prompt given, organised by problem
├── requirements.txt        Python dependencies
├── .env.example            placeholders — copy to .env and fill in
├── .gitignore
├── README.md
├── frontend/               Vite React TypeScript app
├── backend/
│   ├── main.py             FastAPI app — uvicorn main:app --reload --port 8000
│   ├── agent.py            the Pydantic AI agent: model, prompt, tools
│   ├── models.py           every type that crosses a boundary
│   ├── tools.py            the catalogue reads the agent can perform
│   ├── prompts/
│   │   └── prompt.md       system prompt: voice, shopping rules, safety
│   ├── auth.py             password hashing and sessions
│   ├── audit.py            append-only agent-loop log
│   ├── limits.py           timeout and per-shopper turn budget
│   ├── search_terms.py     query normalisation
│   ├── collections_map.py  residential college / graduate school mapping
│   ├── export_catalogue.py regenerates the front end's catalogue files
│   └── seed_test_user.py   resets the test account's password
└── output/
    ├── harness.md          database reference + full system explanation
    ├── design.md           look-and-feel changes and why they drive sales
    ├── usability.md        the four usability improvements
    ├── app_check.html      full site test report
    ├── app_check_images/   screenshots linked from app_check.html
    └── audit_trail.json    append-only log of the agent loop
```

The agent itself is four files: `backend/prompts/prompt.md`, `backend/agent.py`,
`backend/tools.py` and `backend/models.py`.

---

## The data pack (not in this repository)

The database and the product photographs are distributed separately and are
**deliberately git-ignored**. Place them like this before running anything:

```
hw4/
└── data/
    ├── campus_customs.db
    └── products/          102 .jpg files referenced by the catalogue
```

---

## Running it

### 0. Place the data pack

Unzip the data pack so `hw4/data/campus_customs.db` and `hw4/data/products/` exist, as
shown above. Nothing below will work without it.

### 1. Python dependencies and secrets

From `hw4/`:

```bash
pip install -r requirements.txt
```

```bash
cp .env.example .env
```

Then open `.env` and set `PORTKEY_API_KEY` to a real key. The backend will start without
it, but `/api/chat` will return an error until it is set.

### 2. Build the front end's catalogue files

The product JSON and the images the front end serves are generated from the data pack
and are git-ignored, so generate them once:

```bash
python backend/export_catalogue.py
```

This writes `frontend/src/data/products.json` and copies the 102 photographs into
`frontend/public/products/`.

### 3. Start the backend

From the **`backend/`** directory:

```bash
uvicorn main:app --reload --port 8000
```

A cold start takes roughly 30 seconds — importing Pydantic AI and the OpenAI SDK is
slow. It is not hung. Check it with `http://localhost:8000/api/health`.

### 4. Start the front end

From the **`frontend/`** directory, in a second terminal:

```bash
npm install && npm run dev
```

Open `http://localhost:5173`.

---

## Test account

```
email:    test@campuscustoms.yale.edu
password: password
```

If it ever stops working, re-seed it from `hw4/`:

```bash
python backend/seed_test_user.py
```

---

## Pages

| Route | Page | Copy source |
|---|---|---|
| `/` | Home | yalebulldogblue.com |
| `/products` | Catalogue, with filters and sort | own voice |
| `/products/:id` | Single item — large image, full details, stock by size | own voice |
| `/about` | About Us | yalebulldogblue.com + Campus Customs |
| `/login` | Log In | own voice |
| `/create-account` | Create Account | own voice |

A chat widget sits bottom-right on every page, backed by the Pydantic AI agent. The
agent returns product ids; the server hydrates them from SQLite into cards, so prices
and stock on screen always come from the database rather than from the model.

---

## API

| Endpoint | Returns |
|---|---|
| `GET /api/health` | service and catalogue status |
| `GET /api/products` | 102 products; `?category=`, `?collection=`, `?q=`, `?in_stock=` |
| `GET /api/products/{id}` | one product |
| `GET /api/categories` | the six garment categories |
| `GET /api/collections` | residential colleges and graduate schools |
| `GET /products/{file}.jpg` | product image |
| `POST /api/auth/signup` | create an account, returns a session token |
| `POST /api/auth/login` | email + password to session token |
| `POST /api/auth/logout` | revoke the token |
| `GET /api/auth/me` | the signed-in user |
| `POST /api/chat` | one turn with the shopping agent |
| `GET /api/chat/history` | saved conversation for the signed-in shopper |
| `DELETE /api/chat/history` | clear it |
| `GET /api/chat/info` | which prompt file and model are loaded, and every live limit |

---

## Notes

**Passwords** are stored as PBKDF2-HMAC-SHA256 with a per-user random salt and 600,000
iterations — never in plaintext.

**Chat history** is saved to the `chat_messages` table for signed-in shoppers only.
Guests can use the assistant freely; nothing is recorded.

**`garment_type` is dirty.** The database holds 22 inconsistent labels for 102 products —
casing varies (`short-sleeve t-shirt` vs `short-sleeve T-shirt`) and `hoodie`,
`pullover hoodie` and `hooded sweatshirt` all mean the same thing to a shopper. The
backend normalises these into six browseable categories: Crewnecks (29), Hoodies (27),
T-Shirts (25), Quarter-Zips (11), Jackets (8), Long Sleeves (2).

**Full documentation** is in [output/harness.md](output/harness.md): the database schema,
how authentication works, how the front end talks to the API, every agent tool, the
safety rules, and all loop limits and result caps.
