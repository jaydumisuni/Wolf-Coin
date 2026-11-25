# Verify owner-only NSIS with NO visible Wolf-Coin windows or game interaction.
[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$InstallerPath,
  [string]$ExpectedSha256='6fada8d002ed3512c7c037a7daf8e2c399dd8b0b23701058b790057ef5ef9de1',
  [string]$Root=(Join-Path $env:TEMP 'TTG-Wolf-Installer-Acceptance'),
  [switch]$PreflightOnly
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$manifest='HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\Wolf-Coin'
$installed=Join-Path $Root 'installed'
$profile=Join-Path $Root 'isolated-runtime\isolated-profile'
$setup=Resolve-Path -LiteralPath $InstallerPath
if ($null -ne (Get-ItemProperty $manifest -ErrorAction SilentlyContinue)) {
  throw 'A Wolf-Coin installation already exists. Refusing to overwrite.'
}
if(Test-Path -LiteralPath $installed){throw 'Isolated installation already exists.'}
$hash=(Get-FileHash -LiteralPath $setup -Algorithm SHA256).Hash.ToLowerInvariant()
if($hash -ne $ExpectedSha256.ToLowerInvariant()){throw "Installer SHA-256 differs: $hash"}
$report=[ordered]@{schema='wolf.windows.nsis.v1';installer_sha256=$hash;root=$Root;silent=$true}
if($PreflightOnly){$report.result='PREFLIGHT_PASS';$report|ConvertTo-Json -Compress;exit 0}
New-Item -ItemType Directory -Path $Root -Force | Out-Null
$installedOk=$false
$errorThrown=$null
try {
  $p=Start-Process -FilePath $setup -ArgumentList ('/S /D='+$installed) -WindowStyle Hidden -Wait -PassThru
  if($null -ne $p.ExitCode -and $p.ExitCode -ne 0){throw "Silent NSIS install exited $($p.ExitCode)"}
  $exe=Join-Path $installed 'Wolf-Coin.exe'
  $python=Join-Path $installed 'resources\python\python.exe'
  $main=Join-Path $installed 'resources\app\main.cjs'
  if(!(Test-Path $exe) -or !(Test-Path $python) -or !(Test-Path $main)){
    throw 'NSIS installation missing application, embedded Python or native host.'
  }
  $reg=Get-ItemProperty $manifest -ErrorAction Stop
  if($reg.InstallLocation -ne $installed){throw 'Uninstall registry location mismatch.'}
  if(-not ([IO.File]::ReadAllText($main)).Contains("const BACKGROUND_QA=TEST_MODE && process.env.WOLF_BACKGROUND_QA==='1'")){
    throw 'App lacks unfocusable acceptance mode; refusing visible launch.'
  }
  $harness=Join-Path $PSScriptRoot 'windows-background-acceptance.ps1'
  if(!(Test-Path $harness)){throw 'Native background harness missing.'}
  $result=@(& $harness -PackageRoot $installed -EvidenceDir (Join-Path $Root 'isolated-runtime') -FixturePort 44717)
  if(-not $result -or ($result[-1]|ConvertFrom-Json).result -ne 'PASS'){
    throw 'Packaged runtime failed hidden fresh/restore acceptance.'
  }
  $report.runtime=($result[-1]|ConvertFrom-Json)
  $installedOk=$true
} catch {
  $errorThrown=$_
} finally {
  $uninstaller=Join-Path $installed 'Uninstall.exe'
  if(Test-Path $uninstaller){
    $up=Start-Process -FilePath $uninstaller -ArgumentList '/S' -WindowStyle Hidden -Wait -PassThru
    if($null -ne $up.ExitCode -and $up.ExitCode -ne 0){$report.uninstall_exit_code=$up.ExitCode}
  }
  for($i=0;$i -lt 12 -and (Test-Path $installed);$i++){Start-Sleep -Milliseconds 300}
  $report.installation_removed=!(Test-Path $installed)
  $report.registry_removed=!(Test-Path $manifest)
  $report.profile_preserved=Test-Path $profile
}
if($errorThrown){throw $errorThrown}
if(-not $installedOk -or -not $report.installation_removed -or -not $report.registry_removed -or -not $report.profile_preserved){
  throw 'Installation, registry or isolated profile failed cleanup acceptance.'
}
$report.result='PASS'
$report|ConvertTo-Json -Compress -Depth 7
