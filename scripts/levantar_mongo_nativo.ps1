param(
    [int]$Port = 27017
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$MongoExe = "C:\Program Files\MongoDB\Server\6.0\bin\mongod.exe"
$DbPath = Join-Path $Root "tmp\mongo-local-db"
$LogDir = Join-Path $Root "tmp\mongo-local-log"
$LogPath = Join-Path $LogDir "mongod.log"

if (-not (Test-Path $MongoExe)) {
    throw "No se encontro mongod.exe en $MongoExe"
}

New-Item -ItemType Directory -Force -Path $DbPath, $LogDir | Out-Null

$listener = Test-NetConnection 127.0.0.1 -Port $Port -WarningAction SilentlyContinue
if ($listener.TcpTestSucceeded) {
    Write-Host "MongoDB ya esta escuchando en localhost:$Port"
    exit 0
}

Start-Process `
    -FilePath $MongoExe `
    -ArgumentList @(
        "--dbpath", $DbPath,
        "--port", "$Port",
        "--bind_ip", "127.0.0.1",
        "--logpath", $LogPath,
        "--logappend"
    ) `
    -WorkingDirectory $Root `
    -WindowStyle Hidden

Start-Sleep -Seconds 5

$ok = Test-NetConnection 127.0.0.1 -Port $Port -WarningAction SilentlyContinue
if (-not $ok.TcpTestSucceeded) {
    throw "MongoDB no inicio en localhost:$Port. Revisar log: $LogPath"
}

Write-Host "MongoDB local iniciado en localhost:$Port"
Write-Host "Datos: $DbPath"
Write-Host "Log: $LogPath"
