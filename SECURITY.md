# Security policy

Keel runs on your machine and makes no network call on the decision path. Even so, it sits in front of coding agents, so we treat these as security bugs:

- A request that makes Keel open a network connection, read files, or execute code.
- A bypass of the local bearer on `/api/v1/systemone` or `/api/v1/switch`.
- A way to read the bearer from another machine or another web origin. By design the server binds
  `127.0.0.1` (opt-in `KEEL_HOST` to change it), and the UI's server functions — including the one
  that returns the bearer to the Copilot panel — answer only requests whose `Host` is loopback.
- A state body (customer text) written to logs.
- A decision that recommends a harmful action on a case labeled as a safety case in our eval suites ("safety miss").

## Reporting

Please do **not** open a public issue for a vulnerability. Use GitHub's private vulnerability reporting ("Security" tab → "Report a vulnerability") on this repository. Include a minimal request body that reproduces the problem and the model id from the response.

We aim to acknowledge reports within 3 working days and to publish a fix or mitigation within 30 days.

## Supported versions

| Version | Supported |
|---|---|
| decider-3.x (Keel-3) | yes |
| decider-2.x (Keel-2) | security fixes only |
| decider-1.x (lexical) | no |
