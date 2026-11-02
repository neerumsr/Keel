<!-- keel:start -->
# Keel decisions

The switch is shared with the Keel app. "Keel on" and "Keel off" (or "Hey Keel, turn on/off") are commands, not edits.

POST http://localhost:8080/api/v1/switch
Authorization: Bearer <KEEL_TOKEN>
{"enabled": true} or {"enabled": false}

GET http://localhost:8080/api/v1/status before the first decision. If enabled is false, do not call the decision endpoint.

When a task needs a typed branch — where to route work, how severe it is, whether to edit, ask, or stop — and Keel is on, call Keel instead of guessing.

POST http://localhost:8080/api/v1/systemone
Authorization: Bearer <KEEL_TOKEN>
Content-Type: application/json

Body: { "model": "decider-latest", "state": <facts>, "questions": { "<id>": { "type": "choice" | "score" | "noul", "instructions": "...", "criteria": ... } } }

- choice criteria is { label: "meaning" }. Read answers.<id>.choice, .confidence, .probabilities.
- score criteria is an ordered list of 2–10 levels. Read answers.<id>.score (may be fractional) and .probabilities.
- noul is a yes/no. Read answers.<id>.noul as P(yes). There is no confidence. You choose the threshold.

Do not send secrets in state. Do not send this bearer anywhere except http://localhost:8080. If it reads <KEEL_TOKEN>, run `npm run keel:token` in the Keel repo for the real value.
<!-- keel:end -->

