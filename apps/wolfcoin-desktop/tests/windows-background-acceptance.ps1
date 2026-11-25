# Wolf-Coin Windows acceptance: invisible, unfocusable, low-priority, fixture-only.
[CmdletBinding()]
param(
 [string]$PackageRoot = '',
 [string]$PythonExe = '',
 [string]$EvidenceDir = '',
 [int]$FixturePort = 44717,
 [switch]$PreflightOnly
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Get-ForegroundOwner {
 if (-not ('WolfQA.Foreground' -as [type])) {
  Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
namespace WolfQA {
 public static class Foreground {
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hwnd, out uint pid);
 }
}
'@
 }
 $handle=[WolfQA.Foreground]::GetForegroundWindow()
 [uint32]$pidValue=0
 [void][WolfQA.Foreground]::GetWindowThreadProcessId($handle,[ref]$pidValue)
 return [int]$pidValue
}
$game=Get-Process -Name 'sp26-cod' -ErrorAction SilentlyContinue|Select-Object -First 1
$foregroundBefore=Get-ForegroundOwner
$node=Get-Command node.exe -ErrorAction SilentlyContinue
if (-not $PythonExe) {
 $detected=@(& py.exe -3.14 -c 'import sys;print(sys.executable)' 2>$null)
 if ($LASTEXITCODE -eq 0 -and $detected.Count -gt 0) { $PythonExe=[string]$detected[-1] }
}
$pyVersion=if ($PythonExe -and (Test-Path -LiteralPath $PythonExe)) { (& $PythonExe -c 'import sys;print(sys.version)').Trim() } else { 'missing' }
$main=if ($PackageRoot) { Join-Path $PackageRoot 'resources\app\main.cjs' } else { '' }
$exe=if ($PackageRoot) { Join-Path $PackageRoot 'wolf-coin.exe' } else { '' }
$source=if ($main -and (Test-Path -LiteralPath $main)) { [IO.File]::ReadAllText($main) } else { '' }
$offscreenMarker="const BACKGROUND_QA=TEST_MODE && process.env.WOLF_BACKGROUND_QA==='1'"
$hasOffscreen=$source.Contains($offscreenMarker)
$packageReady=[bool]($exe -and (Test-Path -LiteralPath $exe) -and $hasOffscreen)
[ordered]@{
 schema='wolf.windows.background-acceptance.v1'
 game_active=[bool]$game
 game_pid=if($game){$game.Id}else{$null}
 foreground_pid=$foregroundBefore
 node_installed=[bool]$node
 python_version=$pyVersion
 package_ready=$packageReady
 offscreen_marker=$hasOffscreen
 decision=if($packageReady -and $node -and $pyVersion -ne 'missing'){'can-run-hidden'}else{'preflight-only'}
}|ConvertTo-Json -Compress
if ($PreflightOnly) { exit 0 }
if (-not $packageReady) { throw 'Package does not contain verified offscreen QA support; refusing to launch visible desktop.' }
if (-not $node -or $pyVersion -eq 'missing') { throw 'Node/Python prerequisite missing.' }
if (-not $EvidenceDir) { $EvidenceDir=Join-Path ([IO.Path]::GetTempPath()) ('wolf-windows-qa-'+[guid]::NewGuid().ToString('N')) }
New-Item -ItemType Directory -Force -Path $EvidenceDir | Out-Null
$fixtureScript=Join-Path $PSScriptRoot 'test_fixture.cjs'
if (-not (Test-Path -LiteralPath $fixtureScript)) { throw 'Fixture source missing.' }
$prior=@{}
foreach($key in @('WOLF_TEST_MODE','WOLF_BACKGROUND_QA','WOLF_TEST_USER_DATA','WOLF_TEST_FIXTURE','WOLF_TEST_STAGE','WOLF_BACKEND_PYTHON','WOLF_FIXTURE_PORT')) {
 $prior[$key]=[Environment]::GetEnvironmentVariable($key,'Process')
}
$fixtureProc=$null
try {
 $env:WOLF_TEST_MODE='1'
 $env:WOLF_BACKGROUND_QA='1'
 $env:WOLF_TEST_USER_DATA=Join-Path $EvidenceDir 'isolated-profile'
 $env:WOLF_TEST_FIXTURE='http://127.0.0.1:'+([string]$FixturePort)+'/login'
 $env:WOLF_BACKEND_PYTHON=$PythonExe
 $env:WOLF_FIXTURE_PORT=[string]$FixturePort
 $fixtureProc=Start-Process -FilePath $node.Source -ArgumentList ('"'+$fixtureScript+'"') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $EvidenceDir 'fixture.log') -RedirectStandardError (Join-Path $EvidenceDir 'fixture.err')
 $fixtureProc.PriorityClass=[Diagnostics.ProcessPriorityClass]::BelowNormal
 $results=@()
 foreach($stage in @('fresh','restore')) {
  $env:WOLF_TEST_STAGE=$stage
  $logOut=Join-Path $EvidenceDir ($stage+'.stdout.log')
  $logErr=Join-Path $EvidenceDir ($stage+'.stderr.log')
  $proc=Start-Process -FilePath $exe -ArgumentList @('--disable-gpu','--remote-debugging-port=0') -WindowStyle Hidden -PassThru -RedirectStandardOutput $logOut -RedirectStandardError $logErr
  try {
   $proc.PriorityClass=[Diagnostics.ProcessPriorityClass]::BelowNormal
   if (-not $proc.WaitForExit(65000)) { $proc.Kill();throw ('Background '+$stage+' timed out') }
   $log=if(Test-Path -LiteralPath $logOut){[IO.File]::ReadAllText($logOut)}else{''}
   $expected=if($stage -eq 'fresh'){'WOLF_NATIVE_FIXTURE_PASS'}else{'WOLF_NATIVE_RESTART_AND_REMOVE_PASS'}
   if($proc.ExitCode -ne 0 -or -not $log.Contains($expected)) { throw ('Acceptance stage '+$stage+' failed, inspect '+$logOut) }
   $results+=@{stage=$stage;marker=$expected;exit_code=$proc.ExitCode}
  }finally{
   if(-not $proc.HasExited){$proc.Kill()}
   $proc.Dispose()
  }
 }
 $foregroundAfter=Get-ForegroundOwner
 $gameAfter=Get-Process -Name 'sp26-cod' -ErrorAction SilentlyContinue|Select-Object -First 1
 if($game -and (-not $gameAfter -or $gameAfter.Id -ne $game.Id)){throw 'Game process continuity changed.'}
 if($game -and $foregroundBefore -ne $foregroundAfter){throw 'Foreground focus changed during background qualification.'}
 [ordered]@{schema='wolf.windows.background-acceptance.v1';result='PASS';stages=$results;foreground_preserved=($foregroundAfter -eq $foregroundBefore);evidence_dir=$EvidenceDir}|ConvertTo-Json -Compress -Depth 5
}finally{
 if($fixtureProc -and -not $fixtureProc.HasExited){$fixtureProc.Kill()}
 if($fixtureProc){$fixtureProc.Dispose()}
 foreach($key in $prior.Keys){[Environment]::SetEnvironmentVariable($key,$prior[$key],'Process')}
}
