"""Hand-written seed bank d_* (data-2). Emits training/data/v3/seeds/d_*.jsonl.

Targets the generalization classes from the Keel-2 failure analysis (security-flavoured
routing with access/login vocabulary, subtle sentiment, track-vs-return, scoped edits vs
unsafe gates, cold leads, PII/phishing/deadline yes-no). Written fresh; the builder's
6-gram filter still checks every state against held-out/open suites.
"""
from __future__ import annotations

import json
import pathlib

OUT = pathlib.Path(__file__).resolve().parents[1] / "data" / "v3" / "seeds"

SUPPORT = {
    "security": [
        "If I change the number at the end of the invoice URL I can download invoices for a company I've never heard of.",
        "The password reset email I got last month still logs me in today, and it worked on my colleague's account when I pasted it.",
        "After I log out, pressing back in the browser shows my dashboard again and I can still click around.",
        "Your API returns other customers' order details if you swap the account id in the request.",
        "I can access the admin settings page just by typing /admin even though I'm a basic user.",
        "Our API key shows up in plain text in the URL of every request, so it ends up in proxy logs.",
        "Someone logged into my account from another country and the session is still active even after I changed my password.",
        "The invite link for my workspace lets anyone who has it join as an owner, not just a member.",
        "When I sign in with SSO I land in a different tenant's workspace with their files visible.",
        "Login works with any password as long as the email is right. Tried it twice to be sure.",
        "The one-time code from the login SMS can be reused as many times as I want.",
        "Your website accepts requests from any origin, our pentester flagged the wildcard CORS header on the account endpoint.",
        "I noticed the session cookie isn't marked secure or httponly and it's readable from the console.",
        "Exported CSV includes password hashes for every user in the org.",
        "My access token from a revoked integration still works against the API a week later.",
        "Uploading an SVG avatar runs the script inside it when someone views my profile.",
        "A former employee can still log in because deactivating them didn't kill their existing sessions.",
        "Clicking 'forgot password' tells you whether an email is registered, and there's no rate limit on it.",
    ],
    "account_access": [
        "I forgot my password and the reset email never arrives, checked spam too.",
        "Got a new phone and lost my authenticator app, now I can't get past two-factor.",
        "My account is locked after too many wrong attempts, how long until I can try again?",
        "I changed my email address and now I can't log in with either the old or the new one.",
        "The login page just spins after I enter my credentials.",
        "How do I add a backup email so I don't get locked out again?",
        "My username was changed by our admin and I don't know what it is now.",
        "SSO login says my account isn't provisioned yet, I started this week.",
        "I keep getting logged out every few minutes on the mobile app.",
        "Can you unlock my account? I mistyped my password a few times this morning.",
    ],
    "data_privacy": [
        "Please delete all the personal data you hold about me under GDPR.",
        "I'd like a copy of every piece of data you've collected about me.",
        "Who do you share my email address with? I started getting spam right after signing up.",
        "Stop using my purchase history for ad targeting, I opted out last month.",
        "How long do you keep call recordings, and can I have mine removed?",
    ],
    "billing": [
        "I was charged for the annual plan even though I picked monthly.",
        "The invoice shows the wrong company name and VAT number.",
        "Why did my bill go up this month? Nothing changed on our side.",
        "Card declined on renewal but the bank says there's no problem.",
    ],
    "integrations": [
        "The Slack integration stopped posting notifications after we renamed the channel.",
        "Zapier says our webhook is returning 401 since yesterday.",
        "Calendar sync with Outlook duplicates every event.",
        "The Salesforce connector maps the company field into the contact name.",
    ],
    "bug": [
        "The export button does nothing in Firefox, works in Chrome.",
        "Dates show as one day earlier in the report than in the editor.",
        "Uploading a file over 10 MB gives a blank error dialog.",
        "Sorting the table by price puts 100 before 20.",
    ],
}

SENTIMENT = {
    "positive": [
        "Not bad at all for the price, I'd buy it again.", "Can't complain, it does exactly what it says.", "I wasn't expecting much, but wow.",
        "Didn't think a budget kettle could feel this solid.", "Zero issues in six months, which is more than I can say for the last one.",
        "Honestly no notes. Ten out of ten.", "Hard to find anything wrong with it.", "Never had a smoother check-in.", "Exceeded what I paid for, easily.",
        "The staff couldn't have been nicer.", "My only regret is not buying it sooner.", "I'll admit it, the update actually made things faster.",
    ],
    "negative": [
        "Oh perfect, the app logged me out mid-payment. Love that for me.", "Fantastic, a second 'final' notice for a bill I already paid.",
        "Wow, three hours on hold. Truly world-class service.", "I wasn't impressed, the room smelled of smoke.", "Not exactly what I'd call helpful.",
        "It does the job, I suppose, if the job is wasting my weekend.", "Returned it. Enough said.", "Expected better from a brand this expensive.",
        "I've stopped recommending them to friends.", "The food was cold and the waiter acted like we were a nuisance.",
        "Sure, take another week, it's not like I needed my order.", "Great, the 'upgrade' removed the one feature I used.",
        "Package arrived. Box was empty.", "I won't be renewing.", "Lovely design, shame it stopped charging after a month.",
    ],
    "neutral": [
        "The package arrived on Tuesday.", "I ordered the blue one in medium.", "The store opens at nine on weekdays.", "Is the charger included in the box?",
        "We switched to the annual plan last spring.", "The manual is available in four languages.", "My flight lands at 6pm.",
        "The update installed overnight.", "The meeting has been moved to the second floor.", "It comes in black and silver.",
    ],
    "mixed": [
        "Great screen, terrible battery.", "The hotel was beautiful but the staff were rude.", "Tastes amazing, costs way too much.",
        "Setup was a pain, but now it works perfectly.", "Love the features, hate the subscription.", "Fast delivery, but the box was crushed.",
    ],
}

ECOM = {
    "track_order": [
        "Where is my parcel? The tracking page hasn't updated since Monday.", "Has order 55812 shipped yet?", "The courier says delivered but nothing's at my door.",
        "Can you tell me when my sofa will arrive?", "Tracking number doesn't work on the carrier's site.", "It's been ten days, is my package lost?",
    ],
    "return_item": [
        "The jacket is too small, how do I send it back?", "I'd like to return the headphones, the left side crackles.", "Can I return something bought on sale?",
        "Need a return label for the lamp that arrived broken.", "Shoes don't fit, want to send them back for my money.", "Wrong colour arrived, I'm sending it back.",
    ],
    "cancel_order": ["Please cancel the order I placed an hour ago.", "I ordered twice by mistake, cancel the second one.", "Stop my order before it ships please."],
    "refund_status": ["I returned the blender two weeks ago, where's my refund?", "Your warehouse got my return on the 3rd, still no money back."],
    "change_address": ["I moved, can you send my order to my new flat instead?", "Typo in my street name on the order, can you fix it before it ships?"],
}

AGENT = {
    "refuse": [
        "Set Access-Control-Allow-Origin to * on the auth API so the partner demo works, we'll fix it later.",
        "Comment out the webhook signature check in prod, it keeps rejecting Stripe events.",
        "Turn off TLS certificate verification in the payment client, the cert is expired.",
        "Reuse the admin's refresh token for the batch job so it doesn't need its own login.",
        "Hardcode the production database password in config.py, env vars are annoying.",
        "Disable the CSRF middleware globally, the form keeps failing.",
        "Make the S3 bucket with customer uploads public so the CDN can read it.",
        "Skip JWT expiry validation, users are complaining about being logged out.",
        "Delete the audit log table, it's taking up too much space.",
        "Run the migration that drops the users.email column directly on production right now.",
        "Grant the CI service account owner role on the whole subscription, permissions errors are slowing us down.",
        "Log full credit card numbers in the payments service so we can debug the declines.",
    ],
    "proceed": [
        "Clamp the volume slider value to 0-100 in Slider.tsx.", "Add an aria-label to the close button in Modal.tsx.", "Rename the CSS class .btn-primay to .btn-primary everywhere.",
        "Fix the typo 'recieve' in the onboarding email template.", "Add a null check before calling user.profile.name in Header.tsx.",
        "Bump the lodash version in package.json to the latest patch release.", "Add a unit test for the parseDate helper covering leap years.",
        "Increase the request timeout in api/client.ts from 5s to 10s.", "Sort the dropdown options alphabetically in CountryPicker.tsx.",
        "Replace the deprecated componentWillMount in Legacy.jsx with componentDidMount.", "Add a loading spinner to the submit button while the form posts.",
        "Extract the duplicated currency formatting into a formatCurrency helper in utils/format.ts.",
    ],
    "clarify": [
        "Make the app faster.", "Clean up the backend.", "Fix the login stuff.", "Update the styles to look more modern.", "Refactor the data layer.",
        "Handle the edge cases.", "Make it work like the old version.", "Improve security.",
    ],
}

LEAD = {
    "cold": ["Just browsing for now, no budget this year.", "Saw your ad, curious, not looking to buy anything.", "Student here doing research for a class project.",
             "We just signed a three-year deal with a competitor.", "Please remove me from your mailing list."],
    "warm": ["We're evaluating a few tools for next quarter, can you send pricing?", "Interested, but I need to check with my manager first.",
             "Could we get a demo sometime next month?", "Our contract with the current vendor ends in the autumn."],
    "hot": ["We have budget approved and need this live in two weeks, can we sign today?", "Send the contract, our CFO approved 200 seats.",
            "Our current vendor is shutting down Friday, we need to switch immediately."],
}

NOUL = {
    "has_pii": [("Call me back at 212-555-0173 after 5.", "yes"), ("My date of birth is 4 March 1987, if you need it for verification.", "yes"),
                ("Ship it to 18 Harbor Lane, Fairview, it's my home address.", "yes"), ("SSN ends 6620, full number on the form: 078-05-1120.", "yes"),
                ("My personal email is lena.k.travels@gmail.com.", "yes"), ("Order 7781-2290 still hasn't shipped.", "no"),
                ("Contact our support desk at support@contoso.com.", "no"), ("The office is at the corner of the main square.", "no"),
                ("Ticket INC-40213 is about the printer.", "no"), ("I'd rather not give my phone number.", "no")],
    "is_phishing": [("Your mailbox is 98% full. Verify your password within 24h at mail-upgrade-portal.co or lose access.", "yes"),
                    ("HR: please confirm your bank details for payroll via the attached HTML form today.", "yes"),
                    ("We noticed unusual activity. Log in at paypa1-secure.help to keep your account open.", "yes"),
                    ("CEO here, I need you to buy gift cards for a client, keep it quiet and send me the codes.", "yes"),
                    ("Your monthly statement is ready. Log in through our app as usual to view it.", "no"),
                    ("Reminder: the all-hands is moved to 3pm, same room.", "no"),
                    ("Your order has shipped. Track it from your account page.", "no")],
    "has_deadline": [("Please send the signed contract by Thursday noon.", "yes"), ("Applications close on the 30th.", "yes"),
                     ("Need your feedback before Friday's board meeting.", "yes"), ("Whenever you have a minute, no rush.", "no"),
                     ("Thanks for the update, looks good.", "no"), ("We met last Thursday to discuss it.", "no")],
    "has_threat": [("If you post that again I'll find you after school and break your nose.", "yes"), ("I'm going to annihilate you in chess tonight.", "no"),
                   ("My manager will kill me if I miss this deadline.", "no"), ("You'd better sleep with one eye open, I know your address.", "yes")],
}


ML = {  # (task, label, text)
    "es": [("sentiment", "positive", "No está nada mal, la verdad. Volvería a comprarlo."), ("sentiment", "positive", "El servicio fue impecable y muy rápido."),
           ("sentiment", "negative", "Genial, otra vez se ha caído la app justo al pagar."), ("sentiment", "negative", "No quedé nada contento con la habitación."),
           ("sentiment", "negative", "El pedido llegó roto y nadie contesta."), ("sentiment", "neutral", "El paquete llegó el martes por la tarde."),
           ("sentiment", "mixed", "La comida estaba rica, pero el servicio fue lentísimo."), ("ecom_intent", "track_order", "¿Dónde está mi pedido? El seguimiento no se actualiza."),
           ("ecom_intent", "return_item", "Quiero devolver las zapatillas, me quedan pequeñas."), ("ecom_intent", "cancel_order", "Por favor, cancelad el pedido que hice esta mañana."),
           ("ecom_intent", "refund_status", "Devolví la chaqueta hace dos semanas y aún no veo el reembolso."), ("has_pii", "yes", "Mi número es 612 345 678, llámame por la tarde."),
           ("has_pii", "no", "El número de pedido es 448812, gracias."), ("support_route", "security", "Si cambio el número en la URL de la factura veo facturas de otras empresas."),
           ("support_route", "account_access", "Olvidé mi contraseña y el correo de recuperación no llega.")],
    "fr": [("sentiment", "positive", "Pas mal du tout, je suis agréablement surpris."), ("sentiment", "positive", "Livraison rapide et produit parfait."),
           ("sentiment", "negative", "Super, encore une mise à jour qui efface mes réglages."), ("sentiment", "negative", "Je n'ai pas du tout apprécié l'accueil."),
           ("sentiment", "negative", "Trois semaines d'attente pour un colis vide."), ("sentiment", "neutral", "La boutique ouvre à neuf heures en semaine."),
           ("sentiment", "mixed", "Bel écran, mais la batterie ne tient pas la journée."), ("ecom_intent", "track_order", "Mon colis n'a pas bougé depuis lundi, où est-il ?"),
           ("ecom_intent", "return_item", "Je voudrais renvoyer la robe, la taille ne va pas."), ("ecom_intent", "change_address", "J'ai déménagé, pouvez-vous livrer à ma nouvelle adresse ?"),
           ("ecom_intent", "cancel_order", "Merci d'annuler ma commande avant l'expédition."), ("has_pii", "yes", "Vous pouvez me joindre au 06 12 34 56 78."),
           ("has_pii", "no", "Le ticket 5521 concerne l'imprimante."), ("support_route", "security", "Le lien de réinitialisation fonctionne aussi pour le compte d'un collègue."),
           ("support_route", "billing", "J'ai été facturé deux fois ce mois-ci.")],
    "de": [("sentiment", "positive", "Gar nicht schlecht, ehrlich gesagt."), ("sentiment", "positive", "Top Qualität und super freundlicher Service."),
           ("sentiment", "negative", "Na toll, schon wieder abgestürzt, mitten in der Zahlung."), ("sentiment", "negative", "Ich war mit dem Zimmer überhaupt nicht zufrieden."),
           ("sentiment", "negative", "Die Lieferung kam zwei Wochen zu spät und beschädigt."), ("sentiment", "neutral", "Das Paket wurde am Dienstag zugestellt."),
           ("sentiment", "mixed", "Toller Klang, aber der Akku ist ein Witz."), ("ecom_intent", "track_order", "Wo bleibt meine Bestellung? Die Sendungsverfolgung zeigt nichts."),
           ("ecom_intent", "return_item", "Ich möchte die Jacke zurückschicken, sie ist zu klein."), ("ecom_intent", "refund_status", "Rücksendung ist seit zehn Tagen da, wo bleibt mein Geld?"),
           ("ecom_intent", "cancel_order", "Bitte stornieren Sie meine Bestellung von heute früh."), ("has_pii", "yes", "Meine Handynummer ist 0151 2345 6789."),
           ("has_pii", "no", "Die Auftragsnummer lautet 77812."), ("support_route", "security", "Nach dem Abmelden kann ich über den Zurück-Button weiter im Konto klicken."),
           ("support_route", "bug", "Der Export-Button reagiert in Firefox nicht.")],
    "pt": [("sentiment", "positive", "Nada mal, gostei bastante."), ("sentiment", "positive", "Atendimento excelente, resolveram em minutos."),
           ("sentiment", "negative", "Ótimo, mais uma atualização que apagou minhas configurações."), ("sentiment", "negative", "Não fiquei nada satisfeito com o produto."),
           ("sentiment", "negative", "Chegou quebrado e ninguém responde."), ("sentiment", "neutral", "A loja abre às nove nos dias úteis."),
           ("sentiment", "mixed", "A tela é linda, mas a bateria é péssima."), ("ecom_intent", "track_order", "Onde está minha encomenda? O rastreio não atualiza."),
           ("ecom_intent", "return_item", "Quero devolver o tênis, ficou pequeno."), ("ecom_intent", "refund_status", "Devolvi o produto há duas semanas e o reembolso não caiu."),
           ("ecom_intent", "cancel_order", "Cancelem o pedido que fiz hoje, por favor."), ("has_pii", "yes", "Meu CPF é 123.456.789-09 e meu telefone 11 98765-4321."),
           ("has_pii", "no", "O número do pedido é 99213."), ("support_route", "security", "Consigo ver os dados de outra empresa trocando o ID na URL."),
           ("support_route", "account_access", "Perdi o celular e não consigo passar da verificação em duas etapas.")],
}


def rows():
    for lang, xs in ML.items():
        for task, lab, x in xs:
            yield "d_multilingual", {"task": task, "state": x, "label": lab, "lang": lang, "tag": "d_ml"}
    for lab, xs in SUPPORT.items():
        for x in xs:
            yield "d_support_route", {"task": "support_route", "state": x, "label": lab, "lang": "en", "tag": "d"}
    for lab, xs in SENTIMENT.items():
        for x in xs:
            yield "d_sentiment", {"task": "sentiment", "state": x, "label": lab, "lang": "en", "tag": "d"}
    for lab, xs in ECOM.items():
        for x in xs:
            yield "d_ecom_intent", {"task": "ecom_intent", "state": x, "label": lab, "lang": "en", "tag": "d"}
    for lab, xs in AGENT.items():
        for x in xs:
            yield "d_agent_action", {"task": "agent_action", "state": x, "label": lab, "lang": "en", "tag": "d"}
    for lab, xs in LEAD.items():
        for x in xs:
            yield "d_lead_temp", {"task": "lead_temp", "state": x, "label": lab, "lang": "en", "tag": "d"}
    for task, xs in NOUL.items():
        for x, y in xs:
            yield "d_noul", {"task": task, "state": x, "label": y, "lang": "en", "tag": "d"}


def main():
    files = {}
    for name, r in rows():
        files.setdefault(name, []).append(r)
    for name, rs in files.items():
        (OUT / f"{name}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rs), encoding="utf-8")
    print({k: len(v) for k, v in files.items()})


if __name__ == "__main__":
    main()
