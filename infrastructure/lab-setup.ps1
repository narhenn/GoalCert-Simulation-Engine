# GoalCert live-fire range — one-time setup (Windows / PowerShell).
# Builds the Kali attacker image, pulls the target images, starts the range, and smoke-tests it.
# Run this ONCE before a demo so everything is cached and starts instantly on the day.
#
#   pwsh infrastructure/lab-setup.ps1
#
param([switch]$Rebuild)

$ErrorActionPreference = "Stop"
$compose = Join-Path $PSScriptRoot "docker-compose.lab.yml"
$proj = "gclab"   # MUST match the engine's default project (app/lab/docker_lab.py)

function Step($n, $msg) { Write-Host "`n[$n] $msg" -ForegroundColor Cyan }

Step 1 "Checking Docker..."
docker version --format '{{.Server.Version}}' | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Docker is not running. Start Docker Desktop and retry." }
Write-Host "  Docker OK" -ForegroundColor Green

Step 2 "Building the Kali attacker image (first build pulls ~1GB, then it's cached)..."
if ($Rebuild) { docker compose -f $compose -p $proj build --no-cache attacker }
else { docker compose -f $compose -p $proj build attacker }

Step 3 "Pulling target images (DVWA web + Samba file server)..."
docker compose -f $compose -p $proj pull target-web target-files

Step 4 "Starting the range..."
docker compose -f $compose -p $proj up -d
Start-Sleep -Seconds 4

Step 5 "Verifying the attacker toolset..."
docker compose -f $compose -p $proj exec -T attacker sh -lc "command -v nmap && command -v nikto && command -v impacket-secretsdump && command -v ttyd && (command -v nxc || echo 'nxc: optional, not present')"

Step 6 "Smoke test — real nmap against the web target..."
docker compose -f $compose -p $proj exec -T attacker sh -lc "nmap -sV -Pn -T4 target-web | tail -n 15"

$dvwa = (docker compose -f $compose -p $proj port target-web 80) -replace '0.0.0.0','localhost'
$term = (docker compose -f $compose -p $proj port attacker 7681) -replace '0.0.0.0','localhost'
Write-Host "`nRange is up." -ForegroundColor Green
Write-Host "  DVWA in a browser:   http://$dvwa  (admin / password, then 'Create / Reset Database')"
Write-Host "  Kali shell (ttyd):   http://$term"
Write-Host "  Stop it later:       docker compose -f infrastructure/docker-compose.lab.yml -p gclab down"
Write-Host "  In GoalCert:         start a live mission, then toggle 'Live-fire' (host) and play Red."
