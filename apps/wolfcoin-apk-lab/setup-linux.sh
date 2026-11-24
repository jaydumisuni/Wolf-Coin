#!/usr/bin/env bash
set -euo pipefail
# Native Linux Android emulator using KVM where available; no Docker.
if [ "$#" -lt 1 ];then echo "Usage: setup-linux.sh /path/app-debug.apk [android-serial]" >&2;exit 2;fi
SDK="$(printenv ANDROID_SDK_ROOT || printenv ANDROID_HOME || printf '%s/Android/Sdk' "$HOME")"
AVD="$(printenv WOLF_AVD_NAME || printf 'wolfcoin_api35_lab')"
APK="$1"
SERIAL=emulator-5554
if [ "$#" -ge 2 ];then SERIAL="$2";fi
LAB="$(printenv WOLF_ANDROID_LAB || printf '%s/.cache/wolfcoin-apk-lab' "$HOME")"
mkdir -p "$LAB"
"$SDK/cmdline-tools/latest/bin/sdkmanager" --sdk_root="$SDK" \
  "platform-tools" "emulator" "platforms;android-35" "system-images;android-35;default;x86_64"
if ! "$SDK/cmdline-tools/latest/bin/avdmanager" list avd | grep -Fq "$AVD"; then
  printf 'no\n' | "$SDK/cmdline-tools/latest/bin/avdmanager" create avd \
    -n "$AVD" -k 'system-images;android-35;default;x86_64' --device pixel_2
fi
"$SDK/emulator/emulator" -avd "$AVD" -no-window -no-audio -no-snapshot -gpu swiftshader_indirect -memory 2048 -cores 2 >"$LAB/emulator.log" 2>&1 &
EMU_PID=$!
echo "Android emulator PID $EMU_PID (only this new emulator is used by this harness)"
"$SDK/platform-tools/adb" -s "$SERIAL" wait-for-device
for i in $(seq 1 300); do
 if [ "$("$SDK/platform-tools/adb" -s "$SERIAL" shell getprop sys.boot_completed | tr -d '\r')" = "1" ];then break;fi
 sleep 0.5
done
ANDROID_SDK_ROOT="$SDK" node "$(dirname "$0")/verify-apk.mjs" --apk "$APK" --serial "$SERIAL" --port 9224 --evidence "$LAB/evidence"
