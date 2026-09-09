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

## Alpha release preparation — 2026-09-09

- 78 Python tests passed on Python 3.11.16 and 3.13.15 in temporary runtimes.
- Isolated-home tests cover install, repeated install, uninstall, unsupported
  Lua API, refusal to remove foreign files, and failed-install rollback.
- Personal author and committer emails were replaced with the maintainer's
  GitHub noreply identity. A private local bundle retains the original history.
- GitHub-hosted CI remains subject to the account billing restriction; local
  matrix results are not represented as hosted-CI success.

The isolated-home tests mock desktop commands. They do not count as a second
physical-machine installation. This is an alpha release, not a stable release.
