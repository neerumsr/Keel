# Hugging Face upload for Keel-Pro. NOT EXECUTED BY ANYONE YET.
#
# Every command is commented out on purpose. Read hf/keel-pro/FILES.md and
# RELEASE_CHECKLIST.md section 3 (Keel-Pro), then uncomment and run the lines one at a time from the repo root.
#
# Prerequisites (one-time, by the maintainer):
#   pip install -U "huggingface_hub[cli]"
#   huggingface-cli login            # write token; never commit or paste it anywhere
#
# Parameters (fill from artifacts/parity/pro/status.json "finalist")
# $HfRepo   = "neerumsr/keel-pro"
# $HfGguf   = "neerumsr/keel-pro-GGUF"
# $Run      = "C:/KeelWork/pro/runs/soup78"   # adapter in $Run/soup (it7+it8 average)
# $Base     = "C:/KeelWork/models/Qwen3.5-27B"
# $Gguf     = "C:/KeelWork/gguf"
# $Revision = "v1.0.0"
# $Stage    = "hf/_stage-pro"
#
# 1. Stage the adapter repo.
# Remove-Item -Recurse -Force $Stage -ErrorAction SilentlyContinue
# New-Item -ItemType Directory -Force $Stage | Out-Null
# Copy-Item artifacts/parity/pro/MODEL_CARD.md "$Stage/README.md"
# Copy-Item LICENSE, hf/keel-pro/NOTICE $Stage
# Copy-Item "$Run/soup/adapter_config.json", "$Run/soup/adapter_model.safetensors" $Stage
# foreach ($f in "tokenizer.json", "tokenizer_config.json", "chat_template.jinja") { if (Test-Path "$Base/$f") { Copy-Item "$Base/$f" $Stage } }
# Copy-Item "$Run/keel-pro.json" $Stage
#
# 2. Checks.
# if (Select-String -Path "$Stage/README.md" -Pattern "TBD") { throw "fill the TBDs in MODEL_CARD.md" }
# node scripts/oss-audit.mjs --fail-on medium; if ($LASTEXITCODE) { throw "audit not clean" }
#
# 3. Checksums.
# Get-ChildItem $Stage -Recurse -File | Where-Object Name -ne "SHA256SUMS" | ForEach-Object {
#   "{0}  {1}" -f (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLower(), $_.Name
# } | Set-Content -Encoding ascii "$Stage/SHA256SUMS"
#
# 4. Upload the adapter repo.
# huggingface-cli repo create ($HfRepo.Split('/')[1]) --type model --organization ($HfRepo.Split('/')[0])
# huggingface-cli upload $HfRepo $Stage . --repo-type model --commit-message "Keel-Pro $Revision"
# huggingface-cli tag $HfRepo $Revision --repo-type model
#
# 5. GGUF repo (card, LICENSE, NOTICE and the two quantizations).
# huggingface-cli repo create ($HfGguf.Split('/')[1]) --type model --organization ($HfGguf.Split('/')[0])
# huggingface-cli upload $HfGguf "$Stage/README.md" README.md --repo-type model
# huggingface-cli upload $HfGguf LICENSE LICENSE --repo-type model
# huggingface-cli upload $HfGguf hf/keel-pro/NOTICE NOTICE --repo-type model
# huggingface-cli upload $HfGguf "$Gguf/keel-pro-27b-Q8_0.gguf" keel-pro-Q8_0.gguf --repo-type model
# huggingface-cli upload $HfGguf "$Gguf/keel-pro-27b-Q4_K_M.gguf" keel-pro-Q4_K_M.gguf --repo-type model
#
# 6. Clean up.
# Remove-Item -Recurse -Force $Stage
