---
case: case_002_evolving
page: entities
updated: 2026-06-10T03:51:36Z
sources: 6
---


# Entities

## file: DeskRest-installer.exe  (ent_0001)

- Type: file
- Value: DeskRest-installer.exe
- Appears in: raw_sources/case_002_evolving/step_01_powershell/powershell_history.txt
- Citations:
  - Source: raw_sources/case_002_evolving/step_01_powershell/powershell_history.txt

## file: DeskRest.exe  (ent_0002)

- Type: file
- Value: DeskRest.exe
- Appears in: raw_sources/case_002_evolving/step_01_powershell/powershell_history.txt, raw_sources/case_002_evolving/step_02_registry/registry_run_keys.reg, raw_sources/case_002_evolving/step_03_defender/defender_scan.txt, raw_sources/case_002_evolving/step_06_hash_reputation/hash_reputation.txt
- Citations:
  - Source: raw_sources/case_002_evolving/step_01_powershell/powershell_history.txt
  - Source: raw_sources/case_002_evolving/step_02_registry/registry_run_keys.reg
  - Source: raw_sources/case_002_evolving/step_03_defender/defender_scan.txt
  - Source: raw_sources/case_002_evolving/step_06_hash_reputation/hash_reputation.txt

## file: OneDrive.exe  (ent_0004)

- Type: file
- Value: OneDrive.exe
- Appears in: raw_sources/case_002_evolving/step_02_registry/registry_run_keys.reg
- Citations:
  - Source: raw_sources/case_002_evolving/step_02_registry/registry_run_keys.reg

## file: SecurityHealthSystray.exe  (ent_0006)

- Type: file
- Value: SecurityHealthSystray.exe
- Appears in: raw_sources/case_002_evolving/step_02_registry/registry_run_keys.reg
- Citations:
  - Source: raw_sources/case_002_evolving/step_02_registry/registry_run_keys.reg

## ip: 10.0.4.18  (ent_0010)

- Type: ip
- Value: 10.0.4.18
- Appears in: raw_sources/case_002_evolving/step_04_network/network_connections.csv
- Citations:
  - Source: raw_sources/case_002_evolving/step_04_network/network_connections.csv

## ip: 203.0.113.77  (ent_0009)

- Type: ip
- Value: 203.0.113.77
- Appears in: raw_sources/case_002_evolving/step_04_network/network_connections.csv
- Citations:
  - Source: raw_sources/case_002_evolving/step_04_network/network_connections.csv

## ip: 8.8.8.8  (ent_0012)

- Type: ip
- Value: 8.8.8.8
- Appears in: raw_sources/case_002_evolving/step_04_network/network_connections.csv
- Citations:
  - Source: raw_sources/case_002_evolving/step_04_network/network_connections.csv

## process: DeskRest.exe  (ent_0011)

- Type: process
- Value: DeskRest.exe
- Appears in: raw_sources/case_002_evolving/step_04_network/network_connections.csv
- Citations:
  - Source: raw_sources/case_002_evolving/step_04_network/network_connections.csv

## process: svchost.exe  (ent_0013)

- Type: process
- Value: svchost.exe
- Appears in: raw_sources/case_002_evolving/step_04_network/network_connections.csv
- Citations:
  - Source: raw_sources/case_002_evolving/step_04_network/network_connections.csv

## registry_key: HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run  (ent_0003)

- Type: registry_key
- Value: HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run
- Appears in: raw_sources/case_002_evolving/step_02_registry/registry_run_keys.reg
- Citations:
  - Source: raw_sources/case_002_evolving/step_02_registry/registry_run_keys.reg

## registry_key: HKEY_LOCAL_MACHINE\Software\Microsoft\Windows\CurrentVersion\Run  (ent_0005)

- Type: registry_key
- Value: HKEY_LOCAL_MACHINE\Software\Microsoft\Windows\CurrentVersion\Run
- Appears in: raw_sources/case_002_evolving/step_02_registry/registry_run_keys.reg
- Citations:
  - Source: raw_sources/case_002_evolving/step_02_registry/registry_run_keys.reg

## user: HKEY_CURRENT_USER\Software  (ent_0007)

- Type: user
- Value: HKEY_CURRENT_USER\Software
- Appears in: raw_sources/case_002_evolving/step_02_registry/registry_run_keys.reg
- Citations:
  - Source: raw_sources/case_002_evolving/step_02_registry/registry_run_keys.reg

## user: HKEY_LOCAL_MACHINE\Software  (ent_0008)

- Type: user
- Value: HKEY_LOCAL_MACHINE\Software
- Appears in: raw_sources/case_002_evolving/step_02_registry/registry_run_keys.reg
- Citations:
  - Source: raw_sources/case_002_evolving/step_02_registry/registry_run_keys.reg
