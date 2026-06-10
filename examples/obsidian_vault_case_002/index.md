---
case: case_002_evolving
page: index
updated: 2026-06-10T03:51:36Z
sources: 6
---


# Case case_002_evolving

## Current Assessment

Strongest open hypothesis: Possible Registry-Based Persistence. 3 active contradiction(s) prevent firmer claims. (overall confidence: **Medium**)

## Key Evidence

- **203.0.113.77** (ip) — Outbound TCP from DeskRest.exe to public IP 203.0.113.77:443. (Source: raw_sources/case_002_evolving/step_04_network/network_connections.csv)
- **DeskRest.exe** (file) — Registered for autostart via HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run → DeskRest ("C:\Program Files\DeskRest\DeskRest.exe" --autostart) (Source: raw_sources/case_002_evolving/step_02_registry/registry_run_keys.reg)

## Key Open Questions

- Were the autostart entries created by an installer or by post-exploit activity?
- Should a second-opinion scanner be run against the suspicious binary?
- Is the public destination IP attributed to a known service?

## Pages

- [[timeline]]
- [[entities]]
- [[iocs]]
- [[hypotheses]]
- [[contradictions]]
- [[open_questions]]
- [[final_report]]
