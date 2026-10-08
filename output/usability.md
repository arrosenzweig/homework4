# Usability improvements

Four improvements — two frontend, two backend — chosen against the site's mission:
help someone find Yale apparel they want, confirm we actually have it, and buy it.

Each was picked from a measured defect rather than a guess. One candidate
(catalogue caching) was dropped after measurement showed it would save ~9 ms against
a 2–20 second model call: real, but invisible.

---

## B1 — Search that matches how shoppers type

**File:** `backend/search_terms.py`, wired into `tools.search_products()`

### The problem

Search matched raw substrings against catalogue text. Measured against the real
database:

| Query | Matches before |
|---|---|
| `gray` | 50 |
| `grey` | **0** |
| `hoodie` | 27 |
| `hoodei` | **0** |
| `sweater` | 6 |
| `jumper` | **0** |
| `t shirt` | **102** — the entire catalogue |

Two distinct failures. **Recall:** British spelling, typos and everyday synonyms
returned nothing from a shop full of matching items. **Precision:** `"t shirt"` split
into `t` and `shirt`; the single letter `t` appears in nearly every description, so the
query matched everything and ranked nothing.

### What was added

A normalization pass that runs before matching:

1. **Drop terms too short to discriminate**, with an allow-list for real short words
   (sizes, `tee`, `zip`, `art`, `law`, `mom`, `dad`). This alone fixes `"t shirt"`.
2. **Drop stopwords** — "do you have any", "I'm looking for" — so filler cannot inflate
   a score.
3. **Map shopper vocabulary onto catalogue vocabulary.** Spelling variants
   (grey→gray, colour→color), plurals (hoodies→hoodie, jackets→jacket), and words the
   product copy never uses (jumper→sweater, hoody→hoodie, zip up→full-zip).
   Multi-word phrases are folded first, so `quarter zip` becomes `quarter-zip`.
4. **Rescue typos.** A term that matches no catalogue word is compared against the
   vocabulary built from the live catalogue; a close spelling within a couple of edits
   is substituted.

### Result

| Query | Before | After |
|---|---|---|
| `grey` | 0 | **50** |
| `hoodei` | 0 | **27** |
| `jumper` | 0 | **6** |
| `t shirt` | 102 | **25** (exactly the T-Shirts category) |
| `zip up` | 21 | **7** (now full-zips specifically) |
| `hoodie` | 27 | 27 — no regression |
| `gray` | 50 | 50 — no regression |

End to end: *"do you have anything in grey?"* now returns six product cards. It
previously returned nothing.

### Why this supports the mission

A shop that answers "we don't have that" when it has fifty of them has failed at its
only job. Every one of these queries is something a real person types. This is the
single highest-leverage fix in the set: it converts dead ends into product views.

---

## B2 — A bounded wait and a turn budget on `/api/chat`

**File:** `backend/limits.py`, wired into the chat route

### The problem

Two gaps, both structural rather than cosmetic:

- **No timeout.** `agent.run()` could hang indefinitely. If the gateway stalled, the
  request never returned and the chat widget spun forever — the only recovery was a
  page reload, and the shopper had no idea anything was wrong.
- **No ceiling.** Every turn is a billed gateway call. An open endpoint with no limit
  is a budget anyone can drain with a `for` loop.

### What was added

**Timeout.** `asyncio.wait_for` bounds the agent call at 45 seconds (observed turns run
2–20s, so this is generous headroom while still bounding the worst case). On expiry the
route returns `504` with a plain message: *"That took longer than expected and I had to
stop waiting. Please try asking again."*

**Rate limit.** A sliding window of 25 turns per 5 minutes, keyed by account for
signed-in shoppers (so the limit follows them across devices) and by IP for guests. Over
the limit returns `429` with a `Retry-After` header and a message naming the wait.

**The widget now surfaces the server's own explanation** instead of a generic failure,
so a rate-limited or timed-out shopper reads what actually happened.

### Verified

26 rapid requests against a limit of 25 produced:

```
status 429
{"detail":"You have sent a lot of messages in a short time.
           Give it about 278 seconds and try again."}
```

### Why this supports the mission

A spinner that never resolves reads as a broken site, and a shopper who thinks the site
is broken leaves. Bounding the wait converts an invisible hang into a recoverable
message. The rate limit protects the thing the assistant runs on — if the gateway budget
is drained, the assistant stops working for every genuine shopper.

### Honest limitation

The limiter holds state in process memory. That is correct for a single-worker course
project and **wrong for a multi-process deployment**, where each worker would keep its
own counter and the effective limit would multiply by the worker count. A real
deployment needs shared state (Redis) or a gateway-level limit.

---

## F1 — Sort and filter on the products page

**File:** `frontend/src/pages/Products.tsx`, `src/lib/pageContext.ts`

### The problem

102 products, and the only tools for narrowing them were a category chip row and a text
box. No way to sort by price, cap a budget, or hide things that cannot be bought. A
shopper with "under $60, size XL" in mind had to read every card.

### What was added

- **Sort:** Featured, Price low→high, Price high→low, Name A–Z
- **Size filter:** shows only products with that size actually on the shelf
- **Max price slider:** bounded by the real catalogue range, $32–$98
- **In-stock-only toggle**
- **Reset**, shown only when something is filtered
- A live result count that states the filters in words: *"68 products available in XL
  under $76"*

**All filter state lives in the URL**, not component state. A filtered view is
shareable and bookmarkable, survives a refresh, and — the reason it matters here — can
be read back by the assistant.

### The gap this closed

`usePageContext()` previously sent `search_query: null` hardcoded, and computed
`visible_product_ids` from the category alone. So the assistant's picture of the page
was wrong whenever a shopper had typed or sorted. It now mirrors the grid's exact
filtering *and sorting*, so `visible_product_ids` really is what is on screen, in the
order shown — which is what makes "how much is the third one?" resolve correctly.

### Verified

`/products?sort=price-desc&size=XL&maxPrice=75&inStock=1` → 68 products, first card
$72.00, last $32.00. Independently checked against the catalogue: 68 products have XL
in stock at ≤ $75, with a price range of $32–$72. Exact match.

### Why this supports the mission

Budget and size are the two things that decide whether a purchase can happen at all.
Letting someone say "XL, under $75" up front removes the work of checking 102 products
by hand, and the in-stock toggle keeps them from falling for something they cannot buy.
Shareable URLs also mean a shopper can send a filtered view to the person actually
paying.

---

## F2 — An accessible chat panel

**File:** `frontend/src/components/ChatWidget.tsx`

### The problem

The assistant is a primary way to shop this site, and it was unusable without a mouse
and sighted reading:

- **Replies were never announced.** No live region, so a screen reader user got silence
  when an answer arrived.
- **Escape did nothing.** The panel could only be dismissed by clicking a small ×.
- **Focus was unmanaged.** Opening the panel left focus behind it; closing could strand
  focus on a hidden element.
- **No way to clear a conversation.** `DELETE /api/chat/history` existed from problem 8
  but had no UI, so a shopper on a shared computer could not remove their thread.

### What was added

- **`aria-live="polite"` announcement region.** Replies are announced once, including a
  count of products shown ("…Showing 6 products."). The announcement is a separate
  element rather than the log itself, so a screen reader reads the *new* message instead
  of re-reading the whole thread on every update.
- **`role="dialog"`** on the panel, **`role="log"`** on the transcript, and a label on
  the typing indicator.
- **Escape closes the panel.**
- **Focus management:** opening moves focus to the message input; closing returns it to
  the launcher button.
- **Visible focus rings** on every interactive control site-wide, in white over the navy
  nav so they stay visible there.
- **Clear button** in the panel header, which resets the thread and, for signed-in
  shoppers, deletes the saved history server-side.

### Verified

| Check | Result |
|---|---|
| Panel role / label | `dialog` / "Shopping assistant" |
| Transcript role | `log` |
| Live region | `aria-live="polite"`, `aria-atomic="true"` |
| Focus on open | the message input |
| Reply announced | "Yes—there are plenty of grey options…" |
| Escape | panel closed, focus returned to `.chat-fab` |
| Clear | thread back to greeting, "Conversation cleared." announced |

### Why this supports the mission

A shopper who cannot use the assistant cannot use the fastest path to a product on this
site. Keyboard and screen-reader support is the difference between a usable store and
an unusable one for people who shop that way — and the same focus rings and Escape
handling make the panel faster for everyone. The Clear button matters on a shared
machine: without it, the only way to remove a conversation was to never start one.
