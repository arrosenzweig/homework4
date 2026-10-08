# Design and UI changes

Changes to how the site looks and feels, and why each one should move product.

The shop's position is specific: officially licensed Yale apparel, sold from a storefront
at 57 Broadway since 1975, to people with a reason to wear Yale on their chest. The
design work below leans on that rather than on generic ecommerce patterns.

---

## 1. Yale Athletics ticker along the bottom

**Files:** `src/components/AthleticsTicker.tsx`, `src/data/athletics.ts`

A fixed strip across the bottom of every page, scrolling the upcoming Yale Athletics
home events of the Fall 2026 season — date, sport, opponent, and a Home tag.

Real schedule data, taken from the published 2026 schedules on yalebulldogs.com: five
football home games at the Yale Bowl (Merrimack, Dartmouth, Rhode Island, Brown,
Princeton), women's soccer at Reese Stadium (Princeton, Columbia, Penn), the volleyball
homestand at John J. Lee Amphitheater (Harvard, Dartmouth, Columbia, Cornell, Brown),
and The Game at Harvard on Nov 21.

**Each event is a button, not decoration.** Clicking one opens the catalogue filtered to
gear for that sport — the football games go to `/products?q=football`, volleyball to
volleyball, and the Harvard game to the rivalry merchandise.

Events that have already happened are filtered out, so the strip always leads with what
is next. On 7 October it opens with Dartmouth on 10 October; the 3 October games are
gone.

### Why it should drive sales

**It supplies the occasion.** The hardest part of selling a $68 sweatshirt is giving
someone a reason to buy it *today* rather than eventually. "Football vs Dartmouth, Oct
10" is that reason, and it is a true one. Game-day apparel is bought in the days before
a game, and this puts the date in front of the shopper at the moment they are already
looking at sweatshirts.

**It routes intent straight to product.** A shopper who notices the volleyball match is
one click from volleyball gear — no searching, no category guessing. The distance from
"I should get something for that" to a product page is a single tap.

**It signals the shop is current.** A store showing this week's fixtures reads as a
real New Haven business that follows the team, which is exactly what Campus Customs is.
A static storefront reads as abandoned.

### Design care

- **Pauses on hover and on keyboard focus**, so a moving target can actually be read
  and clicked. A ticker that cannot be caught is an irritation, not a feature.
- **Respects `prefers-reduced-motion`**: the animation stops entirely and the strip
  becomes a horizontally scrollable list. Perpetual motion is a genuine accessibility
  problem for vestibular disorders, and a fixed-position animation is the worst case.
- **Dismissible**, remembered for the session.
- **The duplicated row for seamless looping is `aria-hidden`**, so a screen reader hears
  each fixture once rather than twice.
- **Layout gets out of its own way**: `body.has-ticker` adds footer padding and lifts
  the chat launcher, so the strip never covers the footer or the assistant.

---

## 2. Honest stock badges on product cards

**File:** `src/components/ProductCard.tsx`

Cards now carry a badge when the inventory warrants one:

- **Sold out** — nothing left in any size
- **Low stock** — 12 or fewer units across all sizes
- **"2 sizes left"** — plenty of units, but concentrated in very few sizes

Every threshold reads the real `inventory` rows. Verified against the catalogue: 1
product qualifies for Low stock and 5 for the sizes badge, which is exactly what the
page renders.

### Why it should drive sales

**Scarcity converts — when it is true.** "Low stock" is the oldest lever in retail
because it answers "should I buy now or later?". The version that works long-term is the
honest one: this badge is derived from stock the shop actually holds, so a shopper who
checks finds it accurate. Invented urgency buys one conversion and costs the trust that
produces the next ten.

**The sizes badge prevents a specific disappointment.** The worst moment in this store
is choosing a sweatshirt, then discovering your size is gone. Surfacing "2 sizes left"
on the card lets someone skip it before investing attention — which keeps them shopping
instead of leaving.

---

## 3. Product cards that respond

**File:** `src/index.css`

The product photo now scales gently on hover, inside a card that already lifts and
takes a blue border. Suppressed under `prefers-reduced-motion`.

### Why it should drive sales

Apparel is bought on how it looks, and the photo is the entire pitch. A small movement
toward the shopper on hover is the digital equivalent of a garment being turned toward
you on a table — it rewards attention and makes the grid feel browsable rather than
static. It also makes the hit target obvious, which matters on a page with 102 cards.

---

## 4. Real page identity

**File:** `index.html`

The site shipped with Vite's defaults: the project name as the tab title and the Vite
logo as the favicon. Now:

- **Title:** "Yale Bulldog Blue by Campus Customs — Officially Licensed Yale Apparel"
- **Description meta** naming the shop, the address, and the categories
- **Favicon:** the navy Y mark, drawn as inline SVG markup in the `<link>` rather than
  shipped as a binary asset
- **`theme-color`** set to Yale blue, so mobile browser chrome matches the site

### Why it should drive sales

Every one of these is a conversion surface outside the page. A shopper with nine tabs
open finds their way back by the title and the favicon — a Vite logo is one they lose.
Shared links show the description. "Officially Licensed" in the title is the shop's
strongest credibility claim and belongs where it is read before the page even loads.

---

## 5. Visible focus states everywhere

**File:** `src/index.css`

Every link, button, input and select now shows a clear focus ring — white over the navy
nav and footer, Yale blue elsewhere.

### Why it should drive sales

Keyboard shoppers are shoppers. Without a focus ring the site is navigable only by
guesswork, which ends the session. This also helps anyone whose mouse hand is busy, and
it costs nothing visually because the ring only appears for keyboard navigation
(`:focus-visible`), never on a mouse click.

---

## 6. Smaller consistency work

- **`text-wrap: balance`** on the hero headline, so "Shop Bulldog Blue" never breaks into
  a lopsided two lines on a narrow screen.
- **Blue accent rule under the nav bar**, tying the header to the ticker at the other
  edge so the page is framed in the shop's color.
- **Shadow on the detail-page image panel**, lifting the product photo off the page —
  the one element on that page that should carry weight.
- **Yale-blue text selection highlight**, a detail people don't notice consciously and
  which makes the whole page feel considered.
- **Smooth in-page scrolling**, disabled under `prefers-reduced-motion`.
- **Mobile:** the ticker drops its "Bulldogs" label and tightens item spacing below
  560px; the filter row stacks to full-width controls.

### Why these help

None of these sells a sweatshirt on its own. Together they are the difference between a
site that feels like a class project and one that feels like a business with a storefront
on Broadway. A shopper deciding whether to enter a card number is reading those signals
whether or not they could name them.

---

## 7. Shop by residential college and graduate school

**Files:** `backend/collections_map.py`, `src/pages/Products.tsx`, `src/pages/Home.tsx`,
`src/pages/ProductDetail.tsx`

The catalogue had one axis of organization: `garment_type`, normalized into six garment
categories. That answers "what kind of clothing is this" and nothing else.

It does not answer the question a large share of Yale shoppers actually arrive with:
*what do you have for Saybrook?* or *my daughter just started at the School of Nursing*.
That affiliation was sitting in product names, descriptions and tags where only free-text
search could reach it — so "Saybrook" worked by accident, and "Nursing" competed with
every description containing the word.

### What was added

A second, independent dimension: **collection**. A product now has a garment category
*and*, when applicable, a residential college or a graduate school. A Benjamin Franklin
quarter-zip is in Quarter-Zips **and** Benjamin Franklin College.

`collections_map.py` classifies each product by matching the fourteen residential
colleges and the graduate and professional schools against product text, with
word-boundary matching so short names cannot fire on fragments. Schools are tested first,
since their multi-word names are more specific.

**32 of 102 products classify into 22 collections** — 11 residential colleges (Benjamin
Franklin, Berkeley, Branford, Davenport, Grace Hopper, Jonathan Edwards, Morse, Pierson,
Saybrook, Timothy Dwight, Trumbull) and 11 schools (Architecture, Art, Divinity,
Engineering & Applied Science, Management, Medicine, Music, Nursing, Public Health, the
Environment, Law).

Surfaced in four places:

- **Products page:** a "College or school" dropdown, grouped under *Residential Colleges*
  and *Graduate & Professional Schools*, composable with every other filter. URL-driven
  like the rest, so `/products?collection=Saybrook%20College` is shareable.
- **Home page:** two browse sections listing every college and school as a chip.
- **Product detail:** the collection shown as a link back to everything in it, tagged with
  its type.
- **The assistant:** a `collection` argument on `search_catalogue` and a `collections`
  tool listing what we stock.

### Why it should drive sales

**It matches how Yale people actually identify.** Nobody at Yale thinks of themselves as
a "quarter-zip person". They think of themselves as Saybrook, or Grace Hopper, or SOM.
Organizing the store the way the customer organizes themselves turns browsing into
recognition — and a shopper who sees their own college named is a shopper who has found
their shelf.

**It converts the highest-intent visitors.** Someone searching for their college's gear
has already decided to buy something; the only question is whether this shop has it.
Three clicks of hunting is where that sale is lost. A named chip on the home page is
where it is kept.

**It opens the gift path.** Parents, grandparents, and alumni buy for a specific person
at a specific college. "Shop your residential college" is a browse entry point built for
exactly that purchase, and it sits next to the existing relatives gear.

**It makes the assistant far more reliable on these questions.** Passing "Saybrook" as a
structured filter instead of free text is an exact match, not a guess. Asked for a
college we do not stock, the agent now says so plainly — *"We don't currently carry
Silliman College gear"* — rather than offering another college's sweatshirt as though it
were theirs. Honest absence protects the trust the rest of the shop runs on.

### Honest limitations

- **70 products have no collection**, which is correct: generic Yale apparel, sports gear
  and relatives items do not belong to a college or school.
- **Three residential colleges have no products** — Ezra Stiles, Pauli Murray, Silliman.
  They are in the classifier so a new product is categorized the day it is added, but
  they are deliberately hidden from the filter and the home page, since a chip leading to
  an empty page is worse than no chip.
- **Classification reads product text**, so a future product that never names its college
  will not be classified. A `collection` column on `catalogue` would be the durable fix;
  this works because the shop's naming is consistent.

---

## What I did not do

**No countdown timers, no "12 people are viewing this", no fake "only 2 left!" on
well-stocked items.** These lift short-term conversion and are the reason people distrust
online shops. Campus Customs has been a family business since 1975 and sells to a
community that comes back every year — alumni, parents, students for four years running.
Manufactured urgency is a bad trade for a shop whose actual advantage is being real.

**No carousel on the home page.** Hero carousels test poorly: most visitors never see
past the first slide, and the movement competes with the thing you want clicked.

**No newsletter interstitial.** The chat widget is already an invitation; a second one
that blocks the page would make both less welcome.
