# Hugging Face upload for the Keel weights. NOT EXECUTED BY ANYONE YET.
#
# Every command is commented out on purpose. Read RELEASE_CHECKLIST.md (step "Hugging Face upload")
# and hf/FILES.md, then uncomment and run the lines one at a time from the repo root.
#
# Prerequisites (one-time, by the maintainer):
#   pip install -U "huggingface_hub[cli]"
#   huggingface-cli login            # token with write access; never commit or paste it anywhere
#
# Parameters
# $HfRepo   = "neerumsr/keel-3"            # or neerumsr/keel-2 if Keel-3 was not promoted
# $Model    = "models/keel-3"           # or models/keel-2
# $Revision = "v3.0.0"                  # tag created on the HF repo after upload
# $Stage    = "hf/_stage"               # local staging folder (gitignored *.onnx)
#
# 1. Assemble a clean staging folder with exactly the files in hf/FILES.md.
# Remove-Item -Recurse -Force $Stage -ErrorAction SilentlyContinue
# New-Item -ItemType Directory -Force "$Stage/onnx" | Out-Null
# Copy-Item hf/README.md, LICENSE, NOTICE $Stage
# foreach ($f in "config.json", "keel.json", "tokenizer.json", "tokenizer_config.json", "special_tokens_map.json", "vocab.txt") {
#   if (Test-Path "$Model/$f") { Copy-Item "$Model/$f" $Stage }
# }
# Copy-Item "$Model/onnx/model_quantized.onnx" "$Stage/onnx/"
#
# 2. Sanity checks: model id, no TBD left in the card, audit clean.
# (Get-Content "$Stage/keel.json" -Raw | ConvertFrom-Json).id          # expect decider-3.0.0
# if (Select-String -Path "$Stage/README.md" -Pattern "TBD") { throw "fill the TBDs in hf/README.md" }
# node scripts/oss-audit.mjs --fail-on medium; if ($LASTEXITCODE) { throw "audit not clean" }
#
# 3. Checksums (also attach SHA256SUMS to the GitHub Release so model:fetch can verify).
# Get-ChildItem $Stage -Recurse -File | Where-Object Name -ne "SHA256SUMS" | ForEach-Object {
#   "{0}  {1}" -f (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLower(), ($_.FullName.Substring((Resolve-Path $Stage).Path.Length + 1) -replace '\\', '/')
# } | Set-Content -Encoding ascii "$Stage/SHA256SUMS"
#
# 4. Create the repo (public) and upload. Review the staging folder once more before this line.
# huggingface-cli repo create ($HfRepo.Split('/')[1]) --type model --organization ($HfRepo.Split('/')[0])
# huggingface-cli upload $HfRepo $Stage . --repo-type model --commit-message "Keel $Revision"
# huggingface-cli tag $HfRepo $Revision --repo-type model
#
# 5. Clean up the local staging copy.
# Remove-Item -Recurse -Force $Stage
