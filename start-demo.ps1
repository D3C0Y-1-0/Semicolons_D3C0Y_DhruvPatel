# One command for demo day: backend + frontend in their own windows, models warmed, console opened.
#   .\start-demo.ps1            laptop only
#   .\start-demo.ps1 -Tunnel    also a Cloudflare quick tunnel for phone links (QR, email); its address goes into
#                               backend\.env as PUBLIC_URL by itself. Anyone with that address reaches the API while
#                               it runs: close the tunnel window after the demo.
# If Windows blocks scripts: powershell -ExecutionPolicy Bypass -File .\start-demo.ps1 -Tunnel
param([switch]$Tunnel)
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$envFile = Join-Path $root "backend\.env"

function Set-PublicUrl($url) {
    # rewrite .env as UTF-8 without BOM, keeping every other line (Set-Content would re-encode it)
    $lines = @([IO.File]::ReadAllLines($envFile) | Where-Object { $_ -notmatch '^PUBLIC_URL=' }) + "PUBLIC_URL=$url"
    [IO.File]::WriteAllLines($envFile, $lines, (New-Object Text.UTF8Encoding $false))
}

function Wait-Url($url, $seconds) {
    for ($i = 0; $i -lt $seconds; $i += 2) {
        try { return Invoke-RestMethod $url -TimeoutSec 3 } catch { Start-Sleep 2 }
    }
    return $null
}

if (Wait-Url "http://localhost:8000/health" 2) {
    Write-Host "A backend is already running on port 8000; using it." -ForegroundColor Yellow
} else {
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\backend'; `$host.UI.RawUI.WindowTitle = 'TrustCheck backend'; .\.venv\Scripts\uvicorn.exe app:app --port 8000"
}
try { Invoke-WebRequest "http://localhost:5173" -UseBasicParsing -TimeoutSec 2 | Out-Null; Write-Host "Frontend already running on 5173." -ForegroundColor Yellow }
catch { Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\frontend'; `$host.UI.RawUI.WindowTitle = 'TrustCheck frontend'; npm run dev -- --port 5173" }

if ($Tunnel) {
    $cf = Join-Path $HOME "cloudflared.exe"
    if (-not (Test-Path $cf)) { throw "cloudflared.exe not found in $HOME. Download cloudflared-windows-amd64.exe from https://github.com/cloudflare/cloudflared/releases/latest and save it there as cloudflared.exe." }
    $log = Join-Path $env:TEMP "trustcheck-tunnel.log"
    Remove-Item $log -ErrorAction SilentlyContinue
    # IPv4 + HTTP/2: campus Wi-Fi and phone hotspots often break cloudflared's default IPv6/QUIC
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$host.UI.RawUI.WindowTitle = 'TrustCheck tunnel (close after the demo)'; & '$cf' tunnel --edge-ip-version 4 --protocol http2 --logfile '$log' --url http://127.0.0.1:8000"
    $url = $null
    for ($i = 0; $i -lt 45 -and -not $url; $i++) {
        Start-Sleep 1
        if (Test-Path $log) { $m = Select-String -Path $log -Pattern 'https://[a-z0-9-]+\.trycloudflare\.com' | Select-Object -First 1; if ($m) { $url = $m.Matches[0].Value } }
    }
    if ($url) { Set-PublicUrl $url; Write-Host "Phone links now use $url" -ForegroundColor Green }
    else { Write-Host "No tunnel address after 45 s. Check the tunnel window; QR and email links won't open on phones until it works." -ForegroundColor Red }
}

Write-Host "Waiting for the backend and its models (about 1.5 min after a fresh start)..."
$h = Wait-Url "http://localhost:8000/health" 60
if (-not $h) { throw "Backend didn't answer on port 8000. Check the 'TrustCheck backend' window." }
for ($i = 0; $i -lt 150 -and $h.models -ne "ready"; $i += 3) { Start-Sleep 3; $h = Wait-Url "http://localhost:8000/health" 3 }
$state = @("models: $($h.models)", "email: $(if ($h.email) {'on'} else {'off'})", "telegram: $(if ($h.telegram) {'on'} else {'off'})", "phone links: $($h.public_url)")
Write-Host ("TrustCheck ready. " + ($state -join ", ")) -ForegroundColor Green
Start-Process "http://localhost:5173/#/app/check"
