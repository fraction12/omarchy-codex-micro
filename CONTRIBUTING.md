# Contributing

Keep changes scoped and include a failing regression test for behavior fixes.
Run the Python suite and default-config validation listed in the README.
UI changes also need the local Omarchy QML tests and a screenshot inspection.

Do not commit personal mappings, device dumps, backups, credentials, audio,
or machine-specific commands. Use synthetic fixtures for tests. Configuration
changes must retain unknown/protected device data and preserve rollback.

Reports should include Omarchy/Hyprland versions, Micro firmware, transport,
steps to reproduce, and expected/actual behavior. Remove private commands and
paths from logs. Do not treat mocked tests as hardware verification.
