# KazeB local development server starter
#
# Starts Django (port 8000) and the Vite React dev server (port 5173)
# in separate PowerShell windows, then prints the local preview URLs.
#
# Usage:
#   .\start-dev.ps1
#
# Prerequisites (run once):
#   .\venv\Scripts\Activate.ps1   (if not already activated)
#   cd frontend && npm install
#   python manage.py migrate
#   python manage.py seed_categories
#   python manage.py vendor_assets
#
# After starting:
#   Computer preview:   http://localhost:5173/
#   Phone / LAN preview: http://<your-computer-ip>:5173/   (same Wi-Fi)
#   Mobile preview:     open http://localhost:5173/ in your browser,
#                       press F12 -> device toolbar (Ctrl+Shift+M),
#                       pick a phone/tablet size and refresh.
#   Django admin:       http://localhost:8000/admin/
#
# Press Ctrl+C in each service window to stop. Closing this window does
# not stop the services (they run in their own windows).

$ErrorActionPreference = "Stop"

$root = Resolve-Path "."
$venvPython = Join-Path $root ".venv\Scripts\python.exe"
$frontendDir = Join-Path $root "frontend"

# ---- Detect the computer's LAN IPv4 address (first non-127 match) ----
$lanIP = $null
foreach ($line in ipconfig) {
    if ($line -match "IPv4.*:\s*([\d.]+)") {
        $candidate = $matches[1]
        if ($candidate -ne "127.0.0.1") {
            $lanIP = $candidate
            break
        }
    }
}
if (-not $lanIP) { $lanIP = "127.0.0.1" }

# ---- Give Django the CSRF-trusted LAN origins so phone POSTs (login,
# language switch, etc.) work over the LAN. ----
$env:DJANGO_CSRF_TRUSTED_ORIGINS = "http://$lanIP:5173,http://$lanIP:8000,http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000,http://127.0.0.1:8000"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  KazeB Local Development Server" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Computer preview:   http://localhost:5173/" -ForegroundColor Green
Write-Host "  Phone / LAN preview: http://$lanIP:5173/" -ForegroundColor Green
Write-Host "  Django admin:       http://localhost:8000/admin/" -ForegroundColor Green
Write-Host ""
Write-Host "  Mobile/desktop preview:" -ForegroundColor Yellow
Write-Host "    Open http://localhost:5173/ in your browser." -ForegroundColor Yellow
Write-Host "    Press F12 -> device toolbar (Ctrl+Shift+M)." -ForegroundColor Yellow
Write-Host "    Choose a phone/tablet width and refresh." -ForegroundColor Yellow
Write-Host ""
Write-Host "  Phone preview: open the LAN URL above on your phone (same Wi-Fi)." -ForegroundColor Yellow
Write-Host ""
Write-Host "  Both services start in separate windows below." -ForegroundColor Yellow
Write-Host "  Press Ctrl+C in each window to stop the services." -ForegroundColor Red
Write-Host ""

# ---- Launch Django dev server bound to all interfaces (LAN reachable) ----
Start-Process powershell.exe `
    -ArgumentList "-NoExit", "-Command", "cd `'$root`'; & `'$venvPython`' manage.py runserver 0.0.0.0:8000" `
    -WindowStyle Normal

# ---- Launch Vite React dev server (proxies API/static to Django) ----
Start-Process powershell.exe `
    -ArgumentList "-NoExit", "-Command", "cd `'$frontendDir`'; npm run dev" `
    -WindowStyle Normal

Write-Host "Django and Vite have been launched in separate windows." -ForegroundColor Green
Write-Host "You can close this window; the services keep running in theirs." -ForegroundColor Green
