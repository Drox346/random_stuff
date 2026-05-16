# TB350FU LineageOS GSI install guide

This guide documents the process used to install a LineageOS GSI on the Lenovo TB350FU. It is written as a repeatable workflow rather than a session log.

## Assumptions

- Device: Lenovo TB350FU / Tab P11 Gen 2 Wi-Fi.
- Host has `adb`, `fastboot`, `wget`, `gzip`, `sha256sum`, `file`, and `unzip`.
- Bootloader can be unlocked.
- USB debugging can be enabled in stock Android.
- Work directory is the project folder, with install files under `android-rom-work/`.

Do not relock the bootloader while this GSI is installed. Relock only after restoring stock firmware, or if a device-specific ROM guide explicitly supports relocking with a valid AVB key.

## 0. Prepare the tablet before installing the GSI

In the original install, these prep steps had already been done before the documented GSI work started. The tablet was already unlocked and sitting in fastboot/fastbootd.

Back up anything important first. Unlocking the bootloader wipes the tablet.

On stock Android:

1. Complete first setup if needed.
2. Open Settings.
3. Go to About tablet.
4. Tap Build number several times to enable Developer options.
5. Open Developer options.
6. Enable OEM unlocking.
7. Enable USB debugging.
8. Connect USB and accept the debugging prompt.

Check ADB:

```bash
adb devices -l
```

Reboot to bootloader:

```bash
adb reboot bootloader
```

If Android is not bootable, use the tablet's hardware button path to reach recovery/bootloader mode, then choose the fastboot option if shown.

Check fastboot:

```bash
fastboot devices -l
fastboot getvar product
fastboot getvar unlocked
```

Unlock the bootloader if it is still locked:

```bash
fastboot flashing unlock
```

Confirm the unlock on the tablet screen, then check again:

```bash
fastboot getvar unlocked
```

Enter userspace fastbootd if needed:

```bash
fastboot reboot fastboot
fastboot devices -l
fastboot getvar is-userspace
```

Why: the GSI install requires an unlocked bootloader, and dynamic partitions such as `system` are flashed from fastbootd.

## 1. Create a work directory

```bash
mkdir -p android-rom-work
```

Why: keep the GSI, rollback firmware, helper images, and notes in one place.

## 2. Confirm the device in fastboot

Boot the tablet into fastboot/fastbootd, then run:

```bash
fastboot devices -l
fastboot getvar product
fastboot getvar unlocked
fastboot getvar current-slot
fastboot getvar slot-count
fastboot getvar is-userspace
fastboot getvar has-slot:system
fastboot getvar all
```

Why: confirm the exact device, bootloader state, active slot, Treble support, ABI, and dynamic partition layout before choosing an image.

For this tablet, the important compatibility traits are:

- Product: `TB350FU`
- ABI: `arm64-v8a`
- A/B slots
- Treble enabled
- Dynamic partitions
- Unlocked bootloader

## 3. Choose the GSI

Use the vanilla no-root A/B arm64 LineageOS 21 GSI:

```text
lineage-21.0-20260507-UNOFFICIAL-arm64_bvN.img.gz
```

Why: `arm64_bvN` matches the tablet architecture and A/B layout, avoids bundling Google apps, and avoids a rooted image. The vanilla image is also less likely to require deleting or resizing other logical partitions.

## 4. Download the GSI

```bash
wget -c -O android-rom-work/lineage-21.0-20260507-UNOFFICIAL-arm64_bvN.img.gz https://sourceforge.net/projects/andyyan-gsi/files/lineage-21-pre-qpr2-td/lineage-21.0-20260507-UNOFFICIAL-arm64_bvN.img.gz/download
```

Check the file:

```bash
gzip -t android-rom-work/lineage-21.0-20260507-UNOFFICIAL-arm64_bvN.img.gz
sha256sum android-rom-work/lineage-21.0-20260507-UNOFFICIAL-arm64_bvN.img.gz
```

Extract it:

```bash
gunzip -k android-rom-work/lineage-21.0-20260507-UNOFFICIAL-arm64_bvN.img.gz
file android-rom-work/lineage-21.0-20260507-UNOFFICIAL-arm64_bvN.img
```

## 5. Download `vbmeta.img`

```bash
wget -c -O android-rom-work/vbmeta.img https://dl.google.com/developers/android/qt/images/gsi/vbmeta.img
sha256sum android-rom-work/vbmeta.img
```

Why: a generic GSI is not signed by Lenovo's stock verified boot chain. This image is used with `--disable-verity --disable-verification` so the GSI can boot.

## 6. Download stock rollback firmware

```bash
wget -c -q -O android-rom-work/TB350FU_S230613_241009_ROW.zip https://mirrors.lolinet.com/firmware/lenowow/2022/Tab_P11_2nd_Gen/TB350FU/TB350FU_S230613_241009_ROW.zip
```

Check the archive:

```bash
sha256sum android-rom-work/TB350FU_S230613_241009_ROW.zip
unzip -t android-rom-work/TB350FU_S230613_241009_ROW.zip
unzip -l android-rom-work/TB350FU_S230613_241009_ROW.zip
```

Why: have a rollback path ready before permanently modifying system partitions.

Useful rollback references:

- Lenovo support: https://pcsupport.lenovo.com/us/en/products/tablets/p-series/tab-p11-2nd-gen/downloads
- Lenovo Software Fix / Rescue and Smart Assistant: https://pcsupport.lenovo.com/us/ru/downloads/ds101291-rescue-and-smart-assistant-lmsa
- Lolinet TB350FU firmware mirror: https://mirrors.lolinet.com/firmware/lenowow/2022/Tab_P11_2nd_Gen/TB350FU/

## 7. Boot stock Android and enable ADB

From fastboot:

```bash
fastboot reboot
```

On the tablet:

1. Complete first setup if needed.
2. Open Settings.
3. Enable Developer options.
4. Enable USB debugging.
5. Accept the USB debugging prompt.

On the host:

```bash
adb devices -l
```

Why: DSU testing runs from Android userspace, so ADB must be authorized in stock Android.

## 8. Check Android-side compatibility

```bash
adb shell 'getprop ro.treble.enabled; getprop ro.product.cpu.abi; getprop ro.build.version.release; getprop ro.build.version.sdk; getprop ro.boot.slot_suffix; getprop ro.boot.dynamic_partitions; getprop ro.build.fingerprint; getprop ro.vendor.build.fingerprint'
```

Check DSU support and free storage:

```bash
adb shell 'pm list packages com.android.dynsystem; df -h /data /storage/emulated/0/Download 2>/dev/null; getprop ro.gsid.image_running'
```

Why: confirm the running stock system exposes the same compatibility traits and supports Dynamic System Updates.

## 9. Stage the GSI on the tablet

```bash
adb push android-rom-work/lineage-21.0-20260507-UNOFFICIAL-arm64_bvN.img.gz /storage/emulated/0/Download/lineage-21-arm64-bvN.img.gz
```

Check the copied file:

```bash
adb shell 'ls -l /storage/emulated/0/Download/lineage-21-arm64-bvN.img.gz; sha256sum /storage/emulated/0/Download/lineage-21-arm64-bvN.img.gz 2>/dev/null || toybox sha256sum /storage/emulated/0/Download/lineage-21-arm64-bvN.img.gz'
```

Why: DSU installs from a file available to Android.

## 10. Test with DSU before permanent flashing

Start the DSU install:

```bash
adb shell am start-activity -n com.android.dynsystem/com.android.dynsystem.VerificationActivity -a android.os.image.action.START_INSTALL -d file:///storage/emulated/0/Download/lineage-21-arm64-bvN.img.gz --el KEY_SYSTEM_SIZE 2543312896 --el KEY_USERDATA_SIZE 8589934592
```

Check DSU state:

```bash
adb shell gsi_tool status
adb shell dumpsys notification --noredact | grep -i -A 20 -B 5 'com.android.dynsystem'
```

On the tablet:

1. Pull down the notification shade.
2. Find the Dynamic System Updates notification.
3. Tap Restart when it says the dynamic system is ready.

Why: DSU boots the GSI temporarily before writing it permanently. This is the safer compatibility test.

## 11. Validate the DSU boot

After the tablet boots into LineageOS setup:

```bash
adb devices -l
adb shell 'getprop ro.build.version.release; getprop ro.build.version.sdk; getprop ro.product.model; getprop ro.gsid.image_running; getprop ro.treble.enabled; getprop ro.product.cpu.abi; getprop ro.boot.slot_suffix'
adb shell gsi_tool status
adb shell 'getprop ro.lineage.version; getprop ro.modversion'
```

On the tablet, test:

- Touch
- Wi-Fi
- Bluetooth
- Rotation
- Speakers
- Brightness
- Sleep/wake
- Charging indicator
- Camera if needed

Why: only permanently flash a GSI after the same image works through DSU.

## 12. Reboot to bootloader for permanent flashing

```bash
adb reboot bootloader
fastboot devices -l
fastboot getvar product
fastboot getvar current-slot
```

Why: permanent installation starts from bootloader fastboot.

## 13. Disable verification for the current slot

```bash
fastboot --disable-verity --disable-verification flash vbmeta android-rom-work/vbmeta.img
```

Why: the GSI system image is not Lenovo-signed, so AVB verification must be disabled for the slot that will boot the GSI.

## 14. Enter fastbootd

```bash
fastboot reboot fastboot
fastboot devices -l
fastboot getvar is-userspace
fastboot getvar product
```

Why: `system` is a logical dynamic partition, so it is flashed from userspace fastbootd.

## 15. Flash the tested GSI

```bash
fastboot flash system android-rom-work/lineage-21.0-20260507-UNOFFICIAL-arm64_bvN.img
```

Why: install the same image that already passed the DSU boot test.

After flashing, check the active slot:

```bash
fastboot getvar current-slot
```

## 16. Make sure vbmeta matches the active slot

If the active slot is `a`, reboot to bootloader and flash `vbmeta_a`:

```bash
fastboot reboot bootloader
fastboot --disable-verity --disable-verification flash vbmeta_a android-rom-work/vbmeta.img
```

If the active slot is `b`, reboot to bootloader and flash `vbmeta_b`:

```bash
fastboot reboot bootloader
fastboot --disable-verity --disable-verification flash vbmeta_b android-rom-work/vbmeta.img
```

Why: on this tablet, flashing `system` may target or switch to a different slot than the one where `vbmeta` was first written. The boot slot and AVB-disabled vbmeta slot need to match.

## 17. Wipe userdata

```bash
fastboot -w
```

Why: avoid setup, encryption, and data compatibility issues after switching from stock Android to the permanent GSI.

## 18. Reboot

```bash
fastboot reboot
```

First boot can take several minutes.

## 19. Validate the permanent install

```bash
adb wait-for-device shell 'getprop ro.lineage.version; getprop ro.gsid.image_running; getprop ro.product.model'
adb shell 'getprop ro.build.version.release; getprop ro.build.version.sdk; getprop ro.boot.slot_suffix; getprop ro.product.cpu.abi; getprop ro.treble.enabled'
adb shell gsi_tool status
adb devices -l
```

The permanent install should report LineageOS, Android 14, the expected active slot, and an empty `ro.gsid.image_running` property.

## 20. Keep the bootloader unlocked

Do not run:

```bash
fastboot flashing lock
```

Why: GrapheneOS can relock on supported Pixels because it provides a complete signed OS and verified boot key flow. This Lenovo GSI install uses disabled AVB verification and a generic system image. Relocking may make the bootloader enforce verification and refuse to boot.

## Installed state from this run

- Device: Lenovo TB350FU
- Installed system: LineageOS 21 GSI
- Build: `21.0-20260507-UNOFFICIAL-arm64_bvN`
- Android version: 14
- Active slot after install: `_a`
- Bootloader: unlocked
- Rollback firmware: `android-rom-work/TB350FU_S230613_241009_ROW.zip`
