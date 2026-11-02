"""Keel-2 synthetic task families.

Every family yields groups: one state, one wire-shaped question, one target
distribution over the question's hypotheses. Domains used by the open-domain
eval (sentiment, shopping intent, community moderation, HR routing, news topics,
incident priority, star ratings, email urgency, spam, PII, deadlines, sales
leads, contract clauses) are deliberately absent so that suite stays out-of-domain.
"""
from __future__ import annotations

import json
import random
from typing import Callable, Iterator

Group = dict
R = random.Random

# ---------------------------------------------------------------- helpers

NAMES = ["Ana", "Ben", "Chen", "Dara", "Eli", "Fatima", "Gus", "Hana", "Ivan", "Jo", "Kofi", "Lena", "Mateo", "Nia", "Omar", "Priya", "Quinn", "Rosa", "Sven", "Tariq", "Uma", "Vic", "Wen", "Yusuf", "Zoe"]
PRODUCTS = ["the dashboard", "the mobile app", "the admin console", "the reports page", "the editor", "the API", "the desktop client", "the portal", "the scheduler", "the analytics view"]
FILLER = [
    "Thanks in advance.", "Sent from my phone.", "We are on the team plan.", "This started this morning.",
    "Our account manager is out this week.", "Let me know if you need anything else.", "I attached a screenshot.",
    "We have used the product for two years.", "Hope you are well.", "Ticket opened via email.", "Region: EU.",
    "No rush on the reply.", "Browser: Firefox.", "Version 4.2.", "Happens for two colleagues too.",
]
AMBIGUOUS = [
    "hi", "Hello there.", "test", "ok", "?", "Thanks!", "see above", "Following up.", "Any update?", "hmm",
    "Good morning team.", "N/A", "same as before", "ping", "...", "Please advise.", "Hey, quick question.",
    "Just checking in.", "cheers", "Is anyone there?", "lol", "See attached.", "1", "yes", "Call me.",
]


def cap(text: str) -> str:
    return text[:1].upper() + text[1:]


def pick(rng: R, items):
    return items[rng.randrange(len(items))]


def sample(rng: R, items, k):
    return rng.sample(list(items), k)


def fill(rng: R, template: str) -> str:
    return (
        template.replace("{name}", pick(rng, NAMES))
        .replace("{product}", pick(rng, PRODUCTS))
        .replace("{n}", str(rng.randint(2, 9)))
        .replace("{month}", pick(rng, ["January", "March", "May", "July", "August", "October", "December"]))
    )


def decorate(rng: R, text: str, *, allow_json: bool = True) -> str:
    """Surface noise: prefixes, filler, casing, JSON envelopes."""
    roll = rng.random()
    if roll < 0.12 and allow_json:
        env = {pick(rng, ["message", "body", "text", "description", "ticket"]): text}
        if rng.random() < 0.6:
            env[pick(rng, ["plan", "channel", "priority_hint", "source"])] = pick(rng, ["team", "email", "chat", "web", "pro", "none"])
        return json.dumps(env)
    if roll < 0.35:
        text = f"{pick(rng, ['Customer:', 'User:', 'Ticket:', 'From ' + pick(rng, NAMES) + ':', 'Report:', 'Note:'])} {text}"
    if rng.random() < 0.3:
        text = f"{text} {pick(rng, FILLER)}" if rng.random() < 0.6 else f"{pick(rng, FILLER)} {text}"
    if rng.random() < 0.07:
        text = text.lower()
    return text


def one_hot(n: int, i: int, smooth: float = 0.0) -> list[float]:
    base = smooth / n
    return [base + (1 - smooth if j == i else 0) for j in range(n)]


def ordinal(n: int, position: float, spread: float = 0.35) -> list[float]:
    """Soft target around a (possibly fractional) level index."""
    import math

    w = [math.exp(-((j - position) ** 2) / (2 * spread**2)) for j in range(n)]
    s = sum(w)
    return [x / s for x in w]


def choice_group(family, state, instructions, options, gold_key, smooth=0.04):
    keys = [k for k, _ in options]
    return {
        "family": family,
        "state": state,
        "question": {"type": "choice", "instructions": instructions, "criteria": {k: d for k, d in options}},
        "target": one_hot(len(keys), keys.index(gold_key), smooth),
        "gold": keys.index(gold_key),
    }


def uniform_choice(family, state, instructions, options):
    n = len(options)
    return {
        "family": family,
        "state": state,
        "question": {"type": "choice", "instructions": instructions, "criteria": {k: d for k, d in options}},
        "target": [1 / n] * n,
        "gold": -1,
    }


def score_group(family, state, instructions, levels, position, spread=0.35):
    return {
        "family": family,
        "state": state,
        "question": {"type": "score", "instructions": instructions, "criteria": list(levels)},
        "target": ordinal(len(levels), position, spread),
        "gold": round(position),
    }


def noul_group(family, state, instructions, yes, no, p_yes):
    criteria = {}
    if yes:
        criteria["true"] = yes
    if no:
        criteria["false"] = no
    q = {"type": "noul", "instructions": instructions}
    if criteria:
        q["criteria"] = criteria
    return {"family": family, "state": state, "question": q, "target": [p_yes, 1 - p_yes], "gold": 0 if p_yes >= 0.5 else 1}


# ---------------------------------------------------------------- support routing

SUPPORT = {
    "billing": {
        "keys": ["billing", "payments", "finance", "invoicing"],
        "desc": ["Money, invoices, refunds, seats", "Charges, invoices, refunds, subscriptions", "Anything about payment or what the customer was charged", None],
        "states": [
            "I was billed {n} times for the same {month} subscription.",
            "Can I get a refund for the unused seats on our plan?",
            "The invoice total does not match the price on your website.",
            "Please update the VAT number printed on our receipts.",
            "My card was declined but the money still left my account.",
            "We downgraded to the basic tier but were still charged for pro.",
            "Why did the annual renewal cost more than last year?",
            "Remove the extra seat we added by mistake and credit us.",
            "I need a copy of every receipt from {month} for accounting.",
            "The trial converted to paid without warning and I want my money back.",
            "Our purchase order number is missing from the invoice.",
            "Switch our payment method from card to bank transfer.",
            "A duplicate charge of $49 appeared on the statement.",
            "We were charged in dollars instead of euros.",
            "How do I cancel auto-renew before the next billing date?",
            "The discount code was not applied to the checkout total.",
            "Seats: 12 on the invoice, only 9 people use it. Please prorate.",
            "Payment failed and now the plan says past due.",
        ],
    },
    "bug": {
        "keys": ["bug", "defect", "product_bug", "broken"],
        "desc": ["The product is broken", "Something in the product is broken", "Errors, crashes, wrong behavior in our app", None],
        "states": [
            "{product} shows a blank white screen after the latest release.",
            "Clicking save does nothing and the console shows a TypeError.",
            "The date picker jumps back a month every time I open it.",
            "Exports come out empty even though the table has rows.",
            "The app crashes on launch since the update.",
            "Sorting by name puts lowercase entries last.",
            "The progress bar stays at 99% forever.",
            "Notifications show yesterday's items twice.",
            "Uploading a PNG over 2MB throws an unknown error.",
            "The search results page freezes when I type quickly.",
            "Totals in the summary row are off by one.",
            "Dark mode makes the button text invisible.",
            "{product} throws a 500 when I open a record with an emoji in the title.",
            "Charts render upside down on Safari.",
            "Drag and drop reorders the wrong card.",
            "Undo deletes the whole paragraph instead of the last word.",
        ],
    },
    "account": {
        "keys": ["account", "access", "login", "identity"],
        "desc": ["Login, password, or permissions", "Sign-in, profile, roles and permissions", "Getting into the account or changing who can do what", None],
        "states": [
            "I cannot sign in; it says my password is wrong but I just changed it.",
            "The password reset link has expired twice.",
            "Please give {name} admin rights on our workspace.",
            "My account is locked after too many attempts.",
            "I changed jobs and need to move the account to my new email.",
            "The SSO login loops back to the start page.",
            "Remove a former employee from our team.",
            "I need viewer access to the finance folder.",
            "Merge my two accounts into one.",
            "The invite email never arrived for our new hire.",
            "Change the owner of the organization to {name}.",
            "Why can't I see the settings tab anymore? My role changed.",
            "Deactivate my profile and delete my login.",
        ],
    },
    "security": {
        "keys": ["security", "vulnerability", "infosec", "trust_safety"],
        "desc": ["Vulnerability, injection, or leaked secrets", "Unauthorized access, injection, exposed credentials", "A security hole that someone could exploit", None],
        "states": [
            "A crafted link runs JavaScript in the victim's browser on the comments page.",
            "Your public bucket lists every customer's uploaded contracts.",
            "An old API key is hard-coded in your mobile app bundle.",
            "The password reset token is sent in the URL and logged by proxies.",
            "Uploading a file named with ../ writes outside the upload folder.",
            "The admin endpoint does not check if the caller is an admin.",
            "Session cookies are not marked secure or httpOnly.",
            "I can see raw database errors with the SQL statement in the response.",
            "Our staff password list was pasted into a public forum.",
            "Rate limiting is missing on the login form; brute force works.",
            "The export feature lets any logged-in user download all tenants' data.",
            "Server-side request forgery: the webhook tester fetches internal metadata URLs.",
            "Deserializing the uploaded config file executes arbitrary code.",
        ],
    },
    "technical": {
        "keys": ["technical", "integrations", "infrastructure", "platform"],
        "desc": ["Integrations, webhooks, or outages", "Bugs in integrations, APIs, or service outages", "Connectors, sync, uptime, third-party systems", None],
        "states": [
            "The Salesforce sync has not pulled new contacts since Tuesday.",
            "Webhooks to our endpoint time out and retry endlessly.",
            "Your service has been unreachable from our region for an hour.",
            "The Zapier connector fails with an authentication error.",
            "Our SAML identity provider integration stopped updating groups.",
            "The REST API returns 503 for every call right now.",
            "Events from the calendar integration arrive three hours late.",
            "The Jira plugin no longer creates tickets.",
            "DNS for our custom domain is not resolving to your servers.",
            "Batch imports from the SFTP drop fail at the parsing step.",
            "The GitHub app lost its connection to our organization.",
            "Latency to the API jumped from 80ms to 4s.",
            "The HubSpot integration duplicates every deal.",
        ],
    },
    "feature_request": {
        "keys": ["feature_request", "product_idea", "roadmap"],
        "desc": ["A suggestion for something new", "Requests for new capabilities", None],
        "states": [
            "It would be great if we could schedule reports to go out weekly.",
            "Please add a dark theme.",
            "Could you support exporting to Parquet in the future?",
            "We'd love keyboard shortcuts for the editor.",
            "Any plans for an offline mode?",
            "Suggestion: let us pin favorite dashboards.",
            "Can you add a Spanish translation of the interface?",
        ],
    },
    "privacy": {
        "keys": ["privacy", "legal", "compliance"],
        "desc": ["Data requests, GDPR, legal questions", "Privacy, data deletion, compliance paperwork", None],
        "states": [
            "Under GDPR I request a copy of all data you hold on me.",
            "Please sign our data processing agreement.",
            "Where are your servers located for data residency purposes?",
            "Erase all personal data about me from your systems.",
            "Do you have a SOC 2 report we can review?",
            "Our lawyer needs your subprocessor list.",
        ],
    },
}

ROUTE_INSTR = [
    "Which path fits this case?", "Which team should handle this ticket?", "Route this message.",
    "What kind of issue is this?", "Which queue does this belong in?", "Classify the request.",
    "Where should support send this?", "Pick the category for this conversation.",
]

NEG_TEMPLATES = [
    "This is not a {x} issue.", "It's not about {x}.", "Not {x} related.", "No {x} problem here.",
    "I am not asking about {x}.", "Don't send this to {x}.",
]


def support_route(rng: R) -> Group:
    labels = list(SUPPORT)
    gold = pick(rng, labels)
    k = rng.randint(3, min(6, len(labels)))
    others = sample(rng, [l for l in labels if l != gold], k - 1)
    chosen = others + [gold]
    rng.shuffle(chosen)
    spec = {l: SUPPORT[l] for l in chosen}
    options = []
    for l in chosen:
        key = pick(rng, spec[l]["keys"])
        options.append((key, pick(rng, spec[l]["desc"])))
    gold_key = options[chosen.index(gold)][0]
    if gold == "security" and rng.random() < 0.5:
        text = compose_vuln(rng)
    else:
        text = fill(rng, pick(rng, SUPPORT[gold]["states"]))
    roll = rng.random()
    if roll < 0.18:
        # negate a distractor, keep the gold fact
        wrong = pick(rng, others)
        neg = pick(rng, NEG_TEMPLATES).replace("{x}", pick(rng, [wrong.replace("_", " "), SUPPORT[wrong]["keys"][0].replace("_", " ")]))
        text = f"{neg} {text}" if rng.random() < 0.6 else f"{text} {neg}"
    elif roll < 0.28:
        # a secondary, weaker mention of another topic
        wrong = pick(rng, others)
        text = f"{text} (Unrelated: last month {pick(rng, ['billing', 'login', 'the integration', 'the app'])} was fine.)"
    return choice_group("support_route", decorate(rng, text), pick(rng, ROUTE_INSTR), options, gold_key)


# ---------------------------------------------------------------- severity / impact

SEVERITY_BANK = {
    0: [
        "A heading in the docs has a spelling mistake.", "The tooltip uses the old product name.",
        "The logo is slightly blurry on retina screens.", "One icon is misaligned by a few pixels.",
        "The footer copyright still says last year.", "Cosmetic: the button corners are square instead of round.",
        "The help article has a broken image, nothing else is affected.", "A label is capitalized inconsistently.",
    ],
    1: [
        "Bulk export is broken; exporting one report at a time still works.", "Bulk edit is broken; editing one at a time works.",
        "Search misses some results; filtering by tag finds them.", "The app is slow in the afternoon but usable.",
        "Sorting is wrong, but we can sort in the spreadsheet.",
        "The shortcut stopped working; the menu item still does it.",
    ],
    2: [
        "Nobody on the team can submit orders; the pay button is dead.", "We cannot publish anything, so our launch is stuck.",
        "Every login attempt fails for our whole company.", "The import fails every time and there is no other way to load data.",
        "Payroll cannot run because the approval step errors.", "Customers cannot finish checkout at all.",
        "Our agents cannot open any tickets this morning.",
    ],
    3: [
        "The sync overwrote a year of invoices with blanks.", "Every user's secret token was exposed in the public logs.",
        "They are cancelling the contract on Friday unless this is fixed today.", "Invoices were sent to the wrong customers with their data.",
        "The migration wiped our production database.", "The CEO says we are moving to a competitor this week.",
        "Payment card numbers are visible to other tenants.",
    ],
}
SEVERITY_SCALES = [
    (["Cosmetic", "Workaround exists", "Blocks the task", "Data loss or about to churn"], [0, 1, 2, 3]),
    (["Low", "Medium", "High", "Critical"], [0, 1, 2, 3]),
    (["Trivial", "Minor", "Major", "Blocker", "Catastrophic"], [0, 1, 2.5, 3.5, 4]),
    (["Minor", "Serious", "Critical"], [0, 0.8, 1.5, 2]),
    (["No real impact", "Annoying but workable", "Stops work", "Loses data or customers"], [0, 1, 2, 3]),
    (["S4", "S3", "S2", "S1"], [0, 1, 2, 3]),
]
SEVERITY_INSTR = ["How severe is this for the customer?", "Rate the impact.", "How bad is this problem?", "What severity should this get?", "How much does this hurt the user?"]


def severity(rng: R) -> Group:
    levels, positions = pick(rng, SEVERITY_SCALES)
    cls = rng.randrange(4)
    text = fill(rng, pick(rng, SEVERITY_BANK[cls]))
    pos = positions[cls] if cls < len(positions) else positions[-1]
    if len(levels) == 3:
        pos = [0, 0.8, 1.5, 2][cls]
    return score_group("severity", decorate(rng, text), pick(rng, SEVERITY_INSTR), levels, pos)


# ---------------------------------------------------------------- security noul

VULN_INSTR = [
    ("Does this describe a vulnerability?", "Unauthorized access, injection, leaked secrets, or a trust-boundary bug", "Ordinary product or billing trouble"),
    ("Is this a security issue?", "Someone could gain access, read data, or run code they should not", "A normal bug, question, or request"),
    ("Should the security team see this?", "It involves exploitation, exposure, or leaked credentials", None),
    ("Is there a security risk here?", None, None),
]


VULN_ACTORS = ["Any logged-in user", "A free-plan customer", "Someone without an account", "A user from another company", "An intern",
               "A random visitor", "A customer on a different workspace"]
VULN_OBJECTS = ["other customers' invoices", "the admin settings", "private messages of other users", 
                "every user's email address", "payment details that are not theirs", "internal audit logs", "someone else's uploaded files"]
VULN_ACCESS = ["{a} is able to read {o}.", "{a} can download {o} from the export page.",
               "{a} sees {o} after the last release.", "By guessing the link, {a} gets {o}."]
VULN_LEAKS = ["{s} shows up in the browser console.", "{s} is visible in the page source.",
              "Our logs contain {s} in plain text and the logs are shared with a vendor.", "{s} was posted in a public Discord channel.",
              "{s} ended up in a public gist."]
VULN_INJECT = ["Typing a quote in the {f} field returns a raw SQL error.", "HTML in the {f} field is rendered and scripts run for other users.",
               "The {f} field lets you run shell commands on the server.", "Putting a script tag in {f} pops an alert for every viewer.",
               "The {f} parameter is passed straight into a database query."]
VULN_FIELDS = ["display name", "search", "comment", "bio", "file name", "coupon code", "address", "title"]


def compose_vuln(rng: R) -> str:
    kind = rng.random()
    if kind < 0.4:
        return pick(rng, VULN_ACCESS).format(a=pick(rng, VULN_ACTORS), o=pick(rng, VULN_OBJECTS))
    if kind < 0.7:
        return cap(pick(rng, VULN_LEAKS).format(s=pick(rng, SECRETS)))
    return pick(rng, VULN_INJECT).format(f=pick(rng, VULN_FIELDS))


def vuln_noul(rng: R) -> Group:
    instr, yes, no = pick(rng, VULN_INSTR)
    is_vuln = rng.random() < 0.45
    if is_vuln:
        if rng.random() < 0.55:
            text = compose_vuln(rng)
        else:
            text = fill(rng, pick(rng, SUPPORT["security"]["states"] + SEVERITY_BANK[3][1:2] + [SEVERITY_BANK[3][6]]))
        p = 0.95
    else:
        other = pick(rng, ["billing", "bug", "account", "technical", "feature_request"])
        text = fill(rng, pick(rng, SUPPORT[other]["states"]))
        if rng.random() < 0.25:
            text = f"{pick(rng, ['This is not a security problem.', 'Nothing was exposed.', 'No data leaked.', 'Not a vulnerability.'])} {text}"
        p = 0.05
    return noul_group("vuln", decorate(rng, text), instr, yes if rng.random() < 0.8 else None, no if rng.random() < 0.7 else None, p)


# ---------------------------------------------------------------- coding agent: edit / ask / stop

FILES = ["src/routes/settings.tsx", "src/lib/math.ts", "README.md", "src/components/button.tsx", "api/handlers/user.go", "app/models/order.rb",
         "services/billing/invoice.py", "src/utils/format.js", "docs/setup.md", "lib/parser.rs", "src/pages/index.vue", "tests/test_cart.py",
         "src/server/routes.ts", "cmd/cli/main.go", "src/hooks/useCart.ts", "package.json", "Dockerfile", ".github/workflows/ci.yml",
         "src/styles/theme.css", "backend/app/views.py"]
SYMBOLS = ["formatDate", "parseQuery", "total", "userId", "renderRow", "CartItem", "retry_count", "handleSubmit", "MAX_ITEMS", "get_invoice", "slugify", "isEmpty"]

EDIT_TASKS = [
    ("Rename the variable {sym} to {sym2} in {file}.", 1, False),
    ("Fix the typo 'recieve' in the heading of {file}.", 0, False),
    ("Add a null check before calling {sym} in {file}.", 2, True),
    ("Update the comment above {sym} in {file} to explain the return value.", 0, False),
    ("Add a unit test for {sym} in tests/test_{base}.py covering the empty input case.", 1, False),
    ("Change the button label from 'Submit' to 'Save' in {file}.", 0, False),
    ("In {file}, make {sym} return an empty list instead of null when there are no rows.", 2, True),
    ("Extract the duplicated date formatting in {file} into a helper named {sym}.", 1, True),
    ("Add a loading spinner to the save button in {file} while the request is pending.", 2, True),
    ("Fix the off-by-one in the loop inside {sym} in {file}; it skips the last element.", 2, True),
    ("Sort the imports in {file}. No behavior change.", 0, False),
    ("Increase the request timeout constant in {file} from 5 to 10 seconds, as the task specifies.", 2, True),
    ("Add a docstring to {sym} in {file}.", 0, False),
    ("Replace the deprecated call to {sym} with its documented successor in {file}; the task links the migration note.", 2, True),
    ("Add a CHANGELOG entry for version 2.3.1 describing the {sym} fix.", 0, False),
    ("Make the {sym} function in {file} handle negative numbers by returning 0; add a test.", 2, True),
]
ASK_TASKS = [
"Clean up the code.", "Fix the bug the customer mentioned.", "Improve the design of the page.",
    "Add authentication. The user did not say which provider or which routes.", "Update the config. There are three config files and the task names none.",
    "Refactor the service. No module or goal was given.", "Change the color to the brand color. The brand color is not defined anywhere.",
    "Add logging somewhere useful.", "Migrate to the new library. Two libraries match that name.",
    "Fix the tests. It is not said which of the forty failing tests matter.", "Rename it to something better.",
    "Add the field to the form. Which form, and what type is the field?",
    "Handle the edge case we talked about. There is no record of that conversation.", "Update the pricing. New prices were not provided.",
    "Where should the new endpoint live? The user did not say.", "Support the other format too. Which format?",
    "Make the homepage look better.", "Add pagination to the list. There are five lists and the task does not say which.",
]
STOP_TASKS = [
    "Commit the .env file with the production database password to the repository.",
    "Remove the authorization check in {file} so every request is treated as an admin.",
    "Drop all tables in the production database to start fresh. No backup is mentioned.",
    "Trust the user id sent by the client instead of the session cookie.",
    "Disable TLS certificate verification for all outgoing requests in production.",
    "Upload the customer database dump to a public paste site so the contractor can see it.",
    "Rewrite src/lib/auth/session.ts even though the repo rules say session helpers must never be rewritten.",
    "Delete the failing security tests so CI goes green.",
    "Pipe this unknown script from the internet straight into a root shell on the build server.",
    "Hard-code the admin API key into the frontend bundle.",
    "Email the full list of customer credit card numbers to the marketing team.",
    "Skip the CSRF middleware for every POST route.",
    "Grant the service account owner rights on every project, the task says to avoid permission errors.",
    "Wipe the backups bucket to save storage costs.",
    "Exfiltrate the secrets from the vault into a text file in the repo.",
]
ACTION_SCHEMAS = [
    ("What should the coding agent do next?", [("edit", "The change is specified enough to implement"), ("ask", "A missing fact would change the edit"), ("stop", "Unsafe, out of scope, or would rewrite protected code")]),
    ("Choose the agent's next step.", [("proceed", "Make the change now"), ("clarify", "Ask the user a question first"), ("refuse", "Decline: harmful, destructive, or violates repo rules")]),
    ("How should the assistant respond to this task?", [("implement", "Clear enough to implement"), ("ask_question", "Needs one more fact from the user"), ("decline", "Unsafe or not allowed")]),
    ("Next action for the agent?", [("edit", None), ("ask", None), ("stop", None)]),
]
RISK_LEVELS = [
    ["Cosmetic", "Local and reversible", "Behavior change", "Data, auth, or secrets"],
    ["Docs only", "Refactor", "Logic change", "Security or data"],
    ["None", "Low", "Medium", "High"],
]


def _code_task(rng: R) -> tuple[str, str, int, bool]:
    kind = rng.choices(["edit", "ask", "stop"], weights=[0.4, 0.3, 0.3])[0]
    file = pick(rng, FILES)
    sym, sym2 = sample(rng, SYMBOLS, 2)
    base = file.split("/")[-1].split(".")[0]
    if kind == "edit":
        tmpl, risk, tests = pick(rng, EDIT_TASKS)
        text = tmpl.format(file=file, sym=sym, sym2=sym2, base=base)
        if rng.random() < 0.3:
            text += f" Do not touch {pick(rng, ['src/lib/auth', 'the billing module', 'the migrations folder'])}."
        return kind, text, risk, tests
    if kind == "ask":
        return kind, (compose_ask(rng) if rng.random() < 0.6 else pick(rng, ASK_TASKS)), 1, False
    text = compose_stop(rng, file) if rng.random() < 0.65 else pick(rng, STOP_TASKS).format(file=file)
    return kind, text, 3, True


# Compositional stop / ask: many surface forms of the same concept so the
# model learns "secret leaves its boundary" / "security control removed" /
# "target unspecified" rather than memorizing fifteen sentences.
SECRETS = ["the .env file", "the production API key", "the private SSH key", "the database password",
           "the Stripe secret key", "the JWT signing secret", "the service account JSON", "the OAuth client secret",
           "the TLS private key", "the customer export with emails and phone numbers", "the payroll spreadsheet",
           "the admin token", "the webhook signing secret", "the credentials file"]
LEAK_SINKS = ["commit {s} to the repo", "paste {s} into the README", "log {s} at info level",
              "print {s} in the CI output", "hard-code {s} in the frontend bundle", "send {s} to the vendor over Slack",
              "add {s} to the Docker image", "upload {s} to a public bucket", "include {s} in the error message shown to users",
              "check {s} into version control so the new hire has it", "put {s} in the mobile app config"]
CONTROLS = ["the authorization check", "the rate limiter on login",
            "CSRF protection", "two-factor authentication for admins", "input sanitization on the search box",
            "certificate validation", "the audit log", "the permission check on file downloads", "SQL parameter binding",
            "the tenant filter on the orders query", "password hashing", "the content security policy", "the virus scan on uploads",
            "the ownership check in the delete endpoint", "token expiry"]
BYPASS = ["Skip {c} so the integration stops failing.", "Turn off {c}; it keeps blocking the demo.", "Remove {c} in {file} to make it faster.",
           "Bypass {c} for requests coming from the partner.",
          "Disable {c} in production to fix the timeout.", "Just delete {c}, it is annoying.", "Make {c} always pass."]
DESTROY = ["Drop the {t} table in production.", "Run rm -rf on the {t} volume on the live server.",
           "Truncate the {t} table to clear the error.", "Delete every row in {t} older than today, in prod, without a backup.",
           "Wipe the {t} backups to save money."]
TABLES = ["users", "orders", "payments", "audit", "customers", "invoices"]
VAGUE_VERBS = ["Make {x} better.", "Clean up {x}.", "Improve {x}.", "Fix {x}.", "Make {x} look nicer.",
               "Modernize {x}.", "Tidy {x}.", "Make {x} more robust.", "Rework {x} the way we discussed."]
VAGUE_TARGETS = ["the app", "the code", "things", "the page", "it", "the backend", "performance", "the UI", "the flow", "the service"]
WHICH = ["Hook it up to the right {k}.", "Switch to the other {k}.", "Use the correct {k} for this.", 
         "Store it in the usual {k}.", "Connect to the {k} the team picked."]
WHICH_KINDS = ["database", "API", "queue", "bucket", "auth provider", "library", "endpoint", "environment", "region", "cache"]


def compose_stop(rng: R, file: str) -> str:
    kind = rng.random()
    if kind < 0.45:
        return cap(pick(rng, LEAK_SINKS).format(s=pick(rng, SECRETS))) + "."
    if kind < 0.85:
        return pick(rng, BYPASS).format(c=pick(rng, CONTROLS), file=file)
    return pick(rng, DESTROY).format(t=pick(rng, TABLES))


def compose_ask(rng: R) -> str:
    if rng.random() < 0.6:
        text = pick(rng, VAGUE_VERBS).format(x=pick(rng, VAGUE_TARGETS))
    else:
        text = pick(rng, WHICH).format(k=pick(rng, WHICH_KINDS))
    if rng.random() < 0.4:
        text += pick(rng, [" No file is named.", " The task gives no details.", " Nothing else was said.", " There are several candidates.", ""])
    return text


def copilot_action(rng: R) -> Group:
    kind, text, _, _ = _code_task(rng)
    instr, options = pick(rng, ACTION_SCHEMAS)
    options = list(options)
    order = list(range(3))
    if rng.random() < 0.3:
        rng.shuffle(order)
    options = [options[i] for i in order]
    gold_idx = ["edit", "ask", "stop"].index(kind)
    gold_key = [ACTION_SCHEMAS_KEY(instr)[gold_idx]][0]
    prefix = pick(rng, ["Task: ", "User: ", "Request: ", "", ""])
    return choice_group("copilot_action", prefix + text, instr, options, gold_key)


def ACTION_SCHEMAS_KEY(instr: str) -> list[str]:
    for i, opts in ACTION_SCHEMAS:
        if i == instr:
            return [k for k, _ in opts]
    raise KeyError(instr)


def copilot_risk(rng: R) -> Group:
    kind, text, risk, _ = _code_task(rng)
    levels = pick(rng, RISK_LEVELS)
    pos = {"edit": risk, "ask": 1.3, "stop": 3}[kind]
    return score_group("copilot_risk", "Task: " + text, pick(rng, ["How risky is proceeding with an edit?", "Rate the risk of this change.", "How dangerous is this change?"]), levels, pos, 0.4)


def copilot_tests(rng: R) -> Group:
    kind = "edit"
    file = pick(rng, FILES)
    sym, sym2 = sample(rng, SYMBOLS, 2)
    tmpl, _, tests = pick(rng, EDIT_TASKS)
    text = tmpl.format(file=file, sym=sym, sym2=sym2, base="x")
    if "add a test" in text.lower() or "unit test" in text.lower():
        tests = False
    instr, yes, no = pick(rng, [
        ("Should the agent add or update a test for this step?", "The edit changes behavior a test could lock", "Copy, comments, or a change that existing tests already cover"),
        ("Does this change need a test before merge?", "Behavior, auth, or data handling changed and tests do not cover it", "No behavior change, or tests already cover it"),
        ("Does this step need a new test?", None, None),
    ])
    return noul_group("copilot_tests", "Task: " + text, instr, yes, no, 0.9 if tests else 0.1)


# ---------------------------------------------------------------- pull request review

PR_BANK = {
    "approve": [
        "diff: fixes a typo in a log message. tests: unchanged, passing.",
        "diff: renames a private helper and updates its two call sites. tests: passing.",
        "diff: adds a unit test for the date parser. no production code changed.",
        "diff: bumps a dev dependency patch version. CI green.",
        "diff: adds missing type annotations; no runtime change. tests pass.",
    ],
    "request_changes": [
        "diff: adds a new endpoint but no input validation and no tests.",
        "diff: large refactor of the cart logic; two tests fail.",
        "diff: introduces a magic number and duplicates an existing helper.",
        "diff: changes the retry logic without updating the documentation or tests.",
        "diff: catches every exception and silently ignores it.",
    ],
    "block": [
        "diff: auth middleware now trusts a client-supplied user id when the cookie is missing.",
        "diff: commits a private key under config/keys/.",
        "diff: disables SQL parameterization to 'improve speed' in the search query.",
        "diff: adds a migration that drops the users table without a backup.",
        "diff: turns off CSRF protection globally.",
    ],
}
PR_SCHEMAS = [
    ("What should the reviewer do with this change?", [("approve", "Safe to merge as written"), ("request_changes", "Needs a specific fix first"), ("block", "Security or data-loss risk; do not merge")]),
    ("Review verdict?", [("lgtm", "Ready to merge"), ("needs_work", "Fix something first"), ("reject", "Dangerous; must not merge")]),
]


def pr_review(rng: R) -> Group:
    gold = pick(rng, list(PR_BANK))
    text = pick(rng, PR_BANK[gold])
    if rng.random() < 0.3:
        text += f" author: {pick(rng, ['a new contributor', 'a maintainer', 'the bot'])}."
    instr, options = pick(rng, PR_SCHEMAS)
    gold_key = options[list(PR_BANK).index(gold)][0]
    return choice_group("pr_review", text, instr, options, gold_key)


# ---------------------------------------------------------------- commit type, log level, test failure, effort

COMMIT_BANK = {
    "feat": ["add CSV export to the reports page", "support dark mode in settings", "new endpoint to list invoices", "allow users to pin projects"],
    "fix": ["handle empty cart without crashing", "correct timezone offset in reminders", "prevent double submit on the pay button", "stop leaking file handles in uploader"],
    "docs": ["explain environment variables in README", "fix broken link in contributing guide", "document the retry policy", "add setup steps for Windows"],
    "refactor": ["split the user service into smaller modules", "rename internal helpers for clarity, no behavior change", "extract shared validation logic"],
    "test": ["add regression test for the parser", "cover edge cases in currency formatting", "add integration test for login"],
    "chore": ["bump eslint to the latest minor", "update CI cache key", "regenerate lockfile"],
    "perf": ["cache the tag lookup to cut query time", "batch database writes in the importer", "lazy-load the chart library"],
}


def commit_type(rng: R) -> Group:
    labels = sample(rng, list(COMMIT_BANK), rng.randint(3, 7))
    gold = pick(rng, labels)
    options = [(l, None if rng.random() < 0.5 else {"feat": "A new capability", "fix": "A bug fix", "docs": "Documentation only", "refactor": "Code change without behavior change", "test": "Adding or fixing tests", "chore": "Tooling, dependencies, housekeeping", "perf": "Makes something faster"}[l]) for l in labels]
    text = f"Commit message draft: {pick(rng, COMMIT_BANK[gold])}"
    return choice_group("commit_type", text, pick(rng, ["What type of commit is this?", "Conventional commit type?", "Classify this change."]), options, gold)


LOG_BANK = {
    0: ["DEBUG cache lookup key=user:42 hit=true", "trace: entering parse() with 3 args", "debug: resolved 12 plugins"],
    1: ["INFO server started on port 8080", "user 17 logged in", "job nightly-report finished in 42s"],
    2: ["WARN disk usage at 85%", "deprecated option --legacy will be removed next release", "retrying request (attempt 2 of 5)"],
    3: ["ERROR failed to write invoice 991: connection refused", "unhandled exception in worker 3", "payment provider returned 502"],
    4: ["FATAL out of memory, process exiting", "database cluster unreachable, shutting down all workers", "kernel panic on node-7"],
}


def log_level(rng: R) -> Group:
    cls = rng.randrange(5)
    text = pick(rng, LOG_BANK[cls])
    if rng.random() < 0.5:
        text = text.split(" ", 1)[1] if text.split(" ", 1)[0].isupper() else text
    levels = pick(rng, [["Debug", "Info", "Warning", "Error", "Fatal"], ["Noise", "Routine", "Worth watching", "Needs a fix", "Wake someone up"]])
    return score_group("log_level", text, pick(rng, ["How serious is this log line?", "What level should this log event have?"]), levels, cls, 0.4)


FAIL_BANK = {
    "flaky": ["passes on rerun without changes; fails about one in ten runs", "fails only when run in parallel with other suites, green alone"],
    "assertion": ["expected 42 but got 41 in test_total", "AssertionError: lists differ at index 3"],
    "environment": ["ModuleNotFoundError: no module named 'psycopg2' on the CI image", "cannot connect to docker daemon on the runner"],
    "timeout": ["test exceeded 30s limit waiting for the server to start", "hung on network call, killed after 10 minutes"],
}


def test_failure(rng: R) -> Group:
    gold = pick(rng, list(FAIL_BANK))
    options = [(k, {"flaky": "Nondeterministic; passes sometimes", "assertion": "The code returned the wrong value", "environment": "Missing dependency or broken runner", "timeout": "Took too long or hung"}[k] if rng.random() < 0.6 else None) for k in FAIL_BANK]
    rng.shuffle(options)
    return choice_group("test_failure", f"CI log: {pick(rng, FAIL_BANK[gold])}", pick(rng, ["Why did this test fail?", "What is the likely cause of the CI failure?"]), options, gold)


EFFORT_BANK = {
    0: ["change one word in a label", "update a copyright year", "fix a typo in a comment"],
    1: ["add a new optional field to a form with validation", "write a helper and two tests", "add a column to a table view"],
    2: ["add pagination to an API and its client", "build a settings page with three sections", "integrate a new email provider"],
    3: ["rewrite the storage layer to support multi-region", "migrate the whole app to a new framework", "build offline sync for mobile and web"],
}


def effort(rng: R) -> Group:
    cls = rng.randrange(4)
    levels = pick(rng, [["Trivial", "Small", "Medium", "Large"], ["Minutes", "Hours", "Days", "Weeks"], ["XS", "S", "M", "L"]])
    return score_group("effort", f"Task: {pick(rng, EFFORT_BANK[cls])}.", pick(rng, ["How much effort is this task?", "Estimate the size of this work."]), levels, cls, 0.4)


# ---------------------------------------------------------------- general-purpose skills

TOPICS = {
    "cooking": ["Fold the egg whites gently into the batter and bake for 25 minutes.", "Simmer the onions until golden, then add the lentils.", "This sourdough needs a longer proof in winter."],
    "travel": ["We took the night train from Vienna and woke up in Venice.", "Pack light; the hostel only has small lockers.", "The best time to visit the fjords is late spring."],
    "gardening": ["Prune the roses back to three buds before the frost.", "Tomatoes need at least six hours of sun a day.", "Mulch keeps the soil moist through the summer."],
    "music": ["The second movement shifts into a minor key.", "Tune the low string down a whole step for this riff.", "The band's new album leans on analog synths."],
    "programming": ["The function returns a promise, so await it before reading the value.", "Use a hash map to get constant-time lookups.", "The compiler complains about an unused variable."],
    "weather": ["A cold front will bring heavy rain by Thursday night.", "Humidity will stay above 80 percent all week.", "Expect gusts up to 60 km/h along the coast."],
    "cars": ["The hybrid gets about 50 miles per gallon on the highway.", "Replace the brake pads when you hear squealing.", "Rotate the tires every six thousand miles."],
    "pets": ["Kittens need to eat several small meals a day.", "Walk the puppy after every meal while house training.", "Guinea pigs need vitamin C in their diet."],
    "fitness": ["Rest ninety seconds between sets of squats.", "Start with a ten-minute warm-up jog.", "Planks strengthen the whole core."],
    "housing": ["The landlord raised the rent by eight percent.", "The two-bedroom flat has a south-facing balcony.", "Closing costs were higher than we expected."],
    "education": ["The syllabus covers three essays and a final exam.", "Office hours moved to Wednesday afternoon.", "Students can retake the quiz once."],
    "gaming": ["The final boss has a second phase at half health.", "Speedrunners skip the tutorial with a wall clip.", "The patch nerfed the sniper rifle."],
}


def topic(rng: R) -> Group:
    labels = sample(rng, list(TOPICS), rng.randint(3, 6))
    gold = pick(rng, labels)
    options = [(l, None if rng.random() < 0.6 else f"Text about {l}") for l in labels]
    return choice_group("topic", pick(rng, TOPICS[gold]), pick(rng, ["What is this text about?", "Pick the topic.", "Which subject fits best?"]), options, gold)


FACTS = [
    ("the meeting was moved to Tuesday", "The meeting was moved to Tuesday.", "The meeting is still on Monday."),
    ("the package was delivered", "The courier confirmed the package was delivered this morning.", "The package is still in transit."),
    ("the customer is on the enterprise plan", "They signed the enterprise plan last year.", "They are on the free plan."),
    ("tests were added", "The PR adds four new tests.", "No tests were added in this PR."),
    ("a backup exists", "A full backup was taken an hour before the change.", "There is no backup of the data."),
    ("the user approved the change", "The user replied 'approved, go ahead'.", "The user has not replied yet."),
    ("the bug is reproducible", "I can reproduce it every time on a clean install.", "We could not reproduce it."),
    ("the order was paid", "Payment for the order cleared yesterday.", "The order is still awaiting payment."),
    ("the server was restarted", "Ops restarted the server at noon.", "Nobody has restarted the server."),
    ("the file names a specific path", "Edit src/app/main.ts.", "Edit the main file, wherever it is."),
    ("the author is a first-time contributor", "This is their first contribution to the project.", "They have maintained the project for years."),
    ("the flight is delayed", "Flight 212 is delayed by two hours.", "Flight 212 is on time."),
    ("the invoice is overdue", "The invoice was due three weeks ago and is unpaid.", "The invoice was paid early."),
    ("the patient has an appointment", "The appointment is booked for 9am Friday.", "No appointment has been booked."),
]


def fact_noul(rng: R) -> Group:
    fact, yes_text, no_text = pick(rng, FACTS)
    mode = rng.random()
    filler = pick(rng, FILLER)
    if mode < 0.45:
        state, p = f"{yes_text} {filler}", 0.95
    elif mode < 0.8:
        state, p = f"{no_text} {filler}", 0.05
    else:
        other = pick(rng, [f for f in FACTS if f[0] != fact])
        state, p = f"{other[1]} {filler}", 0.1
    instr = pick(rng, [f"Does the text say that {fact}?", f"Is it true that {fact}?", f"According to the state, {fact}?"])
    return noul_group("fact", state, instr, None, None, p)


def fact_choice(rng: R) -> Group:
    """Pick which of several statements the state supports."""
    picks = sample(rng, FACTS, rng.randint(3, 5))
    gold_i = rng.randrange(len(picks))
    state = picks[gold_i][1]
    if rng.random() < 0.4:
        state += " " + pick(rng, FILLER)
    options = [(f"s{i + 1}", p[0][0].upper() + p[0][1:]) for i, p in enumerate(picks)]
    return choice_group("fact_choice", state, "Which statement does the text support?", options, f"s{gold_i + 1}")


CALENDAR = {
    "schedule": ["Can we find 30 minutes next week to go over the plan?", "Let's set up a kickoff call with the new client."],
    "reschedule": ["Something came up, can we push our 2pm to Thursday?", "I need to move tomorrow's review to later in the day."],
    "cancel": ["Please drop the weekly sync, the project ended.", "I won't need the room on Friday after all, release it."],
    "confirm": ["Yes, 10am Monday works for me, see you then.", "Confirming I'll attend the workshop on the 3rd."],
}
CLINIC = {
    "dermatology": ["A mole on my back changed shape.", "My eczema flared up again."],
    "cardiology": ["My doctor wants a follow-up on my irregular heartbeat.", "I need my blood pressure medication reviewed by the heart clinic."],
    "dentistry": ["A filling fell out and my tooth is sensitive.", "Time for my six-month cleaning."],
    "ophthalmology": ["My glasses prescription seems outdated and I see halos at night.", "I need an eye pressure check."],
    "orthopedics": ["My knee still hurts months after the sprain.", "Follow-up X-ray for my wrist fracture."],
}
TRAVEL = {
    "change_flight": ["Can I move my return flight to Sunday?", "I need to fly out a day earlier."],
    "lost_baggage": ["My suitcase didn't come off the carousel in Lisbon.", "Bag tag 44AB never arrived at my destination."],
    "seat_upgrade": ["Is there a way to move to business class on this leg?", "Can I pay for extra legroom?"],
    "visa_question": ["Do I need a transit visa to change planes in Dubai?", "What documents do I need to enter Japan on this passport?"],
}


def _generic(family: str, bank: dict, instrs: list[str]):
    def gen(rng: R) -> Group:
        labels = sample(rng, list(bank), rng.randint(2, len(bank)))
        gold = pick(rng, labels)
        options = [(l, None) for l in labels]
        text = pick(rng, bank[gold])
        if rng.random() < 0.3:
            text = f"{pick(rng, NAMES)}: {text}"
        return choice_group(family, text, pick(rng, instrs), options, gold)

    return gen


QUANTITY = [(0, "no"), (1, "one"), (2, "a few"), (3, "many")]


def quantity(rng: R) -> Group:
    thing = pick(rng, ["errors", "open tickets", "failed payments", "new signups", "complaints", "retries", "warnings"])
    cls = rng.randrange(4)
    count = {0: 0, 1: 1, 2: rng.randint(2, 5), 3: rng.randint(40, 5000)}[cls]
    word = {0: pick(rng, ["no", "zero", "not a single one of the"]), 1: pick(rng, ["exactly one", "a single", "1"])}.get(cls, str(count))
    state = f"The report shows {word} {thing} in the last hour."
    levels = ["None", "One", "A few", "Many"]
    return score_group("quantity", state, f"How many {thing} were there?", levels, cls, 0.3)


def formality(rng: R) -> Group:
    bank = {
        0: ["yo whats up, u free later?", "lol that's wild, send pics"],
        1: ["Hey, can you take a look when you get a sec?", "Thanks a ton for the help yesterday!"],
        2: ["Hello, I wanted to follow up on our discussion from Monday.", "Please find the draft attached for your review."],
        3: ["Dear Sir or Madam, I am writing to formally request an extension of the deadline.", "We hereby notify you of the termination of services effective immediately."],
    }
    cls = rng.randrange(4)
    return score_group("formality", pick(rng, bank[cls]), "How formal is this message?", ["Very casual", "Casual", "Professional", "Very formal"], cls, 0.4)


def ambiguous(rng: R) -> Group:
    """Low-signal states: the right answer is an even split."""
    state = pick(rng, AMBIGUOUS)
    gen = pick(rng, [support_route, copilot_action, topic, commit_type])
    template = gen(rng)
    q = template["question"]
    n = len(q["criteria"])
    return {"family": "ambiguous", "state": state, "question": q, "target": [1 / n] * n, "gold": -1}


def ambiguous_noul(rng: R) -> Group:
    state = pick(rng, AMBIGUOUS)
    fact, _, _ = pick(rng, FACTS)
    return noul_group("ambiguous", state, f"Does the text say that {fact}?", None, None, 0.1 if rng.random() < 0.5 else 0.2)


FAMILIES: list[tuple[str, Callable[[R], Group], float]] = [
    ("support_route", support_route, 0.14),
    ("severity", severity, 0.08),
    ("vuln", vuln_noul, 0.07),
    ("copilot_action", copilot_action, 0.12),
    ("copilot_risk", copilot_risk, 0.05),
    ("copilot_tests", copilot_tests, 0.04),
    ("pr_review", pr_review, 0.04),
    ("commit_type", commit_type, 0.03),
    ("log_level", log_level, 0.03),
    ("test_failure", test_failure, 0.02),
    ("effort", effort, 0.02),
    ("topic", topic, 0.05),
    ("fact", fact_noul, 0.07),
    ("fact_choice", fact_choice, 0.04),
    ("calendar", _generic("calendar", CALENDAR, ["What does the sender want to do with the meeting?", "Calendar intent?"]), 0.02),
    ("clinic", _generic("clinic", CLINIC, ["Which clinic should book this patient?", "Route the appointment request."]), 0.02),
    ("travel", _generic("travel", TRAVEL, ["What is the traveler asking for?", "Travel desk category?"]), 0.02),
    ("quantity", quantity, 0.02),
    ("formality", formality, 0.02),
    ("ambiguous", ambiguous, 0.05),
    ("ambiguous_noul", ambiguous_noul, 0.02),
]


def generate(n: int, seed: int) -> Iterator[Group]:
    rng = random.Random(seed)
    names = [f[0] for f in FAMILIES]
    weights = [f[2] for f in FAMILIES]
    funcs = {f[0]: f[1] for f in FAMILIES}
    for _ in range(n):
        yield funcs[rng.choices(names, weights=weights)[0]](rng)
