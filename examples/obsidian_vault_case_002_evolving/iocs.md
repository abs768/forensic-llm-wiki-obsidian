---
case: case_002_evolving
page: iocs
updated: 2026-06-10T04:12:08Z
sources: 6
---


# Indicators of Compromise

| Artifact | Type | First Seen | Source | Confidence | Reason | Related |
|---|---|---|---|---|---|---|
| DeskRest.exe | file | unknown | raw_sources/case_002_evolving/step_02_registry/registry_run_keys.reg | Medium | Registered for autostart via HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run → DeskRest ("C:\Program Files\DeskRest\DeskRest.exe" --autostart) | [[hypotheses]], [[timeline]] |
| 203.0.113.77 | ip | 2026-01-14 08:47:09 | raw_sources/case_002_evolving/step_04_network/network_connections.csv | Low | Outbound TCP from DeskRest.exe to public IP 203.0.113.77:443. | [[entities]], [[hypotheses]] |
