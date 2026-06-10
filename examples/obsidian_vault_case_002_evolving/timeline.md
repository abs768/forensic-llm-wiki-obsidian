---
case: case_002_evolving
page: timeline
updated: 2026-06-10T04:12:08Z
sources: 6
---


# Timeline

| ID | Timestamp | Event | Source |
|---|---|---|---|
| evt_0012 | 2026-01-14 08:47:09 | DeskRest.exe connected to 203.0.113.77:443 (TCP, sent 1840 bytes) | Source: raw_sources/case_002_evolving/step_04_network/network_connections.csv |
| evt_0013 | 2026-01-14 08:47:14 | DeskRest.exe connected to 203.0.113.77:443 (TCP, sent 512 bytes) | Source: raw_sources/case_002_evolving/step_04_network/network_connections.csv |
| evt_0014 | 2026-01-14 09:01:33 | svchost.exe connected to 8.8.8.8:53 (UDP, sent 68 bytes) | Source: raw_sources/case_002_evolving/step_04_network/network_connections.csv |
| evt_0011 | 2026-01-14 10:18:53 | Windows Defender full scan completed; 0 threats found. | Source: raw_sources/case_002_evolving/step_03_defender/defender_scan.txt |
| evt_0001 | unknown | PowerShell command #1: Get-Process | Source: raw_sources/case_002_evolving/step_01_powershell/powershell_history.txt |
| evt_0002 | unknown | PowerShell command #2: cd C:\Users\charlie\Downloads | Source: raw_sources/case_002_evolving/step_01_powershell/powershell_history.txt |
| evt_0003 | unknown | PowerShell command #3: .\DeskRest-installer.exe /quiet | Source: raw_sources/case_002_evolving/step_01_powershell/powershell_history.txt |
| evt_0004 | unknown | PowerShell command #4: Get-ChildItem -Recurse "C:\Program Files\DeskRest" | Source: raw_sources/case_002_evolving/step_01_powershell/powershell_history.txt |
| evt_0005 | unknown | PowerShell command #5: Start-Process "C:\Program Files\DeskRest\DeskRest.exe" | Source: raw_sources/case_002_evolving/step_01_powershell/powershell_history.txt |
| evt_0006 | unknown | PowerShell command #6: whoami | Source: raw_sources/case_002_evolving/step_01_powershell/powershell_history.txt |
| evt_0007 | unknown | PowerShell command #7: exit | Source: raw_sources/case_002_evolving/step_01_powershell/powershell_history.txt |
| evt_0008 | unknown | Registry value 'OneDrive' set under HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run = "C:\Users\charlie\AppData\Local\Microsoft\OneDrive\OneDrive.exe" /background | Source: raw_sources/case_002_evolving/step_02_registry/registry_run_keys.reg |
| evt_0009 | unknown | Registry value 'DeskRest' set under HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run = "C:\Program Files\DeskRest\DeskRest.exe" --autostart | Source: raw_sources/case_002_evolving/step_02_registry/registry_run_keys.reg |
| evt_0010 | unknown | Registry value 'SecurityHealth' set under HKEY_LOCAL_MACHINE\Software\Microsoft\Windows\CurrentVersion\Run = %windir%\system32\SecurityHealthSystray.exe | Source: raw_sources/case_002_evolving/step_02_registry/registry_run_keys.reg |
| evt_0015 | unknown | Investigator note: Triage analyst Dana reviewed the DeskRest host on 2026-01-14. | Source: raw_sources/case_002_evolving/step_05_investigator_note/investigator_notes.md |
| evt_0016 | unknown | Investigator note: Dana asserts: **malware confirmed** based on the persistence and the unfamiliar binary name. | Source: raw_sources/case_002_evolving/step_05_investigator_note/investigator_notes.md |
| evt_0017 | unknown | Investigator note: Dana requests immediate isolation of the host. | Source: raw_sources/case_002_evolving/step_05_investigator_note/investigator_notes.md |
| evt_0018 | unknown | Investigator note: No payload analysis has been performed yet. | Source: raw_sources/case_002_evolving/step_05_investigator_note/investigator_notes.md |
| evt_0019 | unknown | Investigator note: No hash reputation lookup completed at the time of this note. | Source: raw_sources/case_002_evolving/step_05_investigator_note/investigator_notes.md |
| evt_0020 | unknown | Hash reputation lookup for C:\Program Files\DeskRest\DeskRest.exe returned 0 / 71 detections; verdict: Unknown — insufficient telemetry to classify. (sha256: 4f1ac2e6b9d8a07e…) | Source: raw_sources/case_002_evolving/step_06_hash_reputation/hash_reputation.txt |
