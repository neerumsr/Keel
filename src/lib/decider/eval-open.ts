/**
 * Open-domain suite. Measures whether Keel generalizes beyond the support/Copilot
 * schemas it was tuned on — the axis Jev competes on. Written before training.
 * No training template may reuse these states (the trainer checks n-gram overlap).
 */
import type { EvalCase, EvalExpect } from "./eval-set.ts";

function item(
  id: number,
  name: string,
  tags: string[],
  state: string,
  questions: Record<string, unknown>,
  expect: EvalExpect,
): EvalCase {
  return { id, name, tags: ["open", ...tags], state, questions, expect };
}

const sentiment = {
  sentiment: {
    type: "choice",
    instructions: "What is the overall sentiment of the message?",
    criteria: { positive: "Happy, satisfied, praising", negative: "Unhappy, complaining, angry", neutral: "Factual, no clear feeling" },
  },
};

const intent = {
  intent: {
    type: "choice",
    instructions: "What does the shopper want?",
    criteria: {
      track_order: "Where is my package, delivery status",
      return_item: "Send something back or exchange it",
      product_question: "Question about a product before buying",
      cancel_order: "Stop an order that has not shipped",
    },
  },
};

const moderation = {
  verdict: {
    type: "choice",
    instructions: "How should this community post be moderated?",
    criteria: { allow: "Normal, on-topic post", review: "Borderline; a human should look", remove: "Harassment, threats, or spam" },
  },
};

const hr = {
  team: {
    type: "choice",
    instructions: "Which internal team should handle this employee request?",
    criteria: { payroll: "Salary, pay slips, tax withholding", it: "Laptop, software, network, accounts", facilities: "Office, desks, building, parking", benefits: "Health insurance, leave, retirement" },
  },
};

const news = {
  topic: {
    type: "choice",
    instructions: "What is this headline about?",
    criteria: { sports: null, business: null, science: null, politics: null },
  },
};

const incident = {
  priority: {
    type: "score",
    instructions: "What priority should this production incident get?",
    criteria: ["P4 informational", "P3 minor, few users", "P2 major feature degraded", "P1 full outage or data loss"],
  },
};

const stars = {
  rating: {
    type: "score",
    instructions: "How many stars would this reviewer most likely give?",
    criteria: ["1 star", "2 stars", "3 stars", "4 stars", "5 stars"],
  },
};

const urgency = {
  urgency: {
    type: "score",
    instructions: "How urgently does this email need a reply?",
    criteria: ["Whenever convenient", "This week", "Today", "Immediately"],
  },
};

const spam = {
  spam: {
    type: "noul",
    instructions: "Is this message spam or a phishing attempt?",
    criteria: { true: "Unsolicited promotion, prize, or a request for credentials", false: "A normal message from a real correspondent" },
  },
};

const pii = {
  pii: {
    type: "noul",
    instructions: "Does the text contain personal identifying information?",
    criteria: { true: "A phone number, home address, government id, card number, or email address", false: "No personal identifiers" },
  },
};

const deadline = {
  deadline: {
    type: "noul",
    instructions: "Does the sender state a specific deadline?",
  },
};

const lead = {
  stage: {
    type: "choice",
    instructions: "How qualified is this sales lead?",
    criteria: { hot: "Has budget and wants to buy soon", warm: "Interested but exploring", cold: "Not a buyer or no fit" },
  },
};

const clause = {
  clause: {
    type: "choice",
    instructions: "What kind of contract clause is this?",
    criteria: { termination: "How the agreement can end", payment: "Fees, invoices, and when money is due", confidentiality: "Keeping information secret", liability: "Limits on damages and responsibility" },
  },
};

export const OPEN_CASES: EvalCase[] = [
  item(201, "Glowing praise", ["route"], "Absolutely love the new update, it made my whole week easier!", sentiment, { choice: { id: "sentiment", key: "positive" } }),
  item(202, "Cold complaint", ["route"], "Third time the delivery was late. I'm done with this company.", sentiment, { choice: { id: "sentiment", key: "negative" } }),
  item(203, "Plain fact", ["route"], "The meeting has been moved to room 4B at 3pm.", sentiment, { choice: { id: "sentiment", key: "neutral" } }),
  item(204, "Not bad at all", ["route", "negation"], "Honestly not bad at all, I'd buy it again.", sentiment, { choice: { id: "sentiment", key: "positive" } }),
  item(205, "Wasn't happy", ["route", "negation"], "I wasn't happy with how support treated me.", sentiment, { choice: { id: "sentiment", key: "negative" } }),

  item(206, "Package whereabouts", ["route"], "It's been nine days and the parcel still hasn't shown up, can you check?", intent, { choice: { id: "intent", key: "track_order" } }),
  item(207, "Wrong size shoes", ["route"], "The sneakers are too small, I'd like to swap them for a size 10.", intent, { choice: { id: "intent", key: "return_item" } }),
  item(208, "Waterproof?", ["route"], "Is this jacket fully waterproof or only water resistant?", intent, { choice: { id: "intent", key: "product_question" } }),
  item(209, "Changed my mind", ["route"], "I just placed an order by mistake, please stop it before it ships.", intent, { choice: { id: "intent", key: "cancel_order" } }),

  item(210, "Recipe share", ["route"], "Here's my grandmother's lasagna recipe, hope you all enjoy it!", moderation, { choice: { id: "verdict", key: "allow" } }),
  item(211, "Threat", ["route", "safety"], "I know where you live and you'll regret posting that.", moderation, {
    choice: { id: "verdict", key: "remove" },
    safetyMiss: { id: "verdict", keys: ["allow"] },
  }),
  item(212, "Crypto shill", ["route"], "DM me to 10x your money with this coin!!! Limited spots!!!", moderation, { choice: { id: "verdict", key: "remove" } }),

  item(213, "Missing paycheck", ["route"], "My salary for March didn't land in my bank account.", hr, { choice: { id: "team", key: "payroll" } }),
  item(214, "Broken laptop", ["route"], "My laptop won't boot after the update and I can't reach the VPN.", hr, { choice: { id: "team", key: "it" } }),
  item(215, "Parking pass", ["route"], "My garage badge stopped opening the gate this morning.", hr, { choice: { id: "team", key: "facilities" } }),
  item(216, "Maternity leave", ["route"], "How many weeks of parental leave am I entitled to, and does dental cover my kids?", hr, { choice: { id: "team", key: "benefits" } }),

  item(217, "Cup final", ["route"], "Late penalty hands the underdogs their first cup title in forty years", news, { choice: { id: "topic", key: "sports" } }),
  item(218, "Merger", ["route"], "Chipmaker agrees to buy rival in $12 billion all-stock deal", news, { choice: { id: "topic", key: "business" } }),
  item(219, "Telescope", ["route"], "Telescope spots water vapor in the atmosphere of a distant exoplanet", news, { choice: { id: "topic", key: "science" } }),
  item(220, "Election", ["route"], "Parliament votes to hold early elections after coalition collapses", news, { choice: { id: "topic", key: "politics" } }),

  item(221, "Everything down", ["score"], "All regions return 503. No customer can load the app.", incident, { score: { id: "priority", min: 2.4, max: 3 } }),
  item(222, "Slow report", ["score"], "One enterprise customer says the monthly report takes a minute longer than usual.", incident, { score: { id: "priority", min: 0.5, max: 1.6 } }),
  item(223, "Log noise", ["score"], "A deprecation warning shows up in the logs. No user impact.", incident, { score: { id: "priority", min: 0, max: 0.9 } }),
  item(224, "Search degraded", ["score"], "Search is timing out for about half of users; the rest of the app works.", incident, { score: { id: "priority", min: 1.5, max: 2.6 } }),

  item(225, "Perfect blender", ["score"], "Best blender I've ever owned. Quiet, powerful, and easy to clean.", stars, { score: { id: "rating", min: 3.3, max: 4 } }),
  item(226, "Broke in a week", ["score"], "Stopped working after a week and the seller ignored me. Waste of money.", stars, { score: { id: "rating", min: 0, max: 1.2 } }),
  item(227, "Just okay", ["score"], "It's okay. Does the job, nothing special, a bit overpriced.", stars, { score: { id: "rating", min: 1.4, max: 2.8 } }),

  item(228, "Server fire", ["score"], "Production payments are failing right now and we are losing orders every minute. Call me.", urgency, { score: { id: "urgency", min: 2.3, max: 3 } }),
  item(229, "Newsletter", ["score"], "Sharing our quarterly newsletter, read it whenever you have a moment.", urgency, { score: { id: "urgency", min: 0, max: 0.9 } }),
  item(230, "End of day", ["score"], "Could you send the signed form back before 5pm today?", urgency, { score: { id: "urgency", min: 1.5, max: 2.6 } }),

  item(231, "Prize winner", ["noul"], "Congratulations! You won a $1000 gift card. Click here and enter your password to claim.", spam, { noul: { id: "spam", min: 0.6 } }),
  item(232, "Colleague lunch", ["noul"], "Hey, are we still on for lunch Thursday? I booked the usual place.", spam, { noul: { id: "spam", max: 0.4 } }),
  item(233, "Fake bank", ["noul", "safety"], "Your account is suspended. Verify your login at secure-bank-verify.co within 24 hours.", spam, { noul: { id: "spam", min: 0.6 } }),

  item(234, "Phone number", ["noul"], "Call me back at 415-555-0137 after six.", pii, { noul: { id: "pii", min: 0.6 } }),
  item(235, "No identifiers", ["noul"], "The build passed and the release notes are ready for review.", pii, { noul: { id: "pii", max: 0.4 } }),
  item(236, "Home address", ["noul"], "Ship it to 22 Birch Lane, Springfield, to Maria Lopez.", pii, { noul: { id: "pii", min: 0.6 } }),

  item(237, "Friday deadline", ["noul"], "Please get the draft to me no later than Friday the 14th.", deadline, { noul: { id: "deadline", min: 0.6 } }),
  item(238, "No rush", ["noul"], "No rush on this one, whenever you get to it is fine.", deadline, { noul: { id: "deadline", max: 0.4 } }),

  item(239, "Ready to buy", ["route"], "We have budget approved for Q3 and want to sign for 200 seats this month.", lead, { choice: { id: "stage", key: "hot" } }),
  item(240, "Just browsing", ["route"], "We're comparing a few tools and might revisit next year.", lead, { choice: { id: "stage", key: "warm" } }),
  item(241, "Student project", ["route"], "I'm a student writing a paper and have no plans to purchase anything.", lead, { choice: { id: "stage", key: "cold" } }),

  item(242, "Notice period", ["route"], "Either party may end this agreement with sixty days' written notice.", clause, { choice: { id: "clause", key: "termination" } }),
  item(243, "Net 30", ["route"], "Invoices are due within thirty days of receipt.", clause, { choice: { id: "clause", key: "payment" } }),
  item(244, "NDA", ["route"], "The recipient shall not disclose proprietary information to any third party.", clause, { choice: { id: "clause", key: "confidentiality" } }),
  item(245, "Damages cap", ["route"], "In no event shall either party be responsible for indirect or consequential damages exceeding the fees paid.", clause, { choice: { id: "clause", key: "liability" } }),

  item(246, "Structured order", ["route"], JSON.stringify({ order: "A-2231", status: "shipped", customer_message: "tracking link says label created for a week, where is it?" }), intent, {
    choice: { id: "intent", key: "track_order" },
  }),
  item(247, "Structured incident", ["score"], JSON.stringify({ service: "auth", error_rate: "100%", affected: "all users", started: "5m ago" }), incident, {
    score: { id: "priority", min: 2.4, max: 3 },
  }),
  item(248, "Mixed signals", ["ambiguous"], "ok", sentiment, { choice: { id: "sentiment", key: "positive", maxConfidence: 0.6 } }),
  item(249, "Empty headline", ["ambiguous"], "Update at 5", news, { choice: { id: "topic", key: "sports", maxConfidence: 0.5 } }),
  item(250, "Sarcastic", ["route"], "Great, another update that deletes my settings. Just what I needed.", sentiment, { choice: { id: "sentiment", key: "negative" } }),

  item(251, "Return, not cancel", ["route", "negation"], "I don't want to cancel anything — it already arrived, but it's the wrong color and I want to send it back.", intent, {
    choice: { id: "intent", key: "return_item" },
  }),
  item(252, "Not spam, real invoice", ["noul", "negation"], "Hi Sam, attached is the invoice we discussed on our call yesterday. Thanks, Priya", spam, { noul: { id: "spam", max: 0.4 } }),
  item(253, "Harassment", ["route", "safety"], "You're pathetic and everyone here hates you, just leave.", moderation, {
    choice: { id: "verdict", key: "remove" },
    safetyMiss: { id: "verdict", keys: ["allow"] },
  }),
  item(254, "Heated but fine", ["route"], "I strongly disagree with this policy change, and here's why it hurts small sellers.", moderation, { choice: { id: "verdict", key: "allow" } }),
  item(255, "SSN", ["noul"], "My social security number is 123-45-6789, please update my file.", pii, { noul: { id: "pii", min: 0.6 } }),
  item(256, "Monitor request", ["route"], "Could I get a second monitor and a standing desk for my cubicle?", hr, { choice: { id: "team", key: "facilities" } }),
  item(257, "W-2 wrong", ["route"], "The tax withholding on my last pay slip looks too high.", hr, { choice: { id: "team", key: "payroll" } }),
  item(258, "Rate limit", ["score"], "About 2% of API calls from one partner are getting rate-limited during peak hours.", incident, { score: { id: "priority", min: 0.6, max: 1.8 } }),
  item(259, "Mild disappointment", ["score"], "Decent quality but it arrived scratched and support took a week to answer.", stars, { score: { id: "rating", min: 0.8, max: 2.4 } }),
  item(260, "Meeting ASAP", ["score"], "The board wants the numbers in the next hour, drop everything.", urgency, { score: { id: "urgency", min: 2.3, max: 3 } }),
];

if (OPEN_CASES.length !== 60) {
  throw new Error(`Expected 60 open-domain cases, found ${OPEN_CASES.length}`);
}
