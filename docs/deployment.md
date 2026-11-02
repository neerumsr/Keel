# Deploy Keel

Run Keel on your laptop, in a container, on Kubernetes or in any cloud. This page gives a copy-paste path for each, with
the sizes we measured and the security rules that keep your decision data private.

<!-- diagram:deploy-pick -->

## Pick a setup

| You want | Use | Hardware | Speed (measured) | Section |
|---|---|---|---|---|
| Fast, free decisions next to your agent | **Keel-Lite** (`decider-latest`) | Any CPU, 1–2 GB RAM | p95 about 14 ms in-process | [Local](#1-local-no-container), [Docker](#2-docker-keel-lite) |
| A shared Keel for a team or service | **Keel-Lite in a container** | 0.5–1 vCPU, 1–2 GB per replica | same, plus your network | [Kubernetes](#4-kubernetes), [Cloud](#5-cloud-recipes) |
| The most accurate decisions (Decision Index 62.73, full public suite) | **Keel-Pro** (`decider-pro-1.0.0`) | NVIDIA GPU, 24 GB+ (32 GB+ recommended) | median 245 ms per request (DI full public suite, RTX 5090) | [Compose](#3-docker-compose-with-keel-pro), [Kubernetes](#4-kubernetes) |
| Keel-Pro on a smaller GPU or a Mac, outside Keel | **Keel-Pro GGUF** with llama.cpp | ~17 GB (Q4_K_M) | median 0.24 s per question (RTX 5090) | [GGUF](#6-keel-pro-gguf-with-llamacpp) |

Keel-Lite is always there. Keel-Pro is opt-in: a request gets it only when it pins `"model": "decider-pro-1.0.0"`.

## Sizes we measured

| Part | Disk | Memory | Notes |
|---|---|---|---|
| Keel server image (app + Keel-2/Keel-3 ONNX) | about 210 MB of app files | 355 MB working set, 771 MB peak under load | Measured on Windows from the same files the image ships |
| Keel-Pro sidecar | Qwen3.5-27B base about 52 GB, adapter about 0.8 GB | about 21 GB GPU (4-bit NF4 base + LoRA) | Long states need headroom; 32 GB+ is comfortable |
| Keel-Pro GGUF | Q4_K_M 16.8 GB, Q8_0 29.0 GB | about the file size, in VRAM | llama.cpp; matched the HF run on 30/30 dev questions |

## How the pieces fit

<!-- diagram:deploy-pod -->

- **Keel server** (Node, port 8080) checks the key, validates the request, runs Keel-Lite and formats every answer.
- **Keel-Pro sidecar** (Python, port 8090) turns questions into option probabilities on the GPU. It has **no auth of
  its own** and binds `127.0.0.1`. Keel refuses to send decision data to a sidecar that is not on loopback.
- So in containers the two must **share one network namespace**: one Kubernetes pod, or Compose
  `network_mode: service:…`. The sidecar port is never exposed.

## 1. Local (no container)

```powershell
npm install
npm run build; npm start            # http://127.0.0.1:8080, loopback only
npm run -s keel:token               # your API key
```

Keel-Pro locally: see [Keel-Pro serving](../artifacts/parity/pro/SERVE.md).

## 2. Docker (Keel-Lite)

```bash
docker build -t keel .
export KEEL_SECRET="$(openssl rand -base64 48)"       # keep it in your secret store, not in git
docker run -d --name keel -p 8080:8080 -e KEEL_SECRET keel
docker exec keel npm run -s keel:token              # the API key (derived from KEEL_SECRET)
curl -s http://localhost:8080/api/v1/status
```

Or with Compose: put `KEEL_SECRET=…` in a `.env` file (gitignored) and run `docker compose up -d`.

Inside the container Keel listens on all interfaces (`KEEL_HOST=0.0.0.0`) so the port can be published. That is safe
because:

| Request from another machine | Result |
|---|---|
| `POST /api/v1/systemone` without the key | `401` |
| `POST /api/v1/systemone` with the key | the answer |
| The web UI's private functions (they reveal the key) | `403`; the UI works only through `localhost` |

Need the UI on a remote box? Use an SSH tunnel: `ssh -L 8080:localhost:8080 <host>`, then open `http://localhost:8080`.

## 3. Docker Compose with Keel-Pro

On one Linux host with an NVIDIA GPU and the
[NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html):

```bash
# 1. Weights (once). The base is Apache-2.0; the adapter is the Keel-Pro release.
hf download Qwen/Qwen3.5-27B --local-dir /srv/keel/Qwen3.5-27B
#    Keel-Pro adapter: from the Hugging Face release, or from your own training run (docs/keel-pro.md)

# 2. Config (.env next to compose.pro.yaml, never committed)
KEEL_SECRET=<long random string>
KEEL_PRO_BASE=/srv/keel/Qwen3.5-27B
KEEL_PRO_ADAPTER=/srv/keel/keel-pro-adapter

# 3. Run
docker compose -f compose.pro.yaml up -d
docker compose -f compose.pro.yaml logs -f keel-pro-sidecar     # wait for {"event": "ready"} (a few minutes)
```

Ask Keel-Pro:

```bash
TOKEN=$(docker compose -f compose.pro.yaml exec keel npm run -s keel:token)
curl -s http://localhost:8080/api/v1/systemone -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"model":"decider-pro-1.0.0","state":"Deploy failed: health check timeout after DB migration.",
       "questions":{"next":{"type":"choice","instructions":"What should on-call do first?",
         "criteria":{"retry":"Run the deploy again","rollback":"Undo the release","page":"Wake the DB owner"}}}}'
```

If the sidecar is down, Pro requests get `503 model_unavailable`. They never silently fall back to Keel-Lite.

## 4. Kubernetes

Works the same on AKS, EKS, GKE or your own cluster. Build and push both images to your registry, then replace
`REGISTRY/…:VERSION` in the manifests.

```bash
kubectl create secret generic keel --from-literal=KEEL_SECRET="$(openssl rand -base64 48)"

# Keel-Lite: 2 replicas, CPU only
kubectl apply -f deploy/kubernetes/keel.yaml

# Keel + Keel-Pro: one pod with both containers on a GPU node (needs the NVIDIA device plugin)
kubectl apply -f deploy/kubernetes/keel-pro.yaml
```

| In the manifests | Why |
|---|---|
| Both containers in one pod (`keel-pro.yaml`) | They share `localhost`, so the sidecar stays private |
| `startupProbe` allows 15 minutes | Loading a 27B model from disk takes minutes |
| `runAsNonRoot`, `drop: ALL`, no privilege escalation | Least privilege |
| `KEEL_SECRET` from a Secret | Same key on every replica; rotate by changing the Secret |
| Optional `DATABASE_URL` | With 2+ replicas, one Postgres keeps the on/off switch the same everywhere |

Put your ingress (with TLS) in front of the `keel` or `keel-pro` Service.

## 5. Cloud recipes

These are standard managed-container commands. **We test the container images, not each cloud account**; see
[What we tested](#what-we-tested).

### Keel-Lite (CPU)

**Azure Container Apps**

```bash
az group create -n keel-rg -l eastus
az acr create -n <acr> -g keel-rg --sku Basic
az acr build -r <acr> -t keel:1.0 .
az containerapp env create -n keel-env -g keel-rg -l eastus
az containerapp create -n keel -g keel-rg --environment keel-env \
  --image <acr>.azurecr.io/keel:1.0 --registry-server <acr>.azurecr.io --registry-identity system \
  --target-port 8080 --ingress external --cpu 1 --memory 2Gi --min-replicas 1 \
  --secrets keel-secret=<long random string> --env-vars KEEL_SECRET=secretref:keel-secret
```

**Google Cloud Run**

```bash
printf '%s' "<long random string>" | gcloud secrets create keel-secret --data-file=-
gcloud run deploy keel --source . --port 8080 --memory 2Gi --min-instances 1 \
  --set-secrets KEEL_SECRET=keel-secret:latest --allow-unauthenticated   # Keel's own key still guards every call
```

**AWS (ECR + App Runner)**

```bash
aws ecr create-repository --repository-name keel
docker build -t <account>.dkr.ecr.<region>.amazonaws.com/keel:1.0 . && docker push <account>.dkr.ecr.<region>.amazonaws.com/keel:1.0
# Store KEEL_SECRET in Secrets Manager, then create the App Runner service from the image with port 8080 and
# RuntimeEnvironmentSecrets KEEL_SECRET=<secret ARN>. ECS Fargate with the same image works too.
```

### Keel-Pro (GPU)

| Cloud | Simplest path | GPU that fits |
|---|---|---|
| Any | A GPU VM + [Compose](#3-docker-compose-with-keel-pro) | 24 GB+: L4 (tight), L40S 48 GB, A100, H100, RTX PRO 6000 |
| Azure | AKS with a GPU node pool + `keel-pro.yaml` | NC A100 v4, NCads H100 v5 |
| AWS | EKS with a GPU node group + `keel-pro.yaml` | g6e (L40S), p4d/p5 |
| Google Cloud | GKE with a GPU node pool + `keel-pro.yaml` | g2 (L4, tight), a2/a3 |

Keep the weights on a persistent volume or bake a private image layer. Do not download 52 GB on every start.

## 6. Keel-Pro GGUF with llama.cpp

For a smaller GPU or Apple silicon, the GGUF build runs in llama.cpp. It answers with the same letters policy
(`scripts/di/gguf_engine.py` shows the exact prompt and scoring). The Keel server does not proxy to llama.cpp today,
so call it from your own code, or use the sidecar for the `decider-pro-1.0.0` pin.

## Security checklist

- [ ] `KEEL_SECRET` is long, random, and comes from a secret store. Never bake it into an image or commit it.
- [ ] TLS terminates at your ingress or load balancer. Keel itself speaks plain HTTP.
- [ ] The sidecar port (8090) is never published or exposed by a Service.
- [ ] Keep the default rate limit (`KEEL_RATE_PER_MINUTE=120` per instance) on public endpoints.
- [ ] Logs never contain the key or decision `state`. Keel does not log either.
- [ ] Report vulnerabilities privately: [SECURITY.md](../SECURITY.md).

## Settings

| Variable | Default | What it does |
|---|---|---|
| `KEEL_SECRET` | random, stored in `KEEL_SECRET_FILE` | Seed of the API key. Set it in any shared deployment. |
| `KEEL_SECRET_FILE` | `~/.keel/secret` (`/data/secret` in the image) | Where the generated secret is kept when `KEEL_SECRET` is unset |
| `KEEL_HOST` | `127.0.0.1` (`0.0.0.0` in the image) | Interface to listen on |
| `PORT` | `8080` | HTTP port |
| `KEEL_PRO_URL` | `http://127.0.0.1:8090` | Keel-Pro sidecar; loopback only |
| `KEEL_RATE_PER_MINUTE` | `120` | Decisions per minute per instance; `0` turns the limit off |
| `KEEL_MODEL_DIR` | `models/keel-3`, then `models/keel-2` | Keel-Lite model directory |
| `DATABASE_URL` | unset (embedded PGlite) | Postgres for the shared on/off switch |

## Operate it

| Task | How |
|---|---|
| Health check | `GET /api/v1/status` (no key needed). Sidecar: `GET /health` from inside the pod |
| Pin a model version | Clients send `"model": "decider-3.0.0"` or `"decider-pro-1.0.0"`; `decider-latest` follows the default |
| Upgrade | Roll out a new image tag. Pinned clients keep the model they asked for |
| Roll back | Redeploy the previous tag |
| Scale | Keel-Lite: add replicas (CPU-bound, stateless). Keel-Pro: one GPU per pod, add pods |
| Turn decisions off | `POST /api/v1/switch {"enabled": false}`, or the UI switch |

## Call a deployed Keel

Every client from the [Quickstart](quickstart.md) and [Integrations](integrations.md) works. Only the base URL and
key change:

| Client | Setting |
|---|---|
| curl / any HTTP | `https://<your-host>/api/v1/systemone` + `Authorization: Bearer <key>` |
| TypeSafe Jev SDKs | `TYPESAFE_BASE_URL=https://<your-host>/api` |
| Microsoft-Decision-1 clients | `https://<your-host>/providers/microsoft/v1/systemone` + `api-key: <key>` |
| MCP (`keel-mcp`) | `KEEL_URL=https://<your-host>`, `KEEL_TOKEN=<key>` |

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `401 unauthorized` | Wrong or missing key | Read it again with `npm run -s keel:token` in the same environment (same `KEEL_SECRET`) |
| Keys differ between replicas | No `KEEL_SECRET`, so each replica generated its own | Set `KEEL_SECRET` from one Secret |
| `503 model_unavailable` on Pro | Sidecar not ready or not on loopback | Wait for `{"event": "ready"}`; keep both containers in one pod/namespace |
| Sidecar `CUDA out of memory` | GPU under 24 GB, or very long states | Use a bigger GPU or the GGUF build |
| UI shows 403 from another machine | By design: the UI reveals the key | SSH tunnel to `localhost` |
| `429` | Rate limit | Raise `KEEL_RATE_PER_MINUTE` deliberately |

## What we tested

| Check | Status |
|---|---|
| Keel image layout (built server + models, no `node_modules`) answers a decision; 401 without key; 403 for remote UI functions | ✅ Tested locally |
| `docker build` + run + one decision | ✅ In CI on every pull request (`.github/workflows/containers.yml`) |
| Keel-Pro sidecar | ✅ Tested on an RTX 5090, outside a container; image builds in CI |
| Keel-Pro image on a cloud GPU | ⬜ Not yet. Reports welcome |
| Azure / Google / AWS recipes | ⬜ Standard commands, not yet run by us end to end |
