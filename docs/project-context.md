# Project context for teammates and future AI sessions

Our primary goal is to pass the SMVIT 2026–2027 course at FIIT STU with a team gesture-glove project.
The initial idea is preserved in `hardware/reference/glove_smvit.pdf`.

Both flex sensors and fingertip contact pads are required. The current examples also show an IMU.
The provisional board is the Adafruit Feather ESP32-S3 (#5323). Board choice and battery/power arrangement remain open design decisions; do not treat the examples as a build-ready electrical design.
The FreeCAD, KiCad and Fritzing models were experiments showing that AI can work with these tools.
Retain the reproducible integrations; replacing the example models is acceptable.

FreeCAD models physical placement, KiCad represents electrical connections, and Fritzing provides a beginner-friendly wiring view. These views must eventually agree, but matching netlists alone does not validate power, mechanics or a wearable device.

The team includes the repository owner and one colleague using Arch Linux with Nix. Mykhailo Sichkaruk is ST033; Yaroslav Marochok is ST029. The supplied roster has empty ProjectID fields for both. Yaroslav uses integrated Intel plus dedicated NVIDIA graphics. The PRJ number is pending. No actual hardware construction, firmware, calibration, user testing or final presentations are claimed complete.

Microsoft Teams MCP is optional and disabled. STU administrator consent is still pending; do not try to bypass it. CAD/documentation work does not depend on Teams.

This repository replaces the old scratch repository at the same working-directory path, preserving local conversation association without editing Codex session databases. The conversation itself is local application data and is not shared through Git. This document and AGENTS.md are the reusable handoff for other people or new chats.

Next work: confirm course IDs and submission procedure; agree requirements and task ownership; choose components and power; replace PoCs with reviewed designs; implement/test firmware; document evidence and each student's contributions.
