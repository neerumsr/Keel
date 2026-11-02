# Upload Keel-Pro to the Hugging Face Hub.
#
# Creates two repos, PRIVATE by default (pass -Public to create them public; repos that already exist keep their
# visibility):
#   neerumsr/keel-pro       model card, LoRA adapter, tokenizer, keel-pro.json, LICENSE, NOTICE, SHA256SUMS
#   neerumsr/keel-pro-GGUF  GGUF card, Q8_0 and Q4_K_M, LICENSE, NOTICE, SHA256SUMS
# See hf/keel-pro/FILES.md for what is (and is not) uploaded.
#
# Prerequisites: pip install -U huggingface_hub; hf auth login (write token; never commit or paste it anywhere).
# Run from the repo root: pwsh hf/keel-pro/upload.ps1 [-Run <dir>] [-Base <dir>] [-Gguf <dir>] [-Public] [-SkipGguf]
param(
  [string]$HfRepo = "neerumsr/keel-pro",
  [string]$HfGguf = "neerumsr/keel-pro-GGUF",
  [string]$Run = "C:/KeelWork/pro/runs/soup78",      # adapter in $Run/soup (it7+it8 average)
  [string]$Base = "C:/KeelWork/models/Qwen3.5-27B",
  [string]$Gguf = "C:/KeelWork/gguf",
  [string]$Revision = "v1.0.0",
  [string]$Stage = "hf/_stage-pro",
  [switch]$Public,
  [switch]$SkipGguf
)
$ErrorActionPreference = "Stop"
$vis = if ($Public) { "--public" } else { "--private" }

function Write-Sums($dir) {
  Get-ChildItem $dir -File | Where-Object Name -ne "SHA256SUMS" | Sort-Object Name | ForEach-Object {
    "{0}  {1}" -f (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLower(), $_.Name
  } | Set-Content -Encoding ascii (Join-Path $dir "SHA256SUMS")
}
function Invoke-Hf { & hf @args; if ($LASTEXITCODE) { throw "hf $($args -join ' ') failed" } }
function Add-Tag($repo, $msg) { & hf repos tag create $repo $Revision --repo-type model -m $msg; if ($LASTEXITCODE) { Write-Warning "tag $Revision not created on $repo (already there?)" } }

# Checks
foreach ($card in "artifacts/parity/pro/MODEL_CARD.md", "hf/keel-pro/GGUF_CARD.md") {
  if (Select-String -Path $card -Pattern "TBD" -Quiet) { throw "fill the TBDs in $card" }
}
node scripts/oss-audit.mjs --fail-on medium; if ($LASTEXITCODE) { throw "audit not clean" }

# 1. Adapter repo
Remove-Item -Recurse -Force $Stage -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $Stage | Out-Null
Copy-Item artifacts/parity/pro/MODEL_CARD.md "$Stage/README.md"
Copy-Item LICENSE, hf/keel-pro/NOTICE $Stage
Copy-Item "$Run/soup/adapter_config.json", "$Run/soup/adapter_model.safetensors", "$Run/keel-pro.json" $Stage
foreach ($f in "tokenizer.json", "tokenizer_config.json", "chat_template.jinja") { if (Test-Path "$Base/$f") { Copy-Item "$Base/$f" $Stage } }
Write-Sums $Stage
Invoke-Hf repos create $HfRepo --repo-type model $vis --exist-ok
Invoke-Hf upload $HfRepo $Stage . --repo-type model --commit-message "Keel-Pro $Revision"
Add-Tag $HfRepo "Keel-Pro $Revision (soup78, DI public 0.3 = 62.73)"

# 2. GGUF repo (large files; if interrupted, rerun the script: unchanged files are skipped)
if (-not $SkipGguf) {
  $g = "$Stage-gguf"
  Remove-Item -Recurse -Force $g -ErrorAction SilentlyContinue
  New-Item -ItemType Directory -Force $g | Out-Null
  Copy-Item hf/keel-pro/GGUF_CARD.md "$g/README.md"
  Copy-Item LICENSE, hf/keel-pro/NOTICE $g
  foreach ($q in "Q8_0", "Q4_K_M") {
    # hard link, not a copy (same volume); falls back to a copy
    $dst = "$g/keel-pro-$q.gguf"
    try { New-Item -ItemType HardLink -Path $dst -Target (Resolve-Path "$Gguf/keel-pro-27b-$q.gguf") | Out-Null } catch { Copy-Item "$Gguf/keel-pro-27b-$q.gguf" $dst }
  }
  Write-Sums $g
  Invoke-Hf repos create $HfGguf --repo-type model $vis --exist-ok
  Invoke-Hf upload $HfGguf $g . --repo-type model --commit-message "Keel-Pro $Revision GGUF"
  Add-Tag $HfGguf "Keel-Pro $Revision GGUF"
  Remove-Item -Recurse -Force $g
}

Remove-Item -Recurse -Force $Stage
"done: https://huggingface.co/$HfRepo" + $(if (-not $SkipGguf) { " and https://huggingface.co/$HfGguf" })
