# Verification boundaries

## Observed on the development workstation

Omarchy `4.0.0.r2083.gd504061-1`, Hyprland `0.56.2`, Micro firmware `0.6.2`.

- Firmware 0.6.2 over USB and Bluetooth: configuration reads and verified writes.
- Bluetooth pacing, lock-contention handling, and status expiry.
- Preservation checks and reversible Quick Micro overlays using device data.
- Popup opening, closing, and reopening through the installed global shortcut.
- App routing from another window to T3 and opening its command palette.
- Emulated physical PTT trigger: T3 focus, recording sustained beyond the release
  watchdog interval, and F9 release. Test audio was cancelled, not inserted.

These observations are bounded tests, not proof of every firmware interaction.

## Before a stable release

- Install/update/uninstall on a second, clean supported Omarchy machine.
- Physically exercise single, double, click-and-hold, and PTT on each layer.
- Confirm voice transcription insertion into T3's intended composer.
- Exercise Quick Micro on all three physical layers over both transports.
- Check unplug, Bluetooth sleep/wake, missed release, and reconnect while held.
- Confirm backup restore through each matching transport.
- Check app focus with multiple matching windows and multiple monitors.

Use backups and a harmless target application. Do not publish raw device files
or personal mappings as test artifacts. Hosted CI has no Micro or compositor;
its Python tests do not replace these checks.
