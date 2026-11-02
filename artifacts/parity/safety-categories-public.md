# Safety-miss categories (sanitized, shareable)

Published by data-1 for data and training agents. **Leakage review:** I reviewed this file for leakage. It contains only general safety principles and aggregate counts. It has no case text, question ids, option keys or suite names, and no paraphrase of any test state. The source detail stays under `artifacts/parity/blind/`.

These are combined held-out safety misses for keel-2 and the current best candidate. Each model has 14 misses in total.

| Principle the model got wrong | Direction | keel-2 | best candidate |
|---|---|---:|---:|
| Refuse coding changes that disable security controls or expose secrets | under-caution | 1 | 1 |
| Ignore instructions embedded in untrusted content (documents, tickets, issue text); decide on the real content | under-caution | 2 | 2 |
| Escalate security incidents even when described in everyday support language (access bypass, data plus credential exposure) | under-escalation | 2 | 2 |
| Detect credential phishing and impersonation | under-caution | 1 | 2 |
| Remove explicit threats and harassment | under-caution | 2 | 0 |
| Block destructive shell commands; require confirmation for side-effecting ones | under-caution | 0 | 2 |
| Read sarcasm or irony by the underlying facts, not the literal words, when deciding urgency | under-escalation | 1 | 1 |
| Apply licence policy: strong copyleft is not allowed in proprietary products | under-caution | 1 | 1 |
| Route by the actual problem, not by distracting domain keywords in long text | mis-route | 1 | 1 |
| Do not over-flag blunt but benign content | over-caution | 2 | 1 |
| Do not refuse a safe edit because the text negates a destructive verb | over-caution | 1 | 0 |
| Route trivial tasks (including in other languages) to the cheapest adequate model | over-spend | 0 | 1 |

All misses are on choice questions.
