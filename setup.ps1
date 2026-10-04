$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) { python -m venv .venv }
& '.\.venv\Scripts\python.exe' -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
New-Item -ItemType Directory -Path 'outputs\assets' -Force | Out-Null
$modelFile = Join-Path $PSScriptRoot 'outputs\assets\hand_landmarker.task'
if (-not (Test-Path -LiteralPath $modelFile)) {
    Invoke-WebRequest -Uri 'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task' -OutFile $modelFile
}
$modelHash = (Get-FileHash -LiteralPath $modelFile -Algorithm SHA256).Hash.ToLowerInvariant()
if ($modelHash -ne 'fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1') { throw 'Hand landmark model hash mismatch' }
Write-Output 'Setup complete. Collect your own landmarks and train the gesture classifier before starting the live demo.'
