# qa-browser — the Product Manager writes the test, JuL runs it

Your Product Manager writes a test the way they'd describe it to a teammate — plain sentences, in a
ticket. JuL reads it, runs it in a real browser, and tells you whether it passed. That's the whole
idea.

Here's a real one — find a book on barnesandnoble.com and get it into the cart:

```markdown
# Ticket QA-BN-01 — Add a book to the cart from search

Site : https://www.barnesandnoble.com/
Tags : smoke, cart

## Steps

1. If a cookie banner appears, click "Accept All Cookies".
2. Search for "Theo of Golden".
3. Open the book "Theo of Golden: A Novel".
4. Check that the "Theo of Golden" book page is displayed.
5. Click "Add To Cart".
6. Click "View Cart & Checkout".

## Acceptance criteria

- The "Shopping Cart" page is displayed.
- The cart contains "Theo of Golden" with quantity 1.
- The "Checkout" button is visible.
```

No selectors, no code — just what a person would click and what they'd expect to see. Here's JuL
running it:

```console
$ python qa-browser/run.py qa-browser/tickets/barnesandnoble-cart-en.md --headed

→  1. If a cookie banner appears, click "Accept All Cookies"
     CLICK button « Accept All Cookies »   [jul 0.99]
→  2. Search for "Theo of Golden"
     TYPE  search field « Search query »  ⌨ "Theo of Golden"   [jul 1.00]
→  3. Open the book "Theo of Golden: A Novel"
     CLICK link « Theo of Golden: A Novel »   [jul 0.78]
✓  4. Check that the "Theo of Golden" book page is displayed   (JuL 1.00)
→  5. Click "Add To Cart"
     CLICK button « Add To Cart »   [jul 0.99]
→  6. Click "View Cart & Checkout"
     CLICK link « View Cart & Checkout »   [jul 1.00]

Page reached: Cart | Barnes & Noble®  (https://www.barnesandnoble.com/cart)

Acceptance criteria
  ✓ The "Shopping Cart" page is displayed   (JuL 1.00)
  ✓ The cart contains "Theo of Golden" with quantity 1   (JuL 0.99)
  ✓ The "Checkout" button is visible   (JuL 1.00)

PASS — 6 steps, 3 criteria, 32 s
JuL: 9 decisions, median 1576 ms, 0 tokens generated, $0.00
```

**JuL is the only brain here.** It picks every element and judges every check — and it never writes
anything: the only text it ever types is what the Product Manager put in quotes. No API key, nothing
generated, $0 a run. So you can run it on every deploy, and nothing in the code is tied to one site.

Notice step 4: the test checks *as it goes* — did we land on the right book? — and stops at the
first check that fails. When a checkout funnel breaks, that tells you *where* it broke, not just
*that* it broke.

▶️ **[Watch the screencast (`demo.mp4`)](demo.mp4)** — this exact run on barnesandnoble.com, recorded
with `python qa-browser/record_run.py` on a 2021 MacBook M1 Pro (MLX, `wemm-4b-4bit`). The whole
search-to-cart run takes 30 to 40 seconds, and every rerun is free.

## Writing a ticket

A few rules, and that's really all:

- **`Site :`** is where JuL starts.
- **One action per numbered line, in your own words** — *click*, *open*, *go to*. There's no fixed
  vocabulary; JuL works out which element on the page you mean.
- **Anything in "quotes" is copied straight from the site** — a button label, a product name, the
  text to type. It's the one thing to get exactly right, and it's exactly what a user sees on screen.
- **Start a line with *If* (or *Si*) and it's optional.** No banner today? JuL skips it instead of
  failing.
- **Start with *Check that* / *Verify that* / *Vérifier que* and it's an assertion** — JuL just
  looks, no click, and the run halts at the first one that fails. (*Check the box "…"*, with no
  *that*, still ticks the box.)

It works in French too — `## Étapes` and `## Critères de validation`. Each bullet under **Acceptance
criteria** is a yes/no question about the final page, and the ticket passes only when every step,
every assertion and every criterion does.

One tip: **make your checks specific, and pick names nobody else uses.** `"Theo of Golden" with
quantity 1` is judged far more reliably than a bare title, because the extra detail gives JuL
something concrete to agree with. And a quoted product name that also appears inside other results
("The Hobbit" vs. a 4-book boxed set *containing* The Hobbit) can let a wrong item through: the
cart does contain "The Hobbit". Quote the exact title, and look at the screenshot (`--shot`) of
your first green run.

## Under the hood

For each step, the harness reads the page's accessibility tree, keeps the ~10 controls whose names
share words with your sentence, and hands them to JuL. JuL makes the call:

```
OBSERVE  CDP Accessibility.getFullAXTree   → every named control: role + accessible name
DECIDE   Choice  operation (click / type) + target element, one system_one call per step
                 (an optional step also gets "none of these": JuL can say it does not apply)
ACT      a real mouse click on the node, or type the quoted text + Enter; then wait until the
         site's own requests are done and the page has stopped rendering
ASSERT   a "Check that ..." step, and every acceptance criterion, is a Choice/Noul on the current
         page — its title, heading, matching controls and the text around the words that matter;
         re-read until true within a short window, so late-rendered content is not a false negative
```

That's the whole split: the harness does the mechanical work, JuL makes every choice. No CSS
selector, no URL rule, no hand-written list of labels — nothing tied to a particular site.

## Signed-in flows

Some journeys only exist behind a login — and re-typing a password through the UI on every run is
the single flakiest thing in a test suite (captchas, 2FA, bot checks). So you sign in **once**, by
hand, in a browser JuL drives, and every run after that inherits the session:

```bash
google-chrome --remote-debugging-port=9222 --user-data-dir="$HOME/.qa-agent"
# sign in once in that window, then:
python qa-browser/run.py my-signed-in-ticket.md --cdp http://localhost:9222
```

Tag those tickets `auth` so a CI run without the session can skip them (`--exclude auth`).

## Suites, tags & shared setup

Run the tests you need — filter by tag — get one aggregate report and a CI-ready exit code:

```console
$ python qa-browser/suite.py "qa-browser/tickets/*.md"

  … QA-BN-01: 6 steps, 3 criteria, PASS …
  … QA-BN-02: 7 steps, 2 criteria, PASS …
================================================================
  ✓ Ticket QA-BN-01 — Add a book to the cart from search   (39 s)
  ✓ Ticket QA-BN-02 — A guest can start checkout from the cart   (30 s)

2/2 green — 0 tokens generated, $0.00
```

QA-BN-02 starts from a full cart, clicks "Checkout", and checks the guest lands on the checkout page
with the book in the order summary. It stops there: nothing is ever paid.

Two optional header lines make this work:

- **`Tags : smoke, checkout, auth`** — pick what runs: `--tag smoke` for a fast gate on every
  commit, `--exclude auth` to skip the signed-in ones, full suite at night.
- **`Setup : add-book-to-cart`** — pull in a shared step block from `fragments/`, so the "get a
  book into the cart" preamble lives in one file. Each ticket runs it *itself*, so the tests stay
  **independent**: none inherits another's cart, and any ticket runs alone, in any order. That's the
  DRY way to share setup without the fragility of tests that hand state to each other.

Keep only the stable *arrange* steps in a fragment; keep the thing you're actually testing visible
in the ticket.

## Run it regularly

The suite returns a non-zero exit code if anything is red, so it drops straight into CI or cron —
run a fast gate on every push and the full regression every night, and you find out the checkout
broke before your customers do. There's an example workflow in
[`ci.example.yml`](ci.example.yml) — copy it to `.github/workflows/qa.yml` in your app's repo to
switch it on:

```yaml
on:
  push:                       # fast smoke gate on every commit
  schedule:
    - cron: "0 6 * * *"       # full regression every night
```

```console
# on push:   python qa-browser/suite.py qa-browser/tickets/*.md --tag smoke
# nightly:   python qa-browser/suite.py qa-browser/tickets/*.md --exclude auth
```

Because a run costs $0, "run it regularly" can mean *really* regularly — every commit, every hour —
without a bill that grows with your suite. (It needs a runner with the local model and a browser;
signed-in tickets run against a session you seed once.)

## Replay for $0

Every run writes a trace (`qa-browser/runs/<ticket>.json`) with the element JuL chose for each step
and its probability for each check. Replaying reuses those elements:

```console
$ python qa-browser/run.py qa-browser/tickets/barnesandnoble-cart-en.md --replay
```

JuL is only called again for a step whose element has vanished (the site changed) and for the
assertions, which are always re-checked. Rerunning a green test costs nothing.

## Run it

```bash
pip install "jul[mlx]" playwright     # or jul[torch] off Apple Silicon
playwright install chromium
python qa-browser/run.py qa-browser/tickets/barnesandnoble-cart-en.md --headed
```

On a bot-protected site, point JuL at your own browser instead — it keeps your cookies and the
challenge you already solved by hand:

```bash
google-chrome --remote-debugging-port=9222 --user-data-dir="$HOME/.qa-agent"
python qa-browser/run.py my-ticket.md --cdp http://localhost:9222
```

The demo tickets stop at the checkout page — nothing is ever ordered.
