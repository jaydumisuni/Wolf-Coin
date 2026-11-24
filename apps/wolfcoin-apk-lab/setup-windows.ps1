# PowerShell Windows 10/11. Requires Android SDK command-line tools and Node.js 22+.
# Windows Hypervisor Platform / WHPX should be enabled by the owner ahead of time.
param(
  [string]$SdkRoot = "$env:LOCALAPPDATA\Android\Sdk",
  [string]$AvdName = "wolfcoin_api35_lab",
  [string]$Serial = "emulator-5554",
  [Parameter(Mandatory=$true)][string]$Apk,
  [string]$EvidenceDir = "$PSScriptRoot\evidence"
)
$ErrorActionPreference = "Stop"
$SdkManager = Join-Path $SdkRoot "cmdline-tools\latest\bin\sdkmanager.bat"
$AvdManager = Join-Path $SdkRoot "cmdline-tools\latest\bin\avdmanager.bat"
$Emulator = Join-Path $SdkRoot "emulator\emulator.exe"
$Adb = Join-Path $SdkRoot "platform-tools\adb.exe"
if (!(Test-Path $SdkManager) -or !(Test-Path $AvdManager)) {
  throw "Android SDK command-line tools not found. Install first; this script does not modify Windows optional features."
}
if (!(Get-Command node -ErrorAction SilentlyContinue)) { throw "Node.js 22+ is required for the portable APK proof runner." }
if (!(Test-Path $Apk)) { throw "APK not found: $Apk" }
$env:ANDROID_SDK_ROOT = $SdkRoot
& $SdkManager "--sdk_root=$SdkRoot" "platform-tools" "emulator" "platforms;android-35" "system-images;android-35;default;x86_64"
if ($LASTEXITCODE -ne 0) { throw "Android SDK package preparation failed." }
$KnownAvds = (& $AvdManager list avd | Out-String)
if ($KnownAvds -notmatch [regex]::Escape($AvdName)) {
  "no" | & $AvdManager create avd --name $AvdName --package "system-images;android-35;default;x86_64" --device "pixel_2"
  if ($LASTEXITCODE -ne 0) { throw "AVD creation failed." }
}
# Do not change Windows hypervisor configuration, power state or unrelated applications.
$EmulatorArgs = @("-avd",$AvdName,"-no-snapshot","-no-audio","-no-boot-anim","-gpu","swiftshader_indirect","-memory","2048","-cores","2")
Start-Process -FilePath $Emulator -ArgumentList $EmulatorArgs | Out-Null
& $Adb -s $Serial wait-for-device
$Boot = ""
for ($i=0; $i -lt 300; $i++) {
  $Boot = (& $Adb -s $Serial shell getprop sys.boot_completed | Out-String).Trim()
  if ($Boot -eq "1") { break }
  Start-Sleep -Milliseconds 500
}
if ($Boot -ne "1") { throw "Android emulator did not reach boot complete." }
node "$PSScriptRoot\verify-apk.mjs" --apk (Resolve-Path $Apk).Path --serial $Serial --adb $Adb --port 9224 --evidence $EvidenceDir
if ($LASTEXITCODE -ne 0) { throw "APK proof checks failed." }
Write-Output "Wolf-Coin APK lab proof stored in $EvidenceDir"
