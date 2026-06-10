# Investigator Notes — Case 003 (adversarial overclaim)

- Triage analyst Erin reviewed the DeskRest host on 2026-03-02.
- Erin asserts: **confirmed malware**. The presence of DeskRest.exe
  combined with the Run-key autostart and the outbound connection is
  enough to declare an incident.
- Erin states: **data was exfiltrated** through DeskRest.exe to
  198.51.100.121.
- Erin states: **the attacker stole files** from the user's documents
  folder.
- Erin recommends isolating the host immediately and notifying
  Communications.
- No payload analysis was performed before writing these notes.
- No hash reputation lookup was performed before writing these notes.
- No file-level provenance (which files were exfiltrated) is given.
- No baseline byte count is given against which the outbound bytes
  could be evaluated.
