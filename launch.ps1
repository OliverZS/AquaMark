# AquaMark launcher
# Starts the loopback server (unless -NoServer), then opens Edge/Chrome in
# app-window mode on http://127.0.0.1:<port>/AquaMark.html .
# The server shuts itself down on idle, so this script does NOT wait for the
# browser and does NOT kill anything - no race, no premature shutdown.
param([switch]$NoServer)

$root    = Split-Path -Parent $MyInvocation.MyCommand.Path
$readyF  = Join-Path $root '.server.ready'
$pidF    = Join-Path $root '.server.pid'
$store   = Join-Path $env:LOCALAPPDATA 'AquaMark'
$profile = Join-Path $store 'Profile'

$url     = ''
$browser = $null

# ---------------- profile dir ----------------
try {
  foreach ($d in @($store, $profile)) {
    if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null }
  }
} catch { }

# ---------------- find a Chromium browser ----------------
try {
  $bases = @()
  foreach ($n in 'ProgramFiles', 'ProgramFiles(x86)', 'LOCALAPPDATA') {
    $v = [Environment]::GetEnvironmentVariable($n)
    if ($v -and (Test-Path $v)) { $bases += $v }
  }
  foreach ($b in $bases) {
    foreach ($r in 'Microsoft\Edge\Application\msedge.exe', 'Google\Chrome\Application\chrome.exe') {
      $p = Join-Path $b $r
      if (Test-Path $p) { $browser = $p; break }
    }
    if ($browser) { break }
  }
} catch { }

$psExe = Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\powershell.exe'
if (-not (Test-Path $psExe)) { $psExe = 'powershell.exe' }

# ---------------- start the loopback server ----------------
if (-not $NoServer) {
  try {
    Remove-Item $readyF, $pidF -ErrorAction SilentlyContinue
    Start-Process -FilePath $psExe -WindowStyle Minimized -ArgumentList @(
      '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
      (Join-Path $root 'server.ps1'), '-Port', '8731', '-Root', $root
    ) | Out-Null

    $port = 0
    for ($i = 0; $i -lt 60; $i++) {
      Start-Sleep -Milliseconds 250
      if (Test-Path $readyF) {
        $v = (Get-Content $readyF -ErrorAction SilentlyContinue | Select-Object -First 1)
        if ($v -and $v -match '^\d+$') { $port = [int]$v; break }
      }
    }

    if ($port -gt 0) {
      $ok = $false
      try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $tcp.Connect('127.0.0.1', $port)
        $tcp.Close()
        $ok = $true
      } catch { $ok = $false }
      if ($ok) { $url = "http://127.0.0.1:$port/AquaMark.html" }
    }
  } catch { }
}

# ---------------- fallback: plain file:// ----------------
if ($url -eq '') {
  Write-Output '[AquaMark] Loopback server unavailable - opening the file directly.'
  Write-Output '[AquaMark] Ctrl+S will then save a copy instead of overwriting the file.'
  $url = Join-Path $root 'AquaMark.html'
}

# ---------------- open the browser ----------------
if ($browser) {
  # --no-proxy-server matters: with a system/VPN proxy active, Edge would
  # otherwise try to fetch 127.0.0.1 through the proxy and fail.
  Start-Process -FilePath $browser -ArgumentList @(
    "--app=$url",
    "--user-data-dir=$profile",
    '--no-first-run',
    '--no-default-browser-check',
    '--no-proxy-server',
    '--disable-features=Translate',
    '--window-size=1440,900'
  ) | Out-Null
  exit 0
}

Start-Process -FilePath $url | Out-Null
exit 0
