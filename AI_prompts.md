# AI Prompts Log — HW 4

A record of the prompts given to Claude (Claude Code, Opus 5) while completing this
assignment, organized by problem. Prompts are recorded verbatim, in the order they
were asked.

---

## Setup

Prompts issued before work on a numbered problem began.

1. > We are going to be work with hw4 in ai foundations. find the zipped data folder and unzip it

2. > can you do that again? i had the wrong zip folder in it.

---

## Problem 1 — AI prompt log

3. > lets start by creating our AI_prompts.md file which will log the prompts I give you. it should log and organize by section through namin each problem number and all the prompts i asked for to answer that problem. this is task 1

---

## Problem 2 — Database harness

4. > lets look at that .db file. i am glad you understand each table in it. lets create output/harness.md that records each table and its fields from the .db file. for each column, write a short line on why each is an important metric for our shop. this is problem 2

**Produced:** `output/harness.md`

---

## Problem 3 — Storefront (React + Vite + TypeScript)

5. > we are going to make a react + vite + typescript with the goal of having a navigation bar up top that links to the home, products, about us, log in, and create account pages. pull the wording that our company uses from yalebulldogblue.com for the home and about us pages. the rest of the pages should be in your own voice NOT from the site. on the products page, show images of our products with basic product info listed like name, price, and description. each product should open a single-item page, which means having a large image on one side and the product text on the other (description, price, sizes, stock when youhave them). clicking a card on products should take them to his page for each item. this is problem 3

6. > lets also add a chat interface in hte bottom right. we will have it call our backend later. lets start with a simple FastAPI app right now in backend/main.py just to serve the products and images

**Produced:** `frontend/` (React + Vite + TS front end), `backend/main.py` (FastAPI), `README.md`

---

## Problem 4 — Accounts and login

7. > for problem 4 we are going to build the create account and login geatures. the create account should ask for first name, last, email, password, and confirming the password. the login in just needs email and password. new accounts should be put in a users table. lets store passwords securly. lets tests this with the test user that lives in the seed database. it should have email test@campuscustoms.yale.edu and password of password. update output/harness.md with how this authorization works by describing the data we store and how we secure passwords. give me a link so i can test this email and password works

**Produced:** `backend/auth.py`, auth endpoints in `backend/main.py`, `backend/seed_test_user.py`, `frontend/src/lib/auth.tsx`, wired `Login.tsx` / `CreateAccount.tsx` / `NavBar.tsx`, Authentication section in `output/harness.md`

---

## Problem 5 — Pydantic AI chatbot behind FastAPI

8. > for problem 5 it is to time to build the chatbot using the pydantic ai agent ebhind fastapi!! this is the one plugged in our front-end chat widget feature. put api app in backend/main.py. we run this file with uvicorn. keep agent as these files: backend/prompts/prompt.md, backend/agent.py, backend/tools.py, backend/models.py. in main.py lets expose a chat route. i want a message from the site to return an agent reply. put our product and company voice plus safety basic in prompts/prompt.md. start and update types in models.py for chat replies and product cards. in output/harness.md take notes on how the front end is talking to the api and how the agent is loaded meaning the prompt file and model. ENSURE the bakend runs from backend/ folder as follows: uvicorn main:app --reload --port 8000

**Produced:** `backend/agent.py`, `backend/tools.py`, `backend/models.py`, `backend/prompts/prompt.md`, `/api/chat` in `backend/main.py`, rewired `ChatWidget.tsx`, chat agent section in `output/harness.md`

---

## Problem 6 — Database-backed tools, no invented prices or stock

9. > for problem 6 we are giving the agent tools to search in from from the campus_customs.db file including product description, price, number in stock by size when asked by customer. agent must use database but not invent or hallucinate prices and quanitites. if its out of stock, just say that. in prompts/prompt.md add that the agent knows to call these tools for price and stock questions. add and update return types in models.py like always. in output/harness.md, list all tools and explain why you chose certain model fields for searching feature.

**Produced:** typed tool returns in `backend/models.py`, rewritten `backend/tools.py` (size + price-band search, relevance-first ranking), updated tool signatures in `backend/agent.py`, price/stock rules in `backend/prompts/prompt.md`, Agent tools section in `output/harness.md`

---

## Problem 7 — Dynamic product cards on the site

10. > for problem 7, when a customer asks about a type of item the agent should search the catlougue. the site should dynamically should show matching items as product cards with image, name, price, short info. the agent should return structure product matches then the front end renders them on the site. after these dynamic product cards load by the new feature, you MUST ENSURE the same single-item page behavior from problem 3 (product cards plus the ones the chat put on the page) should still open the detail view (the large image on one side and full info on the other) when clicked on. update prompts/prompt.md and output/harness.md to explain how search results reach the site

**Produced:** `frontend/src/lib/agentResults.tsx`, `frontend/src/components/AgentMatches.tsx`, `url`/`in_stock` on `ProductCard` in `backend/models.py`, publish wiring in `ChatWidget.tsx`, section on Home + Products, "how search results reach the site" in `output/harness.md`

---

## Problem 8 — Saved history, identity, and page context

11. > for problem 8, when logged in, save chat history in databadse in correct tableand reload when they return relog in. agent should know who is chatting by name and email. put that in agent deps and tools the agent can call. also give enough page context that the agent can answer customer questions related to the products on the page. guests should still be able to chat but history is only recorded when logged in. document in output/harness.md how chat user history is sotred, the fields the egnt see, plus how page context is passed.

**Produced:** `PageContext` / `ShopperIdentity` / `ChatHistory` and extended `ChatDeps` in `backend/models.py`, `who_am_i` + `current_page` tools in `backend/agent.py`, `optional_user` / persistence / `GET` + `DELETE /api/chat/history` in `backend/main.py`, `frontend/src/lib/pageContext.ts`, history restore in `ChatWidget.tsx`, identity and page rules in `prompts/prompt.md`, harness section

---

## Problem 9 — Four usability improvements

12. > for question 9 we're going to choose and build 4 usability improvements: 2 on the frontend and 2 on the backend. We'll talk them through first. They'll be logged in output/usability.md, with a description of what was added and how it supports the website's mission. What improvement ideas do you have? Don't implement anything until we've agreed on all 4. Once we have, go ahead and build them.

13. > plus retry the failed processes from 9. also run faster!!!!

**Agreed:** F1 sort/filter, F2 accessible chat, B1 search quality, B2 chat timeout + rate limit
**Produced:** `backend/search_terms.py`, `backend/limits.py`, rewritten `Products.tsx`, accessible `ChatWidget.tsx`, `output/usability.md`

---

## Problem 10 — Look and feel

14. > for question 10 I'd like the website to look and feel better overall. One idea is a ticker scrolling along the bottom of the page that lists Yale Athletics events for the Fall 2026 semester. Also look over the site and make whatever general UI improvements you think are worthwhile. Write up each change in output/design.md and explain why it helps drive sales on the site.

**Produced:** `frontend/src/components/AthleticsTicker.tsx`, `frontend/src/data/athletics.ts`, stock badges in `ProductCard.tsx`, polish pass in `index.css`, page identity in `index.html`, `output/design.md`

---

## Problem 10 (follow-up) — Collections by college and school

15. > I'd also like you to add in different product categories by yale graduate school and undergrad residential college. Record this prompt in the Prompts log too

**Produced:** `backend/collections_map.py`, `collection` filter + `list_collections` in `backend/tools.py`, `CollectionSummary` and collection fields in `backend/models.py`, `collections` agent tool + `collection` search argument in `backend/agent.py`, `GET /api/collections` and `?collection=` in `backend/main.py`, collection rules in `prompts/prompt.md`, regenerated `products.json`, college/school filter on Products, browse sections on Home, collection tag on the detail page, write-up in `output/design.md`

---

## Problem 11 — Full site test

16. > for question 11 now we'll test the whole site from top to bottom. Record the testing in output/app_check.html, with clear screenshots and captions. Each of the following gets its own screenshot: a chat checking the inventory level of an item, the dynamic search-result cards, and one of the usability features we added in Question 9. The HTML has to be easy to read (it's homework and will be graded), so give each screenshot a clear identifier and description. Save the screenshots in output/app_check_images and reference them from app_check.html using relative paths.

**Produced:** `output/app_check.html` (15 tests, T-01 to T-15), `output/app_check_images/` (12 screenshots)

---

## Problem 12 — Audit trail, hardened safety, system reference

17. > for question 12 create output/audit_trail.json to log what happens in the agent loop: the time, tool name, a short version of the args and result, the stop reason, and similar details. The file is append-only and must never be cleared between runs. Next, strengthen the safety instructions and precautions in prompt.md. These should cover protecting users and also guarding against runaway spending. Last, complete the harness file with a clear explanation of how the whole system works. It should cover the model fields in models.py and why each was chosen, the tools and what the agent can do, the safety rules, and specs such as loop limits, result caps, which models are used, and how to run the frontend and the backend.

18. > Did you implement the improvements from question 9?

**Produced:** `backend/audit.py`, `output/audit_trail.json` (append-only JSON Lines), `UsageLimits` ceilings in `backend/agent.py`, audited tool wrapper, stop-reason logging in `backend/main.py`, hardened safety sections in `backend/prompts/prompt.md`, System reference section in `output/harness.md`

---

## Problem 13 — Repository structure and push

19. > for question 13 start by checking that our file structure matches the one in this screenshot [attach the assignment's file-structure screenshot]. After that we can handle the rest of the instructions. I already have a GitHub account. Is there a different way to connect to it. https://github.com/arrosenzweig/homework4.git. Make one more pass and act as the grader for this assignment. Anywhere you'd take off points based on my instructions, fix it, and push again if anything changed.

**Fixed during the grader pass:** folder renamed `HW 4` -> `hw4`; `campus-customs/` -> `frontend/`; added root `requirements.txt`, `.env.example`, `.gitignore`; removed `data (1).zip`; git-ignored the data pack, product images, generated `products.json`, `node_modules` and `.env`; added `backend/export_catalogue.py` so the generated files can be rebuilt from the data pack; rewrote `README.md` around the data-pack workflow; ported the Problem 9 search normalisation to the front end so the grid and the assistant agree; removed unused Vite scaffold assets.
