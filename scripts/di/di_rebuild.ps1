$ErrorActionPreference = "Continue"
$env:HF_HUB_DISABLE_XET = "1"
$env:DI_SKIP_BENCHMARKS = "45"
$env:DI_ALLOW_PARTIAL = "1"
$env:GIT_CONFIG_COUNT = "1"; $env:GIT_CONFIG_KEY_0 = "core.autocrlf"; $env:GIT_CONFIG_VALUE_0 = "false"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
Set-Location C:\KeelWork
& C:\KeelWork\decision-index\.venv\Scripts\python.exe -u -m decision_index suite rebuild --work C:\KeelWork\di-work *> C:\KeelWork\logs\di-rebuild.log
"EXIT $LASTEXITCODE" | Out-File -Append C:\KeelWork\logs\di-rebuild.log
