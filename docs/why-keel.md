# Why Keel

The case for putting a small local decision model in front of your LLM, in one page. For the details behind each claim, follow the links.

## The problem: small decisions ride the big loop

An agent session is full of small, typed decisions that nobody sees:

| Hidden decision | Kind | Usually answered by |
|---|---|---|
| Ask the user, or proceed? | choice | The main LLM, in prose |
| Is this shell command dangerous? | yes/no | Allow/deny rules, or an optional LLM judge |
| Which tool, area, owner or sub-agent? | choice | A full LLM turn |
| How urgent or risky is this? | score | Free text |
| Done, or keep going? | yes/no | The main LLM, or a small judge model |
| Does this need the big model? | choice | Your pick, or automatic routing |

Each of these costs a cloud round trip measured in seconds, is billed in tokens, sends context off the machine, and comes back as text that has to be parsed and can differ from run to run.

## The idea: System One for agents

A decision model answers typed questions (pick one, score it, yes or no) with probabilities, fast. An LLM does the open-ended reasoning. TypeSafe Jev and Microsoft-Decision-1 offer this as hosted APIs. Keel offers the same wire format as a 13M-parameter model on your own CPU.

| | Keel | Hosted decision model (Jev, MSD1) | LLM |
|---|---|---|---|
| Job | Typed choice, score, yes/no | Typed choice, score, yes/no | Open reasoning, writing code |
| Where | Your CPU, offline | Vendor cloud | Vendor cloud |
| Latency | <!-- num:k3.p95.idle -->13.7–14.3 ms<!-- /num --> p95 (Keel-3, idle CPU) | Vendor-reported: Jev 70–500 ms; MSD1 p50 85 ms | Seconds (claude-haiku-4.5 via CLI on blind: <!-- num:llm.p50 -->55.7 s<!-- /num --> p50) |
| Cost per call | Zero | Per input token, output free (vendor pricing) | Per token |
| Output | Probabilities | Probabilities | Free text |
| Tune on your data | Yes, on a CPU | No | Prompting only |
| Data leaves the machine | No | Yes | Yes |

## The design: Keel first, LLM fallback

<!-- diagram:keel-first -->

Keel answers every question with a calibrated confidence. If the confidence clears your threshold τ, act on Keel's answer; otherwise send the question to the LLM as before. You keep the LLM for the hard cases and stop paying it for the easy ones.

Measured with the Keel-3 release candidate `t1-r2e` at τ = 0.6 (the promoted Keel-3, `t1-r11`, has not been re-measured for tokens):

| Suite | LLM tokens | Accuracy (LLM alone → hybrid) |
|---|---|---|
| Held-out 100 | <!-- num:tok.k3.ho.cut -->75.8%<!-- /num --> fewer, <!-- num:tok.k3.ho.avoided -->75/100<!-- /num --> calls avoided | <!-- num:tok.k3.ho.acc -->75 → 89 of 100 cases fully right<!-- /num --> |
| Blind (choice questions) | <!-- num:tok.k3.blind.cut -->44.9%<!-- /num --> fewer | <!-- num:tok.k3.blind.acc -->64/71 → 63/71 (−1.4 pts)<!-- /num --> |

By workload, the cut ranged from <!-- num:tok.k3.wl.gating -->100%<!-- /num --> for edit/ask/stop gating to <!-- num:tok.k3.wl.severity -->39%<!-- /num --> for severity scoring. The method, the τ sweep and the cases where the hybrid costs more than it saves are in [Token savings](token-savings.md).

For comparison, Keel-2 in the same setup cut <!-- num:tok.k2.ho.cut -->60.6%<!-- /num --> of held-out tokens but lost <!-- num:tok.k2.ho.accdelta -->6<!-- /num --> cases. The Keel-3 line fixed that mainly through better calibration (blind ECE <!-- num:k2.ece.blind -->0.182<!-- /num --> → <!-- num:k3.ece.blind -->0.108<!-- /num -->).

## The safety net

- **Gate on confidence.** Keel answers only above τ; everything else goes to the LLM.
- **Tighten, never loosen.** Keel may block or escalate; it should never be the only approval for a destructive action. Keel-3 still makes <!-- num:k3.blind.safety -->11<!-- /num --> safety misses on the 234-case blind suite, and <!-- num:k3.blindc.safety -->12<!-- /num --> on the 100-case blind-c suite.
- **Kill switch.** Turn Keel off and agents behave exactly as before.
- **Re-measure.** `npm run keel:tokens` reruns the token benchmark against your LLM.

## Where Keel is not the right tool

Be clear about this before you adopt it:

- **Accuracy on its own.** On the blind suite Keel-3 gets <!-- num:k3.blind -->125/234<!-- /num --> fully right; claude-haiku-4.5 gets <!-- num:llm.blind -->215/234<!-- /num -->. A hosted 9B model such as Microsoft-Decision-1 will also likely be stronger on hard questions (not measured here; MSD1 vendor-reports 83.5% averaged over its own benchmark set).
- **Knowledge and long context.** Keel reads about 256 tokens per option and knows little about the world.
- **Terse in-context decisions.** If the agent already holds the text and answers in a few dozen tokens, calling Keel adds a tool round trip that costs more than it saves: with gpt-5.6-terra deciding in context, routing through Keel used <!-- num:tok.k3.scC.terra -->748.8%<!-- /num --> more tokens. The break-even is about <!-- num:tok.k3.breakeven -->215<!-- /num --> reasoning-plus-output tokens per question.

## Try it

[Quickstart](quickstart.md) gets you a running server and a first decision in five minutes; [Integrations](integrations.md) wires it into Copilot, Claude Code, Codex or Cursor.
