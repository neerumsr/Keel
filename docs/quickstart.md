# Quickstart

Run Keel on your machine and get your first typed decision in about a minute. You will start a local server, find your key, ask one question with curl, and then call it from Python, TypeScript, the TypeSafe Jev SDK and a Microsoft-Decision-1 client.

<!-- diagram:quickstart -->

## 1. Install and run

You need **Node 22 or later**. Python is needed only for training. No GPU is needed.

```powershell
git clone https://github.com/sivamatic/Keel.git
cd Keel
npm install
npm run dev            # http://localhost:8080 (bound to 127.0.0.1)
```

`npm run dev` is plain `vite dev`. For a long-running service use `npm run build` then `npm start`, a standalone Node server on the same address. There is no sign-in; your local key (step 2) is the only credential.

The repository ships the model weights in `models/`. If the folder is missing, for example in a shallow checkout, run `npm run model:fetch`. Keel then loads the zero-shot base model and reports `decider-2.0.0-zeroshot`.

Check that the server is up. The status route needs no key:

```powershell
curl.exe -s http://localhost:8080/api/v1/status
```

```json
{"enabled":true,"model":"decider-3.0.0","engine":"neural","neural":{"loaded":true,"id":"decider-3.0.0","error":null},"fallback":"decider-1.2.0"}
```

## 2. Get your local key

Decision calls need a bearer key. `npm run keel:token` prints yours; `-s` keeps npm's banner out of the variable:

```powershell
# PowerShell
$env:KEEL_TOKEN = npm run -s keel:token
```

```bash
# bash / zsh
export KEEL_TOKEN=$(npm run -s keel:token)
```

The key is unique to your install. On first use Keel generates a random secret and stores it in `~/.keel/secret` (file mode 0600, outside the repo), and the key is an HMAC of that secret. The bench UI's Copilot tab also shows the key, but only to requests from your own machine.

To share one key across machines or CI, set `KEEL_SECRET` instead; it takes precedence over the file. To rotate the key, delete `~/.keel/secret` (or change `KEEL_SECRET`), restart `npm run dev`, and rerun `npm run keel:agents`.

The dev server listens on `127.0.0.1:8080` by default. Set `KEEL_HOST` only if you deliberately want another interface, and do not expose the port to a network you do not control.

## 3. Ask your first question

One request can ask several questions about the same `state`. This one asks all three types at once.

```bash
# bash / zsh
curl -s http://localhost:8080/api/v1/systemone \
  -H "Authorization: Bearer $KEEL_TOKEN" -H "Content-Type: application/json" \
  -d '{"state":"I was charged twice for my subscription this month.",
       "questions":{
         "team":{"type":"choice","instructions":"Which team should handle this ticket?",
                 "criteria":{"billing":"Payments, refunds, invoices","tech":"Bugs and outages","sales":"New purchases"}},
         "urgency":{"type":"score","instructions":"How urgent is it?","criteria":["Low","Medium","High"]},
         "refund":{"type":"noul","instructions":"Is the customer asking for money back?"}}}'
```

```powershell
# PowerShell 7
$body = @{
  state = "I was charged twice for my subscription this month."
  questions = @{
    team    = @{ type = "choice"; instructions = "Which team should handle this ticket?"
                 criteria = @{ billing = "Payments, refunds, invoices"; tech = "Bugs and outages"; sales = "New purchases" } }
    urgency = @{ type = "score"; instructions = "How urgent is it?"; criteria = @("Low", "Medium", "High") }
    refund  = @{ type = "noul"; instructions = "Is the customer asking for money back?" }
  }
} | ConvertTo-Json -Depth 6
Invoke-RestMethod http://localhost:8080/api/v1/systemone -Method Post -ContentType "application/json" `
  -Headers @{ Authorization = "Bearer $env:KEEL_TOKEN" } -Body $body | ConvertTo-Json -Depth 6
```

The response has one answer per question id. This is real output from Keel-3 (`decider-3.0.0`); values change between model versions:

```json
{
  "model": "decider-3.0.0",
  "answers": {
    "team":    { "type": "choice", "choice": "billing", "confidence": 0.996,
                 "probabilities": { "billing": 0.9963, "tech": 0.0018, "sales": 0.0019 } },
    "urgency": { "type": "score", "score": 1.04, "confidence": 0.439,
                 "legend": { "0": "Low", "1": "Medium", "2": "High" },
                 "probabilities": { "0": 0.4032, "1": 0.1576, "2": 0.4392 } },
    "refund":  { "type": "noul", "noul": 0.1503 }
  },
  "usage": { "input_tokens": 0, "output_tokens": 0 }
}
```

How to read it:

- **`choice`** is the winning option, and `confidence` is its probability.
- **`score`** is the expected level, Σ i·pᵢ. Here 1.04 is near Medium (1), but the probabilities are split between Low (0.40) and High (0.44) and `confidence` is only 0.439: Keel is unsure, so this is a question to defer to an LLM or a human.
- **`noul`** is P(yes). Here 0.15 means "probably not asking for money back". The customer reported a double charge but did not ask for a refund, so a careful client treats anything between 0.4 and 0.6 as unsure.
- **`usage`** is always zero, because nothing is billed.

See [Concepts](concepts.md) for confidence, the τ gate, and when to defer to an LLM.

## 4. Call it from code

### Python (requests)

```python
import os, requests

r = requests.post(
    "http://localhost:8080/api/v1/systemone",
    headers={"Authorization": f"Bearer {os.environ['KEEL_TOKEN']}"},
    json={
        "state": "git push --force origin main",
        "questions": {
            "cmd": {"type": "choice", "instructions": "The agent wants to run this command.",
                    "criteria": {"run": "Read-only or workspace-scoped",
                                 "confirm": "Has side effects; ask the user",
                                 "block": "Destructive or exfiltrates data"}}
        },
    },
    timeout=5,
)
r.raise_for_status()
a = r.json()["answers"]["cmd"]
if a["confidence"] < 0.6 or a["choice"] != "run":
    print("ask the user or the LLM:", a)
```

### TypeScript (fetch, Node 18+)

```ts
const res = await fetch("http://localhost:8080/api/v1/systemone", {
  method: "POST",
  headers: { Authorization: `Bearer ${process.env.KEEL_TOKEN}`, "Content-Type": "application/json" },
  body: JSON.stringify({
    state: "Adds a 7% discount on orders over $500.",
    questions: { tests: { type: "noul", instructions: "Should this change ship with new tests?" } },
  }),
});
if (!res.ok) throw new Error((await res.json()).error.message);
const { answers } = await res.json();
console.log(answers.tests.noul); // P(yes)
```

## 5. Drop-in for the TypeSafe Jev SDK

The official Jev SDKs build `${baseURL}/v1/systemone`, so point the base URL at Keel's `/api` prefix. Turn request compression off: the SDKs zstd-compress bodies of 1 KiB or more, and Keel does not decode compressed bodies yet.

```powershell
$env:TYPESAFE_API_KEY  = $env:KEEL_TOKEN
$env:TYPESAFE_BASE_URL = "http://localhost:8080/api"
```

```python
from typesafe_sdk import TypeSafeClient, Choice, Score, Noul

with TypeSafeClient(compression=False) as client:
    r = client.system_one(state="I was charged twice this month.", questions={
        "department": Choice(instructions="Which team?", criteria={"Billing": "Payments", "Tech Support": "Bugs"}),
        "urgency": Score(instructions="How urgent?", criteria=["Low", "Medium", "High"]),
        "refund": Noul(instructions="Is the customer asking for money back?"),
    })
```

```ts
import { TypeSafeClient, choice } from "@typesafe-ai/sdk";
const client = new TypeSafeClient({ apiKey: process.env.KEEL_TOKEN, baseURL: "http://localhost:8080/api", compression: false });
const r = await client.systemOne({ state, questions: { department: choice("Which team?", { Billing: "Payments", "Tech Support": "Bugs" }) } });
```

The SDK default model `jev-latest` makes Keel report **Jev-style confidence**, (p_max − 1/n)/(1 − 1/n), so existing `confidence < 0.5` gates keep their meaning. `client.models.list()` does not work yet, because Keel returns an OpenAI-style list. This was verified with `typesafe-sdk` 0.7.5 and `@typesafe-ai/sdk` 0.7.0.

## 6. Drop-in for Microsoft-Decision-1 clients

Keel serves the Foundry path and accepts the Foundry `api-key` header on decision calls:

```bash
curl -s http://localhost:8080/providers/microsoft/v1/systemone \
  -H "api-key: $KEEL_TOKEN" -H "Content-Type: application/json" \
  -d '{"model":"microsoft-decision-1","state":"Refund my order please",
       "questions":{"refund":{"type":"noul","instructions":"Is this a refund request?"}}}'
# {"model":"decider-3.0.0","answers":{"refund":{"type":"noul","noul":0.9184}},"usage":{"input_tokens":0,"output_tokens":0}}
```

The response `model` names the Keel judge that answered, not the alias you sent.

- Replace `{endpoint}` with `http://localhost:8080`, and the Foundry key with your Keel key.
- Use the model name `microsoft-decision-1`, or omit `model`. Custom Foundry deployment names are rejected with a 400.
- Entra ID tokens are not accepted. Keel has no identity provider.
- OpenRouter clients that call `https://openrouter.ai/api/v1/systemone` can switch their base URL to `http://localhost:8080/api` and keep the model `microsoft/microsoft-decision-1`.

## Next steps

- [Concepts](concepts.md): how choice, score and noul work, and how to gate on confidence.
- [Integrations](integrations.md): one-command setup for Copilot CLI, VS Code, Claude Code, Codex and Cursor.
- [Use cases](use-cases.md): 50 ready-to-run request bodies.
- [API reference](api-reference.md): every field, limit and error.
