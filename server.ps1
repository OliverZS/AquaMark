# AquaMark loopback server
# Serves this folder on 127.0.0.1:<port> so the page runs from a secure
# origin, which is what unlocks the File System Access API (real save).
# Raw TcpListener on loopback: no HttpListener, therefore no netsh URL
# reservation and no administrator rights needed.
# ASCII-only: Chinese text is kept out of PowerShell console output.
#
# Lifecycle: this server shuts ITSELF down once the page stops answering
# the heartbeat (default 45s idle). The launcher therefore never has to
# guess when the browser closed - that was the old fragile design.
param(
  [int]$Port = 8731,
  [string]$Root = (Split-Path -Parent $MyInvocation.MyCommand.Path),
  [int]$IdleSeconds = 45
)

$ErrorActionPreference = 'Stop'
$readyFile = Join-Path $Root '.server.ready'
$pidFile   = Join-Path $Root '.server.pid'
Remove-Item $readyFile -ErrorAction SilentlyContinue
Remove-Item $pidFile   -ErrorAction SilentlyContinue

# ---------------- bind the first free port ----------------
$listener = $null
$bound    = 0
foreach ($p in @($Port, $Port + 1, $Port + 2, $Port + 3, $Port + 4, $Port + 5,
                 $Port + 6, $Port + 7, $Port + 8, $Port + 9, $Port + 10)) {
  try {
    $candidate = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, $p)
    $candidate.Start()
    $listener = $candidate
    $bound    = $p
    break
  } catch {
    # port busy or blocked - try the next one
  }
}
if ($bound -eq 0) { exit 3 }

$rootFull = [IO.Path]::GetFullPath($Root)
[IO.File]::WriteAllText($pidFile,   [string]$PID)
[IO.File]::WriteAllText($readyFile, [string]$bound)

$mime = @{
  '.html' = 'text/html; charset=utf-8'
  '.htm'  = 'text/html; charset=utf-8'
  '.md'   = 'text/markdown; charset=utf-8'
  '.css'  = 'text/css; charset=utf-8'
  '.js'   = 'text/javascript; charset=utf-8'
  '.png'  = 'image/png'
  '.jpg'  = 'image/jpeg'
  '.svg'  = 'image/svg+xml'
  '.ico'  = 'image/x-icon'
  '.txt'  = 'text/plain; charset=utf-8'
  '.json' = 'application/json; charset=utf-8'
}

# Injected into every HTML page so the server knows the editor is still open.
$heartbeat = '<script>(function(){function p(u){try{var x=new XMLHttpRequest();x.open("GET",u,true);x.send();}catch(e){}}setInterval(function(){p("/__hb?t="+Date.now());},8000);p("/__hb?t=0");window.addEventListener("pagehide",function(){p("/__bye");});})();</script>'

function Send-Response($stream, $code, $bytes, $ctype) {
  $head = "HTTP/1.1 $code`r`nContent-Type: $ctype`r`nContent-Length: $($bytes.Length)`r`nCache-Control: no-store`r`nConnection: close`r`n`r`n"
  $hb = [Text.Encoding]::ASCII.GetBytes($head)
  $stream.Write($hb, 0, $hb.Length)
  if ($bytes.Length -gt 0) { $stream.Write($bytes, 0, $bytes.Length) }
  $stream.Flush()
}

$script:bye = $false

function Handle-Client($client) {
  $stream = $null
  try {
    $stream = $client.GetStream()
    $stream.ReadTimeout = 5000
    $req = ''
    $buf = New-Object byte[] 4096
    while ($true) {
      $n = $stream.Read($buf, 0, 4096)
      if ($n -le 0) { break }
      $req += [Text.Encoding]::ASCII.GetString($buf, 0, $n)
      if ($req -match "`r`n`r`n") { break }
      if ($req.Length -gt 65536) { break }
    }
    if ($req.Length -lt 5) { return }

    $line  = ($req -split "`r?`n")[0]
    $parts = $line.Split(' ')
    if ($parts.Length -lt 2) { return }
    $target = [Uri]::UnescapeDataString(($parts[1] -split '\?')[0])

    # ---- keepalive / goodbye ----
    if ($target -eq '/__hb') {
      Send-Response $stream '200 OK' ([Text.Encoding]::ASCII.GetBytes('ok')) 'text/plain'
      return
    }
    if ($target -eq '/__bye') {
      Send-Response $stream '200 OK' ([Text.Encoding]::ASCII.GetBytes('bye')) 'text/plain'
      $script:bye = $true
      return
    }

    if ($target -eq '/' -or $target -eq '') { $target = '/AquaMark.html' }
    $rel  = $target.TrimStart('/').Replace('/', '\')
    $full = [IO.Path]::GetFullPath((Join-Path $rootFull $rel))

    if (-not $full.StartsWith($rootFull, [StringComparison]::OrdinalIgnoreCase)) {
      Send-Response $stream '403 Forbidden' ([Text.Encoding]::UTF8.GetBytes('403')) 'text/plain'
      return
    }

    if (-not (Test-Path $full -PathType Leaf)) {
      Send-Response $stream '404 Not Found' ([Text.Encoding]::UTF8.GetBytes('404')) 'text/plain'
      return
    }

    $ext = [IO.Path]::GetExtension($full).ToLowerInvariant()
    if ($mime.ContainsKey($ext)) { $ctype = $mime[$ext] } else { $ctype = 'application/octet-stream' }

    if ($ext -eq '.html' -or $ext -eq '.htm') {
      $text = [IO.File]::ReadAllText($full, [Text.Encoding]::UTF8)
      $idx  = $text.LastIndexOf('</body>')
      if ($idx -ge 0) { $text = $text.Insert($idx, $heartbeat) } else { $text += $heartbeat }
      Send-Response $stream '200 OK' ([Text.Encoding]::UTF8.GetBytes($text)) $ctype
    } else {
      Send-Response $stream '200 OK' ([IO.File]::ReadAllBytes($full)) $ctype
    }
  } catch {
    # keep serving even if one request misbehaves
  } finally {
    if ($stream -ne $null) { try { $stream.Dispose() } catch {} }
    try { $client.Close() } catch {}
  }
}

$last = Get-Date
try {
  while ($true) {
    if ($listener.Pending()) {
      $c = $null
      try {
        $c = $listener.AcceptTcpClient()
        Handle-Client $c
      } catch {
        # ignore
      } finally {
        if ($c -ne $null) { try { $c.Close() } catch {} }
      }
      $last = Get-Date
      continue
    }

    Start-Sleep -Milliseconds 250

    # page closed -> leave after a short grace period
    if ($script:bye) {
      Start-Sleep -Seconds 3
      break
    }
    if (((Get-Date) - $last).TotalSeconds -gt $IdleSeconds) { break }
  }
} finally {
  $listener.Stop()
  Remove-Item $readyFile -ErrorAction SilentlyContinue
  Remove-Item $pidFile   -ErrorAction SilentlyContinue
}
