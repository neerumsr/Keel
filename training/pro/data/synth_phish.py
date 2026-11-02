"""Synthetic 56 PhishNChips-style rows: should the user click the link in this email?

Framing copies the DI kit (adapters_added.phishnchips): state = {sender, from, subject, body, link_display_text,
link_url}; the nine questions of jev-phishing-bench/run_jev.py, copied literally below. Every email is generated here
from templates with fictional organizations; labels follow from how the email was built (phishing emails link to a
URL shortener, free hosting, IPFS or a lookalike domain; legitimate ones link to the organization's own site, with a
minority of hard cases each way). No DI or PhishNChips row is read.
"""
from rows import rng, row

SRC = "synthetic:keel-pro/synth_phish.py"

Q = {
    "verdict": {"type": "choice", "instructions": "This email arrived in the user's inbox and contains a link (`link_url`). Is it a phishing attempt, or a legitimate message whose link is safe to click?", "criteria": {"phishing": "The email or its link is a phishing attempt or otherwise malicious. The user should not click the link.", "legitimate": "A normal, legitimate message. The link is safe to click."}},
    "is_phishing": {"type": "noul", "instructions": "This email is a phishing attempt and the user should not click the link in `link_url`.", "criteria": {"true": "The email or its link is a phishing attempt or otherwise malicious.", "false": "The email is a normal, legitimate message and the link is safe to click."}},
    "sig_domain_mismatch": {"type": "noul", "instructions": "The domain of the sender address in `from` is different from the organization or domain that the link in `link_url` points to.", "criteria": {}},
    "sig_free_hosting": {"type": "noul", "instructions": "The link in `link_url` points to a URL shortener or to a free hosting or file-sharing platform (for example bit.ly, an IPFS gateway, Firebase, GitHub Pages, Google Docs) rather than to the organization's own website.", "criteria": {}},
    "sig_lure": {"type": "noul", "instructions": "The email asks the user to sign in, verify an account, or open a document or file through the link.", "criteria": {}},
    "sig_urgency": {"type": "noul", "instructions": "The email pressures the user to act quickly, mentions a deadline, or threatens a consequence.", "criteria": {}},
    "sig_generic_sender": {"type": "noul", "instructions": "The sender uses a generic webmail address (such as gmail, outlook, yahoo, hotmail) in `from` while presenting themselves as a company, team, department or organization.", "criteria": {}},
    "verdict_alt_click": {"type": "choice", "instructions": "Should the user click the link in this email?", "criteria": {"do_not_click": "No. The link may be phishing or malicious.", "click": "Yes. The email and its link look legitimate."}},
    "verdict_alt_minimal": {"type": "choice", "instructions": "Classify this email.", "criteria": {"phishing": None, "legitimate": None}},
}

ORG_A = ["Northwind", "Bluepeak", "Corvana", "Lumetra", "Quillfield", "Harbor & Lane", "Vantor", "Meridel", "Oakshore", "Pellucid", "Tamberly", "Crestmoor", "Fenwick", "Solvane", "Arbolux", "Kestrel", "Marlowe", "Ondria", "Brightwell", "Zephyrine", "Calderon", "Ravensgate", "Thistle", "Ambergrove", "Copperline", "Halvard", "Ivoryne", "Juniper", "Lindqvist", "Mosswood"]
ORG_B = ["Bank", "Credit Union", "Logistics", "Health", "Insurance", "Cloud", "Telecom", "Energy", "University", "Payroll", "Realty", "Airlines", "Software", "Pharmacy", "Retail", "Legal", "Analytics", "Media", "Travel", "Labs"]
TLD = ["com", "com", "com", "io", "net", "co", "org", "app"]
FIRST = ["Daniel", "Priya", "Marcus", "Elena", "Tom", "Aisha", "Kenji", "Sofia", "Liam", "Nadia", "Omar", "Grace", "Hugo", "Mei", "Lucas", "Fatima", "Noah", "Ines", "Ravi", "Clara", "Jonas", "Leah", "Mateo", "Yara"]
LAST = ["Thorne", "Patel", "Okafor", "Novak", "Lindgren", "Haddad", "Tanaka", "Moreau", "Brennan", "Costa", "Fischer", "Kowalski", "Ibrahim", "Silva", "Nguyen", "Reyes", "Andersen", "Romano"]
WEBMAIL = ["gmail.com", "outlook.com", "yahoo.com", "hotmail.com", "aol.com", "proton.me", "icloud.com", "gmx.com", "mail.com", "yandex.com"]
SHORT = ["bit.ly", "tinyurl.com", "cutt.ly", "is.gd", "rebrand.ly", "t.ly", "shorturl.at", "rb.gy", "ow.ly", "s.id"]
FREE = ["{s}.firebaseapp.com", "{s}.web.app", "{s}.github.io", "{s}.netlify.app", "{s}.vercel.app", "{s}.pages.dev", "{s}.glitch.me", "{s}.weebly.com", "{s}.wixsite.com/{s}", "{s}.000webhostapp.com", "sites.google.com/view/{s}", "docs.google.com/forms/d/e/{h}/viewform", "docs.google.com/document/d/{h}/edit", "storage.googleapis.com/{s}/index.html", "{s}.blogspot.com", "{s}.r2.dev", "pub-{h}.r2.dev", "{s}.herokuapp.com", "forms.office.com/r/{h}", "{s}.square.site", "{s}.webflow.io", "dropbox.com/s/{h}/{s}.pdf", "1drv.ms/b/s!{h}", "{s}.myshopify.com", "{s}.surge.sh"]
IPFS = ["ipfs.io/ipfs/{H}", "cloudflare-ipfs.com/ipfs/{H}", "{H}.ipfs.dweb.link", "gateway.pinata.cloud/ipfs/{H}", "{H}.ipfs.w3s.link", "nftstorage.link/ipfs/{H}"]
PATH_LEGIT = ["account", "orders/{n}", "invoices/{n}", "events/{w}", "blog/{w}-{w2}", "support/tickets/{n}", "news/{w}", "careers", "docs/{w}", "shipping/track/{n}", "webinar/{w}", "settings/notifications", "community/{w}", "release-notes", "status"]
WORDS = ["spring", "update", "roadmap", "summit", "q3", "benefits", "renewal", "security", "launch", "pricing", "welcome", "survey", "migration", "holiday", "report", "review", "training", "onboarding", "results", "agenda"]

LEGIT = [
    ("Your {org} order {n} has shipped", "Hi {fn},\n\nGood news: your order {n} is on its way and should arrive within {d} business days.\n\nYou can follow the delivery here: {disp}\n\nThanks for shopping with {org}.\n\nThe {org} team", False, False),
    ("Agenda for Thursday's {w} sync", "Hi {fn},\n\nI put together the agenda for Thursday's {w} sync. It is on the team page: {disp}\n\nAdd anything I missed before the meeting.\n\nThanks,\n{sfn}", False, False),
    ("{org} newsletter: {W} edition", "Hello {fn},\n\nThis month at {org}: our {w} program, three customer stories and a look at what is coming next quarter.\n\nRead the full newsletter: {disp}\n\nYou are receiving this because you subscribed. Manage preferences in your account settings.", False, False),
    ("Invitation: {org} {W} webinar", "Hi {fn},\n\nJoin us for a 45-minute session on {w} next {day}. Registration is free and the recording will be shared afterwards.\n\nDetails and registration: {disp}\n\nBest regards,\n{sfn} {sln}\n{org} Events", False, False),
    ("Your {org} statement is available", "Dear {fn},\n\nYour monthly statement is now available in online banking. For your security we never include account details in email.\n\nYou can view it after signing in at our website: {disp}\n\n{org} Customer Service", False, False),
    ("Re: {w} draft", "Hi {fn},\n\nFollowing up on our chat yesterday, here is the reference I mentioned for the {w} draft: {disp}\n\nLet me know if you need anything else.\n\nBest,\n{sfn}", False, False),
    ("Reminder: benefits enrollment closes {day}", "Hi {fn},\n\nA reminder that open enrollment for {yr} benefits closes on {day}. If you do nothing, your current elections carry over.\n\nReview your options on the HR portal: {disp}\n\nPeople Team, {org}", True, False),
    ("Release notes: {org} {v}", "Hello,\n\nVersion {v} of {org} is rolling out this week. Highlights include faster sync and a redesigned settings page.\n\nFull release notes: {disp}\n\n— {org} Product", False, False),
    ("Your support ticket #{n} was updated", "Hi {fn},\n\nOur support team replied to your ticket #{n}. You can read the reply and respond here: {disp}\n\nIf the issue is resolved, no action is needed; the ticket will close in 7 days.\n\n{org} Support", False, False),
    ("Thanks for registering for {W} Summit", "Hi {fn},\n\nYou're registered for {W} Summit. Add the sessions you want to attend to your schedule: {disp}\n\nSee you there,\n{org} Events Team", False, False),
]

PHISH = [
    ("Action required: verify your {org} account", "Dear customer,\n\nWe detected unusual sign-in activity on your {org} account. To avoid suspension, verify your identity within 24 hours.\n\n{disp}\n\nFailure to verify will result in permanent account restriction.\n\n{org} Security Team", True, True),
    ("Document shared with you: {W}_{yr}.pdf", "Hello,\n\n{sfn} {sln} has shared a secure document with you via {org} Docs.\n\nOpen document: {disp}\n\nYou may be asked to sign in with your email account to view it.", True, False),
    ("Your mailbox is almost full", "Dear user,\n\nYour mailbox has reached 98% of its storage limit. Incoming messages will be rejected after today.\n\nClick below to upgrade your quota for free:\n{disp}\n\nIT Help Desk", True, True),
    ("Invoice #{n} overdue - immediate payment needed", "Hi,\n\nPlease find attached invoice #{n}, which is now 14 days overdue. To avoid late fees and service interruption, review and pay today.\n\nView invoice: {disp}\n\nAccounts Receivable\n{org}", True, True),
    ("Payroll update: confirm your direct deposit", "Hi {fn},\n\nWe are migrating to a new payroll system. Sign in and confirm your direct deposit details before {day} so your next salary payment is not delayed.\n\n{disp}\n\nPayroll Department", True, True),
    ("Your package could not be delivered", "Dear customer,\n\nWe attempted to deliver your package but no one was available. A redelivery fee of $1.99 is required.\n\nSchedule redelivery: {disp}\n\n{org} Delivery Services", True, True),
    ("New voicemail message (0:{s2})", "You have received a new voicemail from +1 ({a3}) {a3b}-{a4}.\n\nListen to the message: {disp}\n\nThis message will be deleted in 48 hours.", True, True),
    ("Password expires today", "Your {org} password expires today. Keep your current password by confirming it below:\n\n{disp}\n\nIf you ignore this message you will be logged out of all devices.\n\n{org} IT", True, True),
    ("Re: {w} proposal", "Hi {fn},\n\nAs discussed, I uploaded the revised {w} proposal. Please review it and sign in to leave your comments:\n\n{disp}\n\nThanks,\n{sfn} {sln}", True, False),
    ("{org}: unusual payment detected", "Dear {fn},\n\nA payment of ${amt} to an unknown merchant was flagged on your account. If this was not you, cancel it immediately:\n\n{disp}\n\n{org} Fraud Prevention", True, True),
]


def slug(r, org):
    base = org.lower().replace(" & ", "-").replace(" ", "")
    return r.choice([base, base + "-" + r.choice(["secure", "login", "verify", "support", "portal", "docs", "account"]), r.choice(["secure", "login", "auth", "doc", "share", "files"]) + "-" + base + str(r.randint(1, 999))])


def hexs(r, n):
    return "".join(r.choice("0123456789abcdef") for _ in range(n))


def gen(r, i):
    org1, org2 = r.choice(ORG_A), r.choice(ORG_B)
    org = f"{org1} {org2}"
    dom = org1.lower().replace(" & ", "").replace(" ", "") + r.choice(["", org2.lower().replace(" ", "")[:4], ""]) + "." + r.choice(TLD)
    fn, sfn, sln = r.choice(FIRST), r.choice(FIRST), r.choice(LAST)
    phish = r.random() < 0.5
    fill = dict(org=org, fn=fn, sfn=sfn, sln=sln, n=r.randint(10000, 9999999), d=r.randint(2, 6), w=r.choice(WORDS), w2=r.choice(WORDS), day=r.choice(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]), yr=r.choice([2025, 2026, 2027]), v=f"{r.randint(1, 9)}.{r.randint(0, 20)}", s2=r.randint(10, 59), a3=r.randint(200, 989), a3b=r.randint(200, 989), a4=r.randint(1000, 9999), amt=f"{r.randint(49, 2499)}.{r.randint(0, 99):02d}")
    fill["W"] = fill["w"].capitalize()
    generic = False
    if not phish:
        subj, body, urgency, lure = r.choice(LEGIT)
        kind = r.random()
        if kind < 0.12:
            # colleague shares a document on a public platform from their own corporate address
            host = r.choice(["docs.google.com/document/d/{h}/edit", "dropbox.com/s/{h}/{w}.pdf", "1drv.ms/w/s!{h}", "github.com/{s}/{w}"]).format(h=hexs(r, 24), s=dom.split(".")[0], w=fill["w"])
            url, free, mismatch = "https://" + host, True, True
        elif kind < 0.2:
            # organization's own CDN / marketing domain
            url, free, mismatch = f"https://{dom.split('.')[0]}{r.choice(['cdn', '-mail', 'events', 'news'])}.{r.choice(TLD)}/{r.choice(PATH_LEGIT).format(n=fill['n'], w=fill['w'], w2=fill['w2'])}", False, True
        else:
            sub = r.choice(["", "www.", "app.", "my.", "support.", "events.", "news."])
            url, free, mismatch = f"https://{sub}{dom}/{r.choice(PATH_LEGIT).format(n=fill['n'], w=fill['w'], w2=fill['w2'])}", False, False
        frm = r.choice([f"{sfn.lower()}.{sln.lower()}@{dom}", f"noreply@{dom}", f"hello@{r.choice(['', 'mail.', 'news.'])}{dom}", f"{r.choice(['support', 'events', 'team', 'billing', 'hr'])}@{dom}"])
        sender = r.choice([f"{sfn} {sln}", f"{org}", f"{org} {r.choice(['Support', 'Events', 'Team', 'Billing'])}"])
        if r.random() < 0.06:
            # small business or individual legitimately using webmail, not posing as an organization
            frm, sender = f"{sfn.lower()}.{sln.lower()}{r.randint(1, 99)}@{r.choice(WEBMAIL)}", f"{sfn} {sln}"
            mismatch = True
    else:
        subj, body, urgency, lure = r.choice(PHISH)
        kind = r.random()
        s = slug(r, org1)
        if kind < 0.35:
            url, free = "https://" + r.choice(FREE).format(s=s, h=hexs(r, r.choice([12, 24, 32]))) + r.choice(["", "/login", "/verify", "/index.html", "/secure/auth", "/doc"]), True
        elif kind < 0.55:
            url, free = "https://" + r.choice(IPFS).format(H="bafy" + hexs(r, 52)) + r.choice(["", "?filename=index.html", "#" + fn.lower() + "@" + dom]), True
        elif kind < 0.75:
            url, free = "https://" + r.choice(SHORT) + "/" + "".join(r.choice("abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(r.randint(5, 8))), True
        else:
            # lookalike domain, not free hosting
            look = dom.split(".")[0]
            look = r.choice([look + "-" + r.choice(["secure", "verify", "login", "account"]), look.replace("o", "0", 1) if "o" in look else look + "s", look + r.choice(["support", "help", "online"]), "account-" + look])
            url, free = f"https://{look}.{r.choice(['com', 'net', 'co', 'info', 'online', 'xyz', 'top', 'site'])}/{r.choice(['login', 'verify', 'secure/session', 'auth', 'confirm'])}", False
        fkind = r.random()
        if fkind < 0.35:
            frm, generic = f"{r.choice([org1.lower().replace(' ', ''), 'support', 'security', 'admin', 'helpdesk', 'noreply'])}{r.choice(['', '.team', '-service', str(r.randint(1, 999))])}@{r.choice(WEBMAIL)}", True
        elif fkind < 0.7:
            frm = f"{r.choice(['no-reply', 'security', 'alerts', 'service', 'billing'])}@{r.choice([dom.split('.')[0] + '-' + r.choice(['alerts', 'mail', 'notice']), 'mail-' + dom.split('.')[0], hexs(r, 6)])}.{r.choice(['com', 'net', 'info', 'online', 'xyz'])}"
        else:
            # compromised or spoofed legitimate-looking sender at a real-looking domain
            frm = f"{sfn.lower()}.{sln.lower()}@{r.choice([dom, r.choice(ORG_A).lower().replace(' & ', '').replace(' ', '') + '.' + r.choice(TLD)])}"
        sender = r.choice([f"{org} {r.choice(['Security', 'Support', 'Billing', 'IT', 'Team', 'Notifications'])}", f"{sfn} {sln}", f"{org}", "IT Help Desk", "Payroll Department"])
        mismatch = True
    disp_text = r.choice([url, url, "Click here", "View document", "Open", "Sign in", "Review now", "Track package", "Read more", url.split("//")[1].split("/")[0]]) if phish else r.choice([url, url, "View details", "Read more", url.split("//")[1].split("/")[0]])
    fill["disp"] = url if disp_text == url else disp_text + (" (" + url + ")" if r.random() < 0.3 else "")
    state = {"sender": sender, "from": frm, "subject": subj.format(**fill), "body": body.format(**fill), "link_display_text": disp_text, "link_url": url}
    gen_generic = generic or (frm.split("@")[1] in WEBMAIL and sender != f"{sfn} {sln}")
    labels = {"verdict": "phishing" if phish else "legitimate", "is_phishing": phish, "verdict_alt_click": "do_not_click" if phish else "click", "verdict_alt_minimal": "phishing" if phish else "legitimate", "sig_domain_mismatch": mismatch, "sig_free_hosting": free, "sig_lure": lure or ("sign in" in body.lower() or "verify" in body.lower()), "sig_urgency": urgency, "sig_generic_sender": gen_generic}
    return state, labels


def phish(cap):
    out, seen, i = [], set(), 0
    while len(out) < cap and i < cap * 5:
        i += 1
        r = rng("phish", i)
        state, labels = gen(r, i)
        k = state["body"] + state["link_url"]
        if k in seen:
            continue
        seen.add(k)
        # verdict always; plus two other questions (the kit asks all nine in one request, one prompt each)
        qs = ["verdict"] + r.sample([q for q in Q if q != "verdict"], 2)
        for q in qs:
            out.append(row(56, SRC, state, dict(Q[q]), labels[q]))
    return out[:cap]
