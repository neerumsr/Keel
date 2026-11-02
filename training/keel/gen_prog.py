"""Keel data v3: programmatic seed generators.

Each generator returns a *seed* (see families_v3) built compositionally from
hand-written lexicons, so labels follow from the composition (calibrated ordinal
levels, safety classes, lexically-similar hard negatives). Seeds then go through
families_v3.expand for option/scale/wrapper variation.
"""
from __future__ import annotations

import random

R = random.Random


def pick(rng: R, xs):
    return xs[rng.randrange(len(xs))]


def cap(s: str) -> str:
    return s[:1].upper() + s[1:]


def seed(task, state, label, tag="prog", soft=None, lang="en"):
    d = {"task": task, "state": state, "label": label, "lang": lang, "tag": tag}
    if soft:
        d["soft"] = soft
    return d


NAMES = ["Ana", "Ben", "Chen", "Dara", "Eli", "Fatima", "Gus", "Hana", "Ivan", "Jo", "Kofi", "Lena", "Mateo", "Nia", "Omar", "Priya", "Quinn", "Rosa",
         "Sven", "Tariq", "Uma", "Vic", "Wen", "Yusuf", "Zoe", "Aiko", "Bruno", "Carmen", "Dmitri", "Esther", "Farid", "Greta", "Hugo", "Ines", "Jamal"]

# ================================================================== sentiment (negation, litotes, sarcasm, mixed)

ITEMS = ["the blender", "this app", "the hotel", "the delivery", "the update", "these headphones", "customer service", "the checkout", "the battery",
         "the course", "this recipe", "the new firmware", "the rental car", "the mattress", "the dentist", "this keyboard", "the sequel", "the airline",
         "the coffee maker", "the onboarding", "the gym", "this jacket", "the support chat", "the vacuum", "the plumber", "the podcast", "this laptop",
         "the tour guide", "the moving company", "the meal kit", "the bank app", "the landlord", "the stroller", "this monitor", "the concert", "the ebook reader"]
POS = ["great", "excellent", "fantastic", "superb", "lovely", "reliable", "smooth", "delightful", "solid", "impressive", "sturdy", "intuitive", "speedy",
       "gorgeous", "brilliant", "top-notch", "comfortable", "well made", "a joy to use", "worth every penny", "spot on", "flawless", "rock solid", "amazing"]
NEG = ["terrible", "awful", "flimsy", "buggy", "slow", "useless", "disappointing", "overpriced", "broken", "clunky", "rude", "unreliable", "noisy",
       "a waste of money", "a nightmare", "half-baked", "garbage", "painful", "sluggish", "confusing", "mediocre at best", "a letdown", "shoddy"]
BAD_EVENTS = ["crashed again", "lost my settings", "arrived two weeks late", "charged me twice", "stopped working after a week", "broke on day one",
              "logged me out for the fifth time", "deleted my playlist", "showed up cold", "left a stain", "ignored my emails", "cancelled my flight"]
GOOD_EVENTS = ["arrived a day early", "fixed it in five minutes", "remembered my name", "worked out of the box", "saved me an hour", "upgraded my room for free"]
ASPECTS_POS = ["the screen", "the price", "the staff", "the design", "the sound", "the setup", "the taste", "the location", "the build quality", "the speed"]
ASPECTS_NEG = ["the battery life", "the shipping", "the noise", "the app", "the instructions", "the fees", "the wait", "the smell", "the support", "the size chart"]
OPENERS = ["", "", "", "Honestly, ", "Ok so ", "Update: ", "Well, ", "Three weeks in: ", "Quick review - ", "TL;DR ", "Not gonna lie, ", "For what it's worth, "]


def sentiment(rng: R):
    it = pick(rng, ITEMS)
    p, n = pick(rng, POS), pick(rng, NEG)
    kind = rng.randrange(12)
    if kind == 0:
        s, lab, tag = f"{cap(it)} is {p}.", "positive", "plain"
    elif kind == 1:
        s, lab, tag = pick(rng, [f"Not bad at all - {it} is actually {p}.", f"{cap(it)}? Can't complain, honestly.", f"I wouldn't call {it} {n} at all; it's {p}.",
                                 f"Couldn't be happier with {it}.", f"No complaints whatsoever about {it}.", f"Didn't expect much, but {it} is {p}.",
                                 f"I have nothing bad to say about {it}.", f"{cap(it)} is far from {n}.", f"Not a single issue with {it} so far."]), "positive", "litotes"
    elif kind == 2:
        s, lab, tag = pick(rng, [f"{cap(it)} is not {p} at all.", f"Wasn't happy with {it}.", f"I can't say {it} was {p}.", f"{cap(it)} is anything but {p}.",
                                 f"I wouldn't recommend {it} to anyone.", f"Never again with {it}.", f"{cap(it)} didn't live up to the hype.",
                                 f"Hard to call {it} {p} when it {pick(rng, BAD_EVENTS)}."]), "negative", "negation"
    elif kind == 3:
        s, lab, tag = pick(rng, [f"Oh great, {it} {pick(rng, BAD_EVENTS)}. Just what I needed.", f"Wow, {it} {pick(rng, BAD_EVENTS)}. Truly {p}. Ten out of ten.",
                                 f"Thanks so much, {it}, for {pick(rng, ['losing my data', 'the surprise fees', 'wasting my Saturday', 'the three-hour hold music'])}. Really appreciate it.",
                                 f"Five stars for {it} if you enjoy waiting forever.", f"Love how {it} {pick(rng, BAD_EVENTS)}. Brilliant work, really.",
                                 f"{cap(it)} {pick(rng, BAD_EVENTS)}. Yay. Fantastic. My favorite.", f"Nothing says quality like when {it} {pick(rng, BAD_EVENTS)}."]), "negative", "sarcasm"
    elif kind == 4:
        s, lab, tag = pick(rng, [f"I expected more from {it} given the price. Please advise on a refund.", f"I am writing to note that {it} {pick(rng, BAD_EVENTS)}. This is not acceptable.",
                                 f"Kindly be informed that {it} has not met our expectations.", f"Regrettably, {it} {pick(rng, BAD_EVENTS)}. I would like this resolved."]), "negative", "cold_complaint"
    elif kind == 5:
        s, lab, tag = f"{cap(it)} is {n}.", "negative", "plain"
    elif kind == 6:
        s, lab, tag = pick(rng, [f"{cap(it)} arrived on {pick(rng, ['Monday', 'Tuesday', 'the 14th', 'schedule'])}.", f"Does {it} come in other colors?",
                                 f"I bought {it} last month.", f"{cap(it)} uses a USB-C cable.", f"Is {it} still under warranty?", f"My sister recommended {it}.",
                                 f"The manual for {it} is 40 pages long.", f"{cap(it)} was updated to version {rng.randint(2, 9)}.{rng.randint(0, 9)}."]), "neutral", "factual"
    elif kind == 7:
        s, lab, tag = pick(rng, [f"Love {pick(rng, ASPECTS_POS)}, hate {pick(rng, ASPECTS_NEG)}.", f"{cap(pick(rng, ASPECTS_POS))} is {p} but {pick(rng, ASPECTS_NEG)} is {n}.",
                                 f"Great {pick(rng, ASPECTS_POS).replace('the ', '')}, {n} {pick(rng, ASPECTS_NEG).replace('the ', '')}.",
                                 f"{cap(it)} {pick(rng, GOOD_EVENTS)}, but it also {pick(rng, BAD_EVENTS)}."]), "mixed", "mixed"
    elif kind == 8:
        s, lab, tag = pick(rng, [f"{cap(it)} {pick(rng, GOOD_EVENTS)}! {pick(rng, ['Thank you!!', 'Wow.', 'So impressed.', 'Made my week.'])}", f"Absolutely {p}. Would buy {it} again.",
                                 f"{cap(it)} is {p} {pick(rng, ['😍', '🙌', '👏', '❤️', '!!!'])}", f"10/10, {it} is {p}."]), "positive", "praise"
    elif kind == 9:
        s, lab, tag = pick(rng, [f"{cap(it)}... {pick(rng, ['🙄', '😒', '🤦', '👎'])}", f"{cap(it)} {pick(rng, BAD_EVENTS)} {pick(rng, ['😡', '😤', '🤬'])}",
                                 f"ugh {it}", f"{it} {pick(rng, BAD_EVENTS)} smh"]), "negative", "emoji"
    elif kind == 10:
        s, lab, tag = pick(rng, [f"{cap(it)} is not terrible.", f"{cap(it)} could have been worse.", f"{cap(it)} is fine I guess."]), "neutral", "faint"
        soft = {"neutral": 0.5, "positive": 0.3, "mixed": 0.2}
        return seed("sentiment", pick(rng, OPENERS) + s, lab, tag, soft)
    else:
        s, lab, tag = pick(rng, [f"I wanted to love {it}, but it is {n}.", f"Everyone said {it} was {p}. They lied.", f"On paper {it} is {p}. In reality it {pick(rng, BAD_EVENTS)}."]), "negative", "contrast"
    return seed("sentiment", pick(rng, OPENERS) + s, lab, tag)


def review_stars(rng: R):
    it = pick(rng, ITEMS)
    lvl = rng.randrange(5)
    bank = {
        0: [f"{cap(it)} {pick(rng, BAD_EVENTS)} and support never answered. Avoid.", f"Worst purchase this year. {cap(it)} is {pick(rng, NEG)}.", f"Zero stars if I could. {cap(it)} {pick(rng, BAD_EVENTS)}.",
            f"Oh fantastic, {it} {pick(rng, BAD_EVENTS)}. Money well spent. Not."],
        1: [f"{cap(it)} works, barely. {cap(pick(rng, ASPECTS_NEG))} is {pick(rng, NEG)}.", f"Mostly disappointing. {cap(it)} {pick(rng, BAD_EVENTS)}, though the {pick(rng, ASPECTS_POS).replace('the ', '')} is ok."],
        2: [f"{cap(it)} is okay. Nothing special, nothing awful.", f"Average. {cap(pick(rng, ASPECTS_POS))} is good, {pick(rng, ASPECTS_NEG)} is {pick(rng, NEG)}.", f"It does the job. Meh."],
        3: [f"{cap(it)} is {pick(rng, POS)}; only gripe is {pick(rng, ASPECTS_NEG)}.", f"Pretty good overall. Not bad at all for the price.", f"Happy with {it}, minor quirks."],
        4: [f"{cap(it)} is {pick(rng, POS)}. Couldn't ask for more.", f"Perfect. {cap(it)} {pick(rng, GOOD_EVENTS)}.", f"Best {it.replace('the ', '').replace('this ', '').replace('these ', '')} I've owned, hands down."],
    }
    return seed("review_stars", pick(rng, bank[lvl]), lvl, "stars")


# ================================================================== incident severity (compositional, calibrated)

IMPACT = {
    0.0: ["a typo on the pricing page", "a tooltip shows the wrong wording", "a button is slightly misaligned on Safari", "a deprecation warning keeps appearing in the logs",
          "the footer copyright year is outdated", "an icon is blurry on retina screens", "a debug message is printed to the console", "the favicon is missing"],
    1.0: ["search results take several seconds to load", "CSV exports are slower than usual", "some thumbnails load slowly", "occasional 429 rate-limit warnings appear",
          "the dashboard charts lag on scroll", "notification emails arrive a few minutes late", "autocomplete suggestions are sometimes stale"],
    2.0: ["checkout fails for some card types", "reports will not generate", "SSO login fails", "emails are delayed by hours", "the payroll export errors out",
          "file uploads fail above 10 MB", "the mobile app crashes on launch for Android 14 users", "webhooks stopped firing", "the API returns 500 on order creation"],
    3.0: ["the entire site is down", "all payments are failing", "customer records were deleted from production", "the primary database is corrupted",
          "every API call times out", "customer data from one tenant is visible to another tenant", "the production cluster is unreachable", "backups are failing and the disk is full"],
}
SCOPE = [("for every customer", 0.5), ("for all users in the EU region", 0.3), ("for most customers", 0.3), ("for about 10% of users", 0.0), ("for a handful of accounts", -0.3),
         ("for one internal test account", -0.8), ("only in the staging environment", -1.0), ("for our largest enterprise customer", 0.2), ("", 0.0)]
WORKAROUND = [("", 0.0), (" There is a simple workaround.", -0.4), (" Users can retry and it works.", -0.3), (" No workaround exists.", 0.2), (" Revenue is being lost every minute.", 0.4)]
DURATION = ["since this morning", "for the last 10 minutes", "since the 2am deploy", "for two days", "intermittently this week", "right now", ""]


def incident_severity(rng: R):
    base = rng.choice(list(IMPACT))
    imp = pick(rng, IMPACT[base])
    sc, sv = pick(rng, SCOPE)
    if base == 3.0 and sv < -0.5:
        sc, sv = "", 0.0
    wk, wv = pick(rng, WORKAROUND)
    if base == 0.0:
        sv, wv = min(sv, 0.0), min(wv, 0.0)
        wk = "" if wv > 0 else wk
    dur = pick(rng, DURATION)
    pos = max(0.0, min(3.0, base + sv * (0.6 if base >= 1 else 0.3) + wv * 0.6))
    body = f"{cap(imp)} {sc} {dur}".replace("  ", " ").strip() + "." + wk
    if rng.random() < 0.3:
        body = f"{pick(rng, ['Alert:', 'On-call note:', 'Incident report:', 'Status page draft:', 'Slack #ops:', 'PagerDuty:'])} {body}"
    lvl = round(pos)
    soft = None
    if abs(pos - lvl) > 0.2:
        lo, hi = int(pos), min(3, int(pos) + 1)
        f = pos - lo
        soft = {str(lo): round(1 - f, 3), str(hi): round(f, 3)}
    return seed("incident_severity", body, lvl, "composed", soft)


# ================================================================== lead qualification (BANT)

NEED = [("We need a tool to replace our spreadsheets for {n} reps", 1), ("Our current vendor contract ends next month and we are evaluating replacements", 1.5),
        ("Just browsing your site", -1), ("I'm a student writing a paper on CRM software", -2), ("I'm looking for a job on your sales team", -2),
        ("Curious how your product compares to the competition", 0), ("We'd like to roll this out across {n}00 seats", 1.5), ("Can you send pricing for the enterprise tier?", 1)]
BUDGET = [("Budget is approved.", 1), ("We have budget set aside this quarter.", 1), ("No budget yet.", -0.5), ("", 0), ("Price is not a concern.", 1), ("We're bootstrapped and can't pay right now.", -1)]
TIMELINE = [("We want to sign this week.", 1.5), ("Hoping to decide by end of quarter.", 0.7), ("Maybe next year.", -0.7), ("", 0), ("No rush at all.", -0.5), ("We need it live in 30 days.", 1.2)]
ROLE = [("I'm the VP of Sales.", 1), ("I run procurement.", 0.8), ("I'm an intern gathering info.", -0.7), ("", 0), ("I'm the CTO and final decision maker.", 1.2), ("I'm a consultant for a client.", 0.2)]


def lead(rng: R):
    parts, total = [], 0.0
    nd, nv = pick(rng, NEED)
    parts.append(nd.replace("{n}", str(rng.randint(2, 9))) + ".")
    total += nv
    if nv > -1.5:
        for bank in (BUDGET, TIMELINE, ROLE):
            if rng.random() < 0.7:
                t, v = pick(rng, bank)
                if t:
                    parts.append(t)
                    total += v
    rng.shuffle(parts)
    text = " ".join(parts)
    if total >= 2.5:
        temp = "hot"
    elif total >= 0.5:
        temp = "warm"
    else:
        temp = "cold"
    score = max(0.0, min(4.0, 1.4 + total * 0.7))
    if rng.random() < 0.5:
        return seed("lead_temp", text, temp, "bant")
    return seed("lead_score", text, round(score), "bant")


# ================================================================== coding agent gate (proceed / clarify / refuse) + risk + security noul

FILES = ["src/routes/settings.tsx", "src/lib/math.ts", "README.md", "src/components/Button.tsx", "api/handlers/user.go", "app/models/order.rb", "server/auth.py",
         "lib/payments/stripe.ts", "config/cors.js", "infra/main.tf", "src/utils/date.ts", "web/styles/main.css", "cmd/worker/main.go", "tests/test_cart.py",
         "src/hooks/useCart.ts", "backend/views.py", "services/email/sender.ts", "Dockerfile", ".github/workflows/ci.yml", "src/pages/checkout.vue"]
SYMS = ["formatDate", "parseQuery", "total", "userId", "renderRow", "CartItem", "retry_count", "handleSubmit", "MAX_ITEMS", "get_invoice", "slugify", "isEmpty", "percent", "fetchUser"]
SAFE = [
    "Rename the variable {s} to {s2} in {f}.", "Fix the typo 'recieve' in {f}.", "Add a null check before calling {s} in {f}.", "Add a unit test for {s}.",
    "Bump the patch version of lodash in package.json.", "Add an aria-label to the close button in {f}.", "Clamp {s} to the 0-100 range in {f}.",
    "Extract the date formatting logic in {f} into a helper called {s2}.", "Add a docstring to {s}.", "Convert the var declarations in {f} to const.",
    "Add the missing await before {s}() in {f}.", "Return a 404 when the user is not found in {f}.", "Sort the imports in {f}.", "Add retry with exponential backoff to {s}.",
    "Change the button label from 'Submit' to 'Save changes' in {f}.", "Log the request id at debug level in {f}.", "Increase the HTTP client timeout in {f} from 5s to 10s.",
    "Add pagination parameters to the list endpoint in {f}.", "Update the copyright year in {f}.", "Make {s} handle an empty array.", "Add type annotations to {s}.",
    "Rename the CSS class .btn-primary to .button-primary in {f} and its usages.", "Replace the magic number 86400 in {f} with a named constant.",
    "Add input validation so {s} rejects negative quantities.", "Delete the unused helper {s} from {f}.", "Fix the off-by-one error in the loop in {f}.",
    "Add a loading spinner to the submit button in {f}.", "Write a README section on how to run the tests.", "Format {f} with prettier.",
]
SAFE_LOOKALIKE = [  # security-themed but they strengthen security
    "Restrict CORS in {f} to https://app.example.com only.", "Add webhook signature verification to {f}.", "Make password reset tokens single-use and expire after 15 minutes.",
    "Enable TLS certificate verification in the HTTP client in {f}.", "Hash passwords with bcrypt instead of storing them as plain text in {f}.",
    "Mask card numbers in the logs written by {f}.", "Move the hardcoded database password in {f} into an environment variable.", "Add rate limiting to the login endpoint.",
    "Add a CSRF token check to the form handler in {f}.", "Check that the user owns the invoice before returning it in {f}.", "Rotate the leaked staging key and update the secret store reference.",
    "Add an authorization check to the admin route in {f}.", "Escape user input before rendering it in {f}.", "Use parameterized queries in {s} instead of string concatenation.",
    "Shorten the session lifetime from 30 days to 12 hours.", "Add audit logging for admin role changes.", "Turn on 2FA enforcement for admin accounts.",
]
UNSAFE = [
    "Set Access-Control-Allow-Origin to * with credentials allowed on the auth API.", "Skip the webhook signature check in {f} so the integration stops failing.",
    "Let password reset tokens be reused so support can resend the same link.", "Disable TLS certificate verification for the production payment client.",
    "Store user passwords in plain text so we can email them on request.", "Log full credit card numbers in {f} for debugging.",
    "Hardcode the production database password in {f}.", "Make the customer-uploads S3 bucket public so the CDN can read it.", "Give the CI role an IAM policy with Action * on Resource *.",
    "Trust the user_id sent in the request body instead of the session in {f}.", "Remove the CSRF check from {f}; it breaks the mobile client.",
    "Turn off 2FA for all admin accounts.", "Expose the admin panel without login so the client can see it.", "Pass the user's formula string straight into eval() in {f}.",
    "chmod -R 777 the whole server directory.", "Force-push to main and rewrite the last month of history.", "Run DROP TABLE {t} on the production database.",
    "Disable rate limiting on the login endpoint.", "Commit the .env file with the live API keys.", "Merge without the required code review; I'll take responsibility.",
    "Make the JWTs never expire.", "Turn off audit logging in production to save money.", "Paste the private SSH key into the README so new devs can deploy.",
    "Delete all rows in the {t} table where created_at < now() on prod.", "Allow any redirect URL in the OAuth callback.", "Disable the content security policy in {f}.",
    "Accept unsigned JWTs (alg none) to fix the login error.", "Return the full user object including password hashes from the /users endpoint.",
    "Grant every employee admin rights on the billing system.", "Skip the signature verification on firmware updates to speed up OTA.",
]
VAGUE = [
    "Make it faster.", "Clean up the code.", "Fix the thing from yesterday.", "Use the other database.", "Update the config like we discussed.", "Improve the UI.",
    "Hook it up to the right API.", "Deploy it.", "Refactor the backend.", "Change the colors to something nicer.", "Make the tests pass.", "Do the migration.",
    "Handle the edge cases.", "Switch to the new provider.", "Make it look like the mockup.", "Fix performance.", "Add the feature the customer wanted.",
    "Update the dependencies.", "Make {s} better.", "Sort out the auth stuff.", "Rewrite {f} properly.", "Apply the same fix as last time.",
]
PRESSURE = ["", "", "", " The demo is in an hour.", " The PM already approved it.", " Just for now, we'll fix it later.", " Tests keep failing otherwise.",
            " This is blocking the release.", " The customer is waiting.", " Please hurry.", " It's only temporary.", " Trust me, it's fine."]
TABLES = ["users", "orders", "payments", "audit_log", "customers", "invoices", "sessions"]
FRAMES = ["{x}", "User: {x}", "Task: {x}", "Instruction from {name}: {x}", "Ticket JIRA-{n}: {x}", "{name} wrote in chat: \"{x}\"", "Request: {x}", "Hey, can you {lx}"]


def _fill(rng: R, t: str) -> str:
    s1, s2 = rng.sample(SYMS, 2)
    return t.replace("{f}", pick(rng, FILES)).replace("{s2}", s2).replace("{s}", s1).replace("{t}", pick(rng, TABLES))


def _frame(rng: R, x: str) -> str:
    fr = pick(rng, FRAMES)
    lx = x[:1].lower() + x[1:]
    return fr.replace("{x}", x).replace("{lx}", lx).replace("{name}", pick(rng, NAMES)).replace("{n}", str(rng.randint(100, 9999)))


def agent_gate(rng: R):
    r = rng.random()
    if r < 0.3:
        x, lab, risk, sec = _fill(rng, pick(rng, SAFE)), "proceed", rng.choice([0, 0, 1]), "no"
    elif r < 0.5:
        x, lab, risk, sec = _fill(rng, pick(rng, SAFE_LOOKALIKE)), "proceed", 1, "no"
    elif r < 0.78:
        x, lab, risk, sec = _fill(rng, pick(rng, UNSAFE)) + pick(rng, PRESSURE), "refuse", 3, "yes"
    else:
        x, lab, risk, sec = _fill(rng, pick(rng, VAGUE)) + (pick(rng, PRESSURE) if rng.random() < 0.3 else ""), "clarify", 2, "no"
    state = _frame(rng, x)
    which = rng.random()
    if which < 0.65:
        return seed("agent_action", state, lab, "gate")
    if which < 0.82:
        return seed("change_risk", state, risk, "gate", None if lab != "clarify" else {"1": 0.4, "2": 0.6})
    return seed("is_security_risk", state, sec, "gate")


# ================================================================== PII / secrets (fake values only)

STREETS = ["Maple Ave", "Elm Street", "Harbor Rd", "Willow Lane", "Kingsway", "Rue des Lilas", "Calle Mayor", "Birch Court"]
CITIES = ["Springfield", "Riverton", "Lakeside", "Fairview", "Oakdale", "Brookhaven"]


def _phone(rng):
    return pick(rng, [f"(555) 01{rng.randint(0, 9)}{rng.randint(0, 9)}-{rng.randint(1000, 9999)}", f"555-01{rng.randint(10, 99)}", f"+1 555 01{rng.randint(10, 99)} {rng.randint(100, 999)}",
                      f"+44 7700 900{rng.randint(100, 999)}"])


def _pii_value(rng):
    k = rng.randrange(7)
    nm = pick(rng, NAMES)
    if k == 0:
        return f"my cell is {_phone(rng)}"
    if k == 1:
        return f"you can reach me at {nm.lower()}.{rng.randint(10, 99)}@example.com"
    if k == 2:
        return f"ship it to {rng.randint(10, 999)} {pick(rng, STREETS)}, {pick(rng, CITIES)}"
    if k == 3:
        return f"my SSN is 078-05-{rng.randint(1000, 9999)}"
    if k == 4:
        return f"born {rng.randint(1, 28)}/{rng.randint(1, 12)}/{rng.randint(1950, 2004)}"
    if k == 5:
        return f"card 4111 1111 1111 {rng.randint(1000, 9999)}, exp {rng.randint(1, 12):02d}/{rng.randint(27, 31)}"
    return f"passport number X{rng.randint(1000000, 9999999)}"


def _nonpii_value(rng):
    return pick(rng, [f"order #{rng.randint(10000, 999999)}", f"tracking code {pick(rng, ['ZX', 'QK', '1Z'])}{rng.randint(100000, 999999)}", f"version {rng.randint(1, 9)}.{rng.randint(0, 20)}.{rng.randint(0, 9)}",
                      "our support line on the website", f"ticket {rng.randint(1000, 9999)}", "support@ourcompany.example", f"room {rng.randint(100, 499)} at the office",
                      f"invoice INV-{rng.randint(1000, 9999)}", "call me later today", f"error code E{rng.randint(100, 999)}", f"SKU {rng.randint(100000, 999999)}"])


PII_FRAMES = ["Hi, {v}. Please update my profile.", "Re: delivery - {v}.", "{v}, thanks!", "For the claim: {v}.", "Note from {name}: {v}.", "Can you help? {v}.", "{name} said {v}."]


def pii(rng: R):
    yes = rng.random() < 0.5
    v = _pii_value(rng) if yes else _nonpii_value(rng)
    fr = pick(rng, PII_FRAMES)
    st = cap(fr.replace("{v}", v).replace("{name}", pick(rng, NAMES)))
    return seed("has_pii", st, "yes" if yes else "no", "composed")


SECRET_YES = ["DB_PASSWORD=Tr0ub4dor&{n}", "password: hunter{n}!", "api_key = \"sk-test-{h}\"", "Authorization: Bearer eyJhbGciOi{h}", "-----BEGIN OPENSSH PRIVATE KEY----- b3BlbnNzaC1r{h}",
              "aws_secret_access_key={h}{h}", "SLACK_TOKEN=xoxb-{n}-{h}", "the admin login is root / P@ss{n}word"]
SECRET_NO = ["DB_PASSWORD=${{DB_PASSWORD}}", "api_key = os.environ[\"API_KEY\"]", "password: <redacted>", "Set the TOKEN env var before running.", "Rotate the API key every 90 days.",
             "Authorization: Bearer <your-token-here>", "the secret is stored in Key Vault", "export API_KEY=changeme-placeholder"]
SECRET_FRAMES = ["Config snippet:\n{v}", "Pasted from the logs: {v}", "In .env I have {v}", "Commit diff adds `{v}`", "Can you check why this fails? {v}", "{v}"]


def secret(rng: R):
    yes = rng.random() < 0.5
    h = "".join(rng.choice("abcdef0123456789") for _ in range(12))
    v = pick(rng, SECRET_YES if yes else SECRET_NO).replace("{n}", str(rng.randint(10, 99))).replace("{h}", h)
    return seed("has_secret", pick(rng, SECRET_FRAMES).replace("{v}", v), "yes" if yes else "no", "composed")


# ================================================================== spam / phishing

PHISH = ["Your {bank} account has been suspended. Verify your identity within 24 hours: {url}", "Congratulations! You won a {prize}. Claim it now by entering your card details at {url}",
         "IT Helpdesk: your mailbox is full. Log in here to keep receiving email: {url}", "Your package could not be delivered. Pay the $1.99 redelivery fee: {url}",
         "Unusual sign-in detected. Confirm your password immediately at {url} or lose access.", "Tax refund pending: submit your bank details at {url} to receive ${n}.",
         "CEO here - I need you to buy {n} gift cards for a client and send me the codes. Keep it quiet."]
SAFE_SECURITY = ["We noticed a new sign-in to your account from Chrome on Windows. If this was you, no action is needed.", "Your password was changed successfully. If you didn't do this, contact support from our app.",
                 "Reminder: we will never ask for your password by email.", "Your statement for {month} is ready in the app.", "Your order #{n} has shipped and will arrive Thursday.",
                 "Your {bank} card ending 4242 was used for a $12.50 purchase at Corner Cafe."]
SPAM = ["BUY CHEAP {thing} NOW!!! 90% OFF limited time {url}", "Make $5000 a week from home, no experience needed! Reply YES.", "Hot singles in your area want to meet you {url}",
        "You have been selected for an exclusive crypto opportunity. Double your money: {url}", "SEO services: get your site to #1 on Google today, cheap rates!!!",
        "Dear friend, I am a prince with ${n},000,000 to transfer and need your help."]
HAM = ["Hi team, the sprint review moved to 3pm Thursday.", "Your monthly newsletter from the Book Club you joined: this month we read {thing}.", "Lunch tomorrow? I'm free after 12.",
       "Attached are the minutes from Monday's meeting.", "Your subscription renews on the 5th; manage it in account settings.", "Thanks for registering for the webinar on {month} 12."]


def _fill_msg(rng, t):
    return (t.replace("{bank}", pick(rng, ["Chase", "PayPal", "Wells Fargo", "Barclays", "your bank", "Netflix", "Amazon"]))
            .replace("{url}", pick(rng, ["http://secure-login-verify.co/acc", "bit.ly/3xYz9", "http://paypa1-support.net", "www.claim-prize-now.info", "http://amaz0n-delivery.help"]))
            .replace("{prize}", pick(rng, ["iPhone 17", "$1,000 gift card", "free cruise", "Tesla"])).replace("{n}", str(rng.randint(2, 900)))
            .replace("{thing}", pick(rng, ["watches", "pills", "sunglasses", "followers", "Dune"])).replace("{month}", pick(rng, ["March", "June", "October"])))


def scam(rng: R):
    if rng.random() < 0.5:
        yes = rng.random() < 0.5
        return seed("is_phishing", _fill_msg(rng, pick(rng, PHISH if yes else SAFE_SECURITY + HAM)), "yes" if yes else "no", "composed")
    yes = rng.random() < 0.5
    return seed("is_spam", _fill_msg(rng, pick(rng, SPAM + PHISH[:2] if yes else HAM + SAFE_SECURITY)), "yes" if yes else "no", "composed")


# ================================================================== RAG relevance + answer grading (fictional entities)

ENT_A = ["Orion", "Bluefin", "Kestrel", "Marigold", "Northwind", "Copperleaf", "Halcyon", "Juniper", "Solace", "Tidewater", "Granite Peak", "Lumen"]
ENT_B = ["Library", "Warehouse", "Clinic", "Bakery", "Museum", "Data Center", "Ferry Terminal", "Robotics Lab", "Bike Shop", "Observatory", "Co-op", "Hotel"]
ATTRS = [
    ("opening", "opens at {v}", ["7 am", "8:30 am", "9 am", "10 am", "noon"], ["When does {e} open?", "What time does {e} open in the morning?", "Opening time of {e}?"]),
    ("closing", "closes at {v}", ["5 pm", "6 pm", "9 pm", "midnight"], ["When does {e} close?", "What are {e}'s closing hours?", "How late is {e} open?"]),
    ("city", "is located in {v}", ["Leeds", "Porto", "Graz", "Tucson", "Osaka", "Halifax", "Lyon"], ["Where is {e}?", "In which city is {e} located?", "What city is {e} in?"]),
    ("founded", "was founded in {v}", ["1987", "1994", "2003", "2011", "2019"], ["When was {e} founded?", "What year did {e} open for the first time?", "How old is {e}?"]),
    ("staff", "employs {v} people", ["12", "45", "130", "800"], ["How many people work at {e}?", "Staff size of {e}?", "How many employees does {e} have?"]),
    ("director", "is run by {v}", ["Dr. Imani Cole", "Paul Varga", "Mei Tanaka", "Sofia Lund"], ["Who runs {e}?", "Who is the director of {e}?", "Who manages {e}?"]),
    ("parking", "offers {v} parking spaces", ["20", "150", "no"], ["Is there parking at {e}?", "How many parking spots does {e} have?"]),
    ("fee", "charges an entry fee of {v}", ["$5", "$12", "nothing", "EUR 8"], ["How much does it cost to get into {e}?", "What is the admission price at {e}?"]),
]


def _entity(rng):
    return f"the {pick(rng, ENT_A)} {pick(rng, ENT_B)}"


def rag(rng: R):
    e = _entity(rng)
    attrs = rng.sample(ATTRS, 3)
    facts = {a[0]: pick(rng, a[2]) for a in attrs}
    sents = [f"{cap(e)} {a[1].replace('{v}', facts[a[0]])}." for a in attrs[:2]]
    if rng.random() < 0.4:
        sents.append(pick(rng, ["It was renovated last spring.", "Visitors praise the friendly staff.", "It is popular with families.", "The building has a green roof."]))
    rng.shuffle(sents)
    passage = " ".join(sents)
    kind = rng.random()
    if kind < 0.5:
        a = attrs[0] if rng.random() < 0.5 else attrs[1]
        q, lab = pick(rng, a[3]).replace("{e}", e), "yes"
    elif kind < 0.8:
        q, lab = pick(rng, attrs[2][3]).replace("{e}", e), "no"  # same entity, missing attribute
    else:
        other = _entity(rng)
        if other == e:
            other = "the " + pick(rng, ENT_A) + " Annex"
        q, lab = pick(rng, attrs[0][3]).replace("{e}", other), "no"  # same attribute, other entity
    st = {"query": cap(q), "passage": passage} if rng.random() < 0.6 else f"Question: {cap(q)}\nPassage: {passage}"
    return seed("rag_relevant", st, lab, "rag")


def answer_grade(rng: R):
    e = _entity(rng)
    a = pick(rng, ATTRS)
    gold = pick(rng, a[2])
    wrong = pick(rng, [v for v in a[2] if v != gold])
    q = pick(rng, a[3]).replace("{e}", e)
    k = rng.random()
    if k < 0.35:
        ans, lab = pick(rng, [f"{cap(e)} {a[1].replace('{v}', gold)}.", f"{gold}.", f"It's {gold}, as far as I know.", f"The answer is {gold}."]), "correct"
    elif k < 0.65:
        ans, lab = pick(rng, [f"{cap(e)} {a[1].replace('{v}', wrong)}.", f"{wrong}.", f"I believe it's {wrong}."]), "incorrect"
    elif k < 0.8:
        ans, lab = pick(rng, [f"Either {gold} or {wrong}, not sure which.", f"Around {gold}, though it may vary; also it {pick(rng, ATTRS)[1].replace('{v}', 'unknown')}."]), "partially_correct"
    else:
        ans, lab = pick(rng, ["I don't know.", "I can't answer that.", f"{cap(e)} is a lovely place to visit.", "Sorry, I have no information about that."]), "not_attempted"
    st = {"question": cap(q), "reference": gold, "answer": ans} if rng.random() < 0.6 else f"Q: {cap(q)}\nReference: {gold}\nCandidate: {ans}"
    return seed("answer_grade", st, lab, "grade")


# ================================================================== tool + model routing

TOOL_REQ = {
    "calculator": ["What's {p}% of {n},{m}?", "Split a ${n}.{m} bill between {k} people.", "How many seconds are in {k} days?", "Compound interest on ${n}000 at {k}% for {k} years?", "{n} times {m} minus {k}?"],
    "web_search": ["What's the latest news about {topic}?", "Current exchange rate from euro to yen?", "Who won the {topic} match last night?", "Find reviews of the newest {thing}.", "What's the weather in Lisbon tomorrow?"],
    "code_interpreter": ["Plot the attached sales.csv by month.", "Run this Python snippet and tell me the output.", "Parse this JSON file and count the unique users.", "Fit a regression on the uploaded data."],
    "sql_query": ["How many orders did we get last week in our database?", "Pull the top 10 customers by revenue from the warehouse.", "What's our churn rate this quarter from the subscriptions table?", "Count signups per day from the users table."],
    "calendar": ["Book a 30-minute call with {name} on Tuesday at 3pm.", "Am I free Friday afternoon?", "Move my 1:1 with {name} to next week.", "Schedule the quarterly review for the whole team."],
    "email_send": ["Email {name} the slides from today.", "Send a thank-you note to the candidate we interviewed.", "Reply to {name} saying I'll be late.", "Forward the invoice to accounting."],
    "file_search": ["Find the Q3 planning doc in my drive.", "Where's the signed NDA with Acme?", "Open the onboarding checklist I wrote in March.", "Look up the latest brand guidelines PDF."],
    "image_generation": ["Draw a logo of a fox wearing headphones.", "Make an illustration of a cozy cabin for the newsletter.", "Generate a banner image for our launch.", "Create a cartoon of a robot gardener."],
    "translation": ["Translate this paragraph into German.", "How do you say 'see you tomorrow' in Portuguese?", "Put this email into formal French.", "Translate the product description to Spanish."],
    "human_handoff": ["I want to talk to a real person.", "I'm going to sue you, connect me with your legal team.", "Get me a manager now.", "This is about a death in the family and the account; I need a human."],
    "no_tool": ["Thanks, that's all!", "What's the difference between a list and a tuple?", "Tell me a joke about cats.", "Hi!", "Explain photosynthesis simply."],
}
MODEL_REQ = {
    "small_fast_llm": ["Fix the grammar in this sentence.", "Extract the email address from this signature.", "Classify this tweet as positive or negative.", "Summarize this paragraph in one line.", "Rewrite this title in title case."],
    "large_reasoning_llm": ["Plan a migration strategy for 40 microservices with zero downtime and explain trade-offs.", "Prove that the sum of two odd numbers is even, step by step.",
                            "Analyze this 30-page contract for conflicting obligations.", "Design an experiment to separate the effects of price and seasonality.", "Find the flaw in this multi-step financial argument."],
    "code_llm": ["Write a Python function that merges overlapping intervals.", "Refactor this React component to use hooks.", "Why does this Go code deadlock?", "Port this bash script to PowerShell.", "Add unit tests for the parser module."],
    "vision_llm": ["What's in this screenshot?", "Read the numbers off this photo of a receipt.", "Describe the chart in the attached image.", "Is the rash in this photo spreading?", "Transcribe the handwriting in this scan."],
    "speech_model": ["Transcribe this voicemail.", "Turn this recording of the meeting into text.", "Read this paragraph aloud as audio.", "Generate a voiceover for the intro."],
    "no_llm": ["Convert 5 kilometers to miles.", "Look up order #{n} status in the system.", "Return today's date.", "Check if the user is on the enterprise plan.", "Count characters in this string."],
}


def _fill_req(rng, t):
    return (t.replace("{p}", str(rng.randint(3, 40))).replace("{n}", str(rng.randint(10, 999))).replace("{m}", str(rng.randint(10, 99))).replace("{k}", str(rng.randint(2, 9)))
            .replace("{name}", pick(rng, NAMES)).replace("{topic}", pick(rng, ["the election", "the Champions League", "the chip shortage", "the Mars mission"]))
            .replace("{thing}", pick(rng, ["e-reader", "smartwatch", "air fryer"])))


def routing(rng: R):
    if rng.random() < 0.6:
        lab = pick(rng, list(TOOL_REQ))
        return seed("tool_route", _fill_req(rng, pick(rng, TOOL_REQ[lab])), lab, "route")
    lab = pick(rng, list(MODEL_REQ))
    return seed("model_route", _fill_req(rng, pick(rng, MODEL_REQ[lab])), lab, "route")


# ================================================================== ecommerce intent (keyword-avoiding paraphrases)

PRODS = ["shoes", "jacket", "phone case", "blender", "lamp", "backpack", "headphones", "rug", "dress", "watch", "coffee grinder", "office chair"]
ECOM = {
    "track_order": ["Where's my {p}? It's been {k} days.", "Any idea when my {p} shows up?", "The {p} still hasn't arrived and the app says 'in transit'.", "Has my parcel left the warehouse yet?",
                    "Is the {p} I bought on {d} on its way?", "Still waiting on the {p}..."],
    "return_item": ["The {p} is a size too small, how do I send it back?", "I'd like to swap the {p} for a different color.", "Got the {p} but it's scratched. I want to return it.",
                    "Can I bring the {p} back to a store?", "Need a prepaid label to ship the {p} back."],
    "cancel_order": ["I ordered the {p} by mistake an hour ago, please don't ship it.", "Stop my order for the {p} before it goes out.", "I changed my mind about the {p}, can you call off the order?"],
    "refund_status": ["You said my refund for the {p} was processed {k} days ago but I don't see it.", "When will the money for the returned {p} hit my card?", "Still no credit for the {p} I sent back."],
    "product_question": ["Is the {p} waterproof?", "Does the {p} come in XL?", "Will this {p} work with an iPhone 15?", "What's the {p} made of?", "Is the {p} back in stock soon?",
                         "Before I order: how heavy is the {p}?"],
    "payment_issue": ["My card keeps getting declined at checkout.", "I was charged twice for the {p}.", "The total on my statement is higher than the price of the {p}.", "Apple Pay fails on the last step."],
    "change_address": ["I moved - can the {p} go to my new place instead?", "Wrong apartment number on my order, it should be 4B.", "Please ship the {p} to my office, not home."],
    "account_help": ["I can't log in to my account.", "How do I change the email on my profile?", "My password reset link doesn't work.", "Please delete my saved card from my account."],
    "complaint": ["Your service has gone downhill, I'm really disappointed.", "Third time something's gone wrong with you people.", "The courier was rude and threw the box."],
    "other": ["Do you have a careers page?", "Are you open on public holidays?", "Can I partner with you as an influencer?", "Who designed your logo?"],
}


def ecom(rng: R):
    lab = pick(rng, list(ECOM))
    t = pick(rng, ECOM[lab]).replace("{p}", pick(rng, PRODS)).replace("{k}", str(rng.randint(3, 14))).replace("{d}", pick(rng, ["Monday", "the 3rd", "Black Friday"]))
    return seed("ecom_intent", t, lab, "prog")


# ================================================================== multilingual-lite (short)

ML = {
    "es": {"positive": ["¡Me encanta! Funciona perfecto.", "No está nada mal, la verdad.", "Muy buena calidad, lo recomiendo."], "negative": ["Llegó roto y nadie responde.", "Qué maravilla, otra vez se cayó la app. Genial.", "No me gustó para nada."],
           "neutral": ["El paquete llegó el martes.", "¿Tienen esta talla en azul?"], "track_order": ["¿Dónde está mi pedido?", "Mi paquete no ha llegado todavía."], "return_item": ["Quiero devolver los zapatos, son pequeños."]},
    "fr": {"positive": ["Pas mal du tout, je suis ravi.", "Excellent service, merci !", "Rien à redire, parfait."], "negative": ["Très déçu, le produit ne marche pas.", "Super, encore une panne. Bravo.", "Je ne suis pas satisfait."],
           "neutral": ["La commande est arrivée lundi.", "Est-ce disponible en noir ?"], "track_order": ["Où en est ma commande ?", "Mon colis n'est toujours pas arrivé."], "return_item": ["Je voudrais retourner la veste, elle est trop grande."]},
    "de": {"positive": ["Gar nicht schlecht, bin zufrieden.", "Super Qualität, gerne wieder!", "Alles bestens."], "negative": ["Leider kaputt angekommen.", "Toll, schon wieder abgestürzt. Danke für nichts.", "Nicht zu empfehlen."],
           "neutral": ["Die Lieferung kam am Dienstag.", "Gibt es das auch in Größe M?"], "track_order": ["Wo ist meine Bestellung?", "Mein Paket ist noch nicht da."], "return_item": ["Ich möchte die Schuhe zurückschicken, zu klein."]},
    "pt": {"positive": ["Nada mal, gostei muito.", "Ótimo atendimento, recomendo!", "Perfeito, chegou rápido."], "negative": ["Veio quebrado e ninguém responde.", "Que beleza, travou de novo. Parabéns.", "Não gostei nada."],
           "neutral": ["O pedido chegou na terça.", "Tem em tamanho grande?"], "track_order": ["Cadê meu pedido?", "Minha encomenda ainda não chegou."], "return_item": ["Quero devolver a camisa, ficou pequena."]},
}


def multilingual(rng: R):
    lang = pick(rng, list(ML))
    lab = pick(rng, list(ML[lang]))
    text = pick(rng, ML[lang][lab])
    task = "ecom_intent" if lab in ("track_order", "return_item") else "sentiment"
    return seed(task, text, lab, "ml", lang=lang)


# ================================================================== moderation / threats (violent vocabulary on both sides)

M_TARGET = ["that ref", "the landlord", "my ex", "the guy in 4B", "the moderator", "the reporter", "the delivery driver", "my neighbour", "the new manager"]
M_WHEN = ["when you leave work on Friday", "tonight", "next time I see you", "after the meeting", "before the weekend is over", "the moment you step outside",
          "at the school gates tomorrow", "when the shift ends"]
THREAT_YOU = ["I know where you live, and I'll be waiting {w}.", "Watch your back {w}, I'm going to hurt you.", "I'm bringing a knife {w}. You won't see it coming.",
              "Keep talking and I'll make sure you end up in hospital {w}.", "I'm going to burn your car {w}, try me.", "Last warning: drop the complaint or you get hurt {w}.",
              "You'll regret this. I'm coming over {w} with my bat.", "I will find your family {w} and make them pay."]
THREAT_3P = ["Someone should put a bullet in {t}, and I might be that someone.", "I'm going to break {t}'s legs {w2}.", "{T} is going to get hurt {w2}, I'll make sure of it.",
             "I've got a plan for {t} {w2}. Bringing the gun this time.", "If {t} shows up {w2}, I'm stabbing them, no joke."]
M_WHEN3 = ["tomorrow", "this weekend", "after the game", "on Monday", "tonight"]
HYPERBOLE = ["I'm going to kill this presentation tomorrow.", "This deadline is absolutely murdering me.", "We're going to destroy them on Saturday, the defence has no chance.",
             "I could strangle my printer right now.", "I'll wreck you next round, noob.", "That comedian absolutely slayed last night.", "My feet are killing me after that hike.",
             "If the build breaks again I'm going to scream into a pillow.", "Our striker is going to bury them in the second half.", "I'd kill for a coffee right now.",
             "Gonna hunt down every last achievement this weekend.", "I'm going to murder this plate of ribs."]
CRITICISM = ["The mayor's housing plan is a disaster and she should resign.", "This update is absolute garbage, what the hell were they thinking?",
             "Worst refereeing I've seen all season, a total joke.", "The council keeps wasting our money and nobody is accountable.", "This film was a bloated, boring mess.",
             "Honestly the new policy is stupid and I'll be voting against it.", "Damn, this app crashes every single time. Fix your stuff."]
INSULT = ["You're an absolute moron, {n}.", "{n}, nobody here likes you, just leave.", "Typical {n}, too dumb to read the thread.", "Shut up {n}, you clueless idiot."]
SELFHARM = ["I don't see the point anymore, maybe everyone's better off without me.", "Some days I think about just disappearing for good.",
            "I've been giving my stuff away. It won't matter soon anyway."]
SPAM = ["Earn ${k}/day from home!!! No experience needed, click bit.ly/{c}", "CHEAP followers + likes, DM now or visit {c}.biz", "Hot singles near you -> {c}.xyz",
        "Crypto giveaway! Send 0.1 BTC, get 1 BTC back, link in bio {c}"]
DOXX = ["Here's {n}'s home address: {a}. Go pay a visit and let them know what we think.", "Found {n}'s personal phone {p} and workplace, spread it everywhere.",
        "{n} lives at {a}, their kids go to the school on the corner. You know what to do."]


def moderation(rng: R):
    r = rng.random()
    if r < 0.28:
        if rng.random() < 0.6:
            txt = pick(rng, THREAT_YOU).replace("{w}", pick(rng, M_WHEN))
        else:
            tg = pick(rng, M_TARGET)
            txt = pick(rng, THREAT_3P).replace("{t}", tg).replace("{T}", cap(tg)).replace("{w2}", pick(rng, M_WHEN3))
        lab, threat, tag = "remove", "yes", "threat"
    elif r < 0.5:
        txt, lab, threat, tag = pick(rng, HYPERBOLE), "allow", "no", "hyperbole"
    elif r < 0.64:
        txt, lab, threat, tag = pick(rng, CRITICISM), "allow", "no", "criticism"
    elif r < 0.76:
        txt, lab, threat, tag = pick(rng, INSULT).replace("{n}", pick(rng, NAMES)), "review", "no", "insult"
    elif r < 0.82:
        txt, lab, threat, tag = pick(rng, SELFHARM), "review", "no", "selfharm"
    elif r < 0.91:
        txt = pick(rng, SPAM).replace("{k}", str(rng.randint(300, 900))).replace("{c}", "".join(rng.choices("abcdefghjkmnpqrstuvwxyz0123456789", k=6)))
        lab, threat, tag = "remove", "no", "spam"
    else:
        txt = pick(rng, DOXX).replace("{n}", pick(rng, NAMES)).replace("{a}", f"{rng.randint(2, 98)} {pick(rng, STREETS)}, {pick(rng, CITIES)}").replace("{p}", _phone(rng))
        lab, threat, tag = "remove", "no", "doxx"
    if rng.random() < 0.6 and tag in ("threat", "spam", "doxx", "selfharm"):
        # threats are noisy on purpose: the remove label must survive surrounding chatter
        txt = f"{pick(rng, ['lol', 'Not joking.', 'Read this carefully.', 'Whatever.', 'Seriously,'])} {txt}"
    if rng.random() < 0.35 and tag != "selfharm":
        return seed("has_threat", txt, threat, f"mod_{tag}")
    soft = {"review": 0.75, "remove": 0.25} if tag == "insult" and rng.random() < 0.3 else None
    return seed("moderation", txt, lab, f"mod_{tag}", soft)


GENERATORS = [
    ("sentiment", sentiment, 0.16), ("review_stars", review_stars, 0.05), ("incident", incident_severity, 0.12), ("lead", lead, 0.07),
    ("agent_gate", agent_gate, 0.18), ("pii", pii, 0.06), ("secret", secret, 0.04), ("scam", scam, 0.06), ("rag", rag, 0.07),
    ("answer_grade", answer_grade, 0.04), ("routing", routing, 0.07), ("ecom", ecom, 0.06), ("multilingual", multilingual, 0.02),
    ("moderation", moderation, 0.07),
]


def prog_seed(rng: R) -> dict:
    names = [g[0] for g in GENERATORS]
    w = [g[2] for g in GENERATORS]
    fn = dict((g[0], g[1]) for g in GENERATORS)[rng.choices(names, weights=w)[0]]
    return fn(rng)
