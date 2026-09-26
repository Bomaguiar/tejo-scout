$ErrorActionPreference = 'Stop'
$previewUrl = 'http://127.0.0.1:8765/'
$available = $false
try { $response = Invoke-WebRequest $previewUrl -UseBasicParsing -TimeoutSec 2; $available = $response.Content -match 'Tejo Scout' } catch {}
if (-not $available) {
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) { Start-Process (Join-Path $PSScriptRoot 'index.html'); exit }
    $arguments = @('-m','http.server','8765','--bind','127.0.0.1','--directory',('"' + $PSScriptRoot + '"'))
    Start-Process -FilePath python -ArgumentList $arguments -WindowStyle Hidden | Out-Null
    Start-Sleep -Seconds 1
}
Start-Process $previewUrl

