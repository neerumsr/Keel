# Keel-Pro sidecar (Qwen3.5-27B base in 4-bit NF4 + the Keel-Pro LoRA adapter). Needs an NVIDIA GPU with 24 GB+
# (about 21 GB measured; 32 GB+ recommended for long states). Weights are mounted, not baked in.
#   docker build -f serve/Dockerfile -t keel-pro-sidecar .
#   docker run --gpus all -v <Qwen3.5-27B>:/models/base:ro -v <keel-pro adapter>:/models/adapter:ro keel-pro-sidecar
# The sidecar binds 127.0.0.1 and has no auth: run it in the same network namespace as Keel (a Kubernetes pod or
# Compose network_mode: service:...). See docs/deployment.md.

FROM nvidia/cuda:12.8.1-cudnn-runtime-ubuntu24.04
LABEL org.opencontainers.image.title="Keel-Pro sidecar" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.source="https://github.com/sivamatic/Keel"
ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    VIRTUAL_ENV=/opt/venv PATH=/opt/venv/bin:$PATH \
    PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True HF_HUB_OFFLINE=1
RUN apt-get update && apt-get install -y --no-install-recommends python3.12 python3.12-venv curl \
    && rm -rf /var/lib/apt/lists/* && python3.12 -m venv /opt/venv
RUN pip install torch==2.11.0 --index-url https://download.pytorch.org/whl/cu128
COPY serve/requirements.txt /app/serve/requirements.txt
RUN pip install -r /app/serve/requirements.txt
COPY serve/keel_pro_server.py /app/serve/keel_pro_server.py
COPY training/pro/common.py /app/training/pro/common.py
WORKDIR /app
RUN useradd --create-home --uid 10001 keel
USER keel
EXPOSE 8090
HEALTHCHECK --interval=30s --timeout=5s --start-period=600s --retries=3 CMD curl -fsS http://127.0.0.1:8090/health || exit 1
ENTRYPOINT ["python", "serve/keel_pro_server.py"]
CMD ["--model-dir", "/models/base", "--adapter", "/models/adapter", "--load-4bit", "--port", "8090"]
