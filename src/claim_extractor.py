"""Pull events, IOCs, hypotheses, and contradictions out of parsed sources.

The strategy is deliberately conservative: claim only what the file
literally supports. Hypotheses use Medium or Low confidence; "High" or
"Confirmed" never come from a single source.
"""
from __future__ import annotations

import re

from .parsers import ParsedSource
from .schemas import IOC, Citation, Contradiction, Event, Hypothesis


def _basename(path: str) -> str:
    return path.replace("\\", "/").rsplit("/", 1)[-1]


_SUSPICIOUS_PROCESS_HINTS = (
    "powershell.exe",
    "cmd.exe",
    "rundll32.exe",
    "regsvr32.exe",
    "wscript.exe",
    "cscript.exe",
    "mshta.exe",
)

_PRIVATE_IP_PREFIXES = ("10.", "192.168.", "172.16.", "172.17.", "172.18.", "172.19.",
                        "172.2", "172.30.", "172.31.", "127.")


def _is_public_ip(ip: str) -> bool:
    return not any(ip.startswith(p) for p in _PRIVATE_IP_PREFIXES) and ip != "0.0.0.0"


def extract_events(source: ParsedSource) -> list[Event]:
    cite = Citation(kind="source", target=source.path)
    events: list[Event] = []

    if source.kind == "sysmon_csv" and source.rows:
        for row in source.rows:
            ts = row.get("timestamp", "unknown")
            event_id = row.get("event_id", "")
            image = _basename(row.get("image", "")) or row.get("image", "")
            parent = _basename(row.get("parent_image", "")) or row.get("parent_image", "")
            cmd = row.get("command_line", "")
            if event_id == "1":
                desc = f"{parent or 'unknown parent'} spawned {image}"
                if cmd:
                    desc += f" ({cmd})"
            elif event_id == "3":
                desc = f"{image} initiated network activity ({cmd or 'no detail'})"
            else:
                desc = f"event_id={event_id}: {cmd or image}"
            events.append(Event(timestamp=ts, description=desc, citation=cite))

    elif source.kind == "network_csv" and source.rows:
        for row in source.rows:
            ts = row.get("timestamp", "unknown")
            proto = row.get("protocol", "")
            proc = row.get("process", "unknown")
            remote = row.get("remote_address", "")
            rport = row.get("remote_port", "")
            sent = row.get("bytes_sent", "0")
            desc = (
                f"{proc} connected to {remote}:{rport} ({proto}, sent {sent} bytes)"
            )
            events.append(Event(timestamp=ts, description=desc, citation=cite))

    elif source.kind == "powershell_history":
        for i, line in enumerate(source.text.splitlines()):
            line = line.strip()
            if not line:
                continue
            events.append(Event(
                timestamp="unknown",
                description=f"PowerShell command #{i+1}: {line}",
                citation=cite,
            ))

    elif source.kind == "registry_reg" and source.sections:
        for section in source.sections:
            for entry in section.get("values", []):
                events.append(Event(
                    timestamp="unknown",
                    description=(
                        f"Registry value '{entry['name']}' set under "
                        f"{section['key']} = {entry['value']}"
                    ),
                    citation=cite,
                ))

    elif source.kind == "defender_scan":
        m = re.search(r"Threats Found\s*:\s*(\d+)", source.text)
        if m:
            count = m.group(1)
            events.append(Event(
                timestamp=_first_match(r"Completed\s*:\s*([\d\-:\s]+)", source.text) or "unknown",
                description=f"Windows Defender full scan completed; {count} threats found.",
                citation=cite,
            ))

    elif source.kind == "hash_reputation":
        verdict = _first_match(r"Verdict\s*:\s*(.+)", source.text) or "unknown"
        detections = _first_match(r"Detections\s*:\s*([\d/\s]+)", source.text) or "unknown"
        target = _first_match(r"Target file\s*:\s*(.+)", source.text) or "unknown file"
        sha = _first_match(r"SHA-?256\s*:\s*([0-9a-fA-F]+)", source.text)
        desc = (
            f"Hash reputation lookup for {target.strip()} returned "
            f"{detections.strip()} detections; verdict: {verdict.strip()}"
        )
        if sha:
            desc += f" (sha256: {sha[:16]}…)"
        events.append(Event(timestamp="unknown", description=desc, citation=cite))

    elif source.kind == "investigator_notes":
        for bullet in re.findall(r"^\s*-\s+(.+)$", source.text, flags=re.MULTILINE):
            events.append(Event(
                timestamp="unknown",
                description=f"Investigator note: {bullet.strip()}",
                citation=cite,
            ))

    return events


def extract_iocs(source: ParsedSource) -> list[IOC]:
    iocs: list[IOC] = []
    src = source.path

    if source.kind == "registry_reg" and source.sections:
        for section in source.sections:
            if "\\Run" in section["key"] or section["key"].lower().endswith("\\run"):
                for entry in section.get("values", []):
                    value = entry["value"]
                    fname = _exe_name(value)
                    if not fname:
                        continue
                    if fname.lower() in {"onedrive.exe", "securityhealthsystray.exe"}:
                        continue  # benign baseline
                    iocs.append(IOC(
                        artifact=fname,
                        type="file",
                        first_seen="unknown",
                        source=src,
                        confidence="Medium",
                        reason=(
                            f"Registered for autostart via {section['key']} → "
                            f"{entry['name']} ({value})"
                        ),
                        related=["[[hypotheses]]", "[[timeline]]"],
                    ))

    if source.kind == "sysmon_csv" and source.rows:
        for row in source.rows:
            parent = _basename(row.get("parent_image", "")).lower()
            image_full = row.get("image", "")
            image = _basename(image_full)
            if parent in _SUSPICIOUS_PROCESS_HINTS and image and parent != image.lower():
                iocs.append(IOC(
                    artifact=image,
                    type="file",
                    first_seen=row.get("timestamp", "unknown"),
                    source=src,
                    confidence="Medium",
                    reason=f"Spawned by {parent}, which is a common LOLBin parent.",
                    related=["[[timeline]]", "[[hypotheses]]"],
                ))

    if source.kind == "network_csv" and source.rows:
        for row in source.rows:
            remote = row.get("remote_address", "")
            proc = row.get("process", "unknown")
            if remote and _is_public_ip(remote) and proc.lower() not in {"outlook.exe", "svchost.exe"}:
                iocs.append(IOC(
                    artifact=remote,
                    type="ip",
                    first_seen=row.get("timestamp", "unknown"),
                    source=src,
                    confidence="Low",
                    reason=(
                        f"Outbound TCP from {proc} to public IP {remote}:"
                        f"{row.get('remote_port', '?')}."
                    ),
                    related=["[[entities]]", "[[hypotheses]]"],
                ))

    return iocs


def extract_hypotheses(source: ParsedSource) -> list[Hypothesis]:
    """Produce *hypotheses*, not conclusions. Only Low/Medium confidence here."""
    out: list[Hypothesis] = []
    src = source.path

    if source.kind == "registry_reg" and source.sections:
        run_targets: list[str] = []
        for section in source.sections:
            if "\\Run" not in section["key"]:
                continue
            for entry in section.get("values", []):
                fname = _exe_name(entry["value"])
                if fname and fname.lower() not in {"onedrive.exe", "securityhealthsystray.exe"}:
                    run_targets.append(f"{fname} via {section['key']}\\{entry['name']}")
        if run_targets:
            out.append(Hypothesis(
                title="Possible Registry-Based Persistence",
                confidence="Medium",
                facts=[
                    f"Registry Run key references {t} (Source: {src})."
                    for t in run_targets
                ],
                inference=(
                    "Run-key entries cause the referenced binary to execute at "
                    "user logon. This is a recognised persistence technique "
                    "(MITRE ATT&CK T1547.001), although it is also used by "
                    "legitimate software."
                ),
                supporting_evidence=[f"Source: {src}"],
                contradicting_evidence=[],
                open_questions=[
                    "Is the referenced executable digitally signed?",
                    "What is the SHA-256 reputation of the executable?",
                    "Was the Run key created by an installer or by post-exploit activity?",
                ],
                next_steps=[
                    "Hash the executable and submit to a reputation service.",
                    "Check Authenticode signature.",
                    "Correlate Run-key creation time with process activity.",
                ],
            ))

    if source.kind == "sysmon_csv" and source.rows:
        suspicious_spawns = []
        for row in source.rows:
            parent = _basename(row.get("parent_image", "")).lower()
            image = _basename(row.get("image", ""))
            if parent in _SUSPICIOUS_PROCESS_HINTS and image and parent != image.lower():
                suspicious_spawns.append(
                    f"{parent} → {image} at {row.get('timestamp', 'unknown')} "
                    f"(Source: {src})"
                )
        if suspicious_spawns:
            out.append(Hypothesis(
                title="Suspicious Process Execution Chain",
                confidence="Medium",
                facts=suspicious_spawns,
                inference=(
                    "Interactive interpreters such as PowerShell launching "
                    "additional binaries is a common pattern in both benign "
                    "administration and malicious execution."
                ),
                supporting_evidence=[f"Source: {src}"],
                contradicting_evidence=[],
                open_questions=[
                    "Was the parent PowerShell session user-initiated or automated?",
                    "Were the spawned binaries signed and known?",
                ],
                next_steps=[
                    "Pull the PowerShell ScriptBlock log for the parent session.",
                    "Hash and reputation-check each spawned binary.",
                ],
            ))

    if source.kind == "network_csv" and source.rows:
        public_conns = [
            row for row in source.rows
            if _is_public_ip(row.get("remote_address", ""))
            and row.get("process", "").lower() not in {"outlook.exe", "svchost.exe"}
        ]
        if public_conns:
            facts = [
                f"{row.get('process', '?')} → {row.get('remote_address', '?')}:"
                f"{row.get('remote_port', '?')} at {row.get('timestamp', 'unknown')} "
                f"(Source: {src})"
                for row in public_conns
            ]
            out.append(Hypothesis(
                title="Possible Outbound C2 Beacon",
                confidence="Low",
                facts=facts,
                inference=(
                    "A non-browser process connecting to an unfamiliar public "
                    "IP may indicate command-and-control activity, but byte "
                    "volumes and frequency must be examined before drawing a "
                    "conclusion."
                ),
                supporting_evidence=[f"Source: {src}"],
                contradicting_evidence=[],
                open_questions=[
                    "Is the remote IP attributed to a known service?",
                    "Are the beacons periodic or one-off?",
                    "What is the data volume in each direction?",
                ],
                next_steps=[
                    "WHOIS / passive-DNS the remote IP.",
                    "Pull full PCAP if available.",
                ],
            ))

    return out


def extract_contradictions(
    source: ParsedSource,
    prior_hypotheses: list[Hypothesis],
    prior_iocs: list[IOC],
) -> list[Contradiction]:
    """Compare new evidence against what the wiki already believes."""
    out: list[Contradiction] = []

    if source.kind == "hash_reputation":
        verdict = _first_match(r"Verdict\s*:\s*(.+)", source.text) or ""
        detections = _first_match(r"Detections\s*:\s*([\d]+)\s*/\s*([\d]+)",
                                  source.text)
        inconclusive = "unknown" in verdict.lower() or "inconclusive" in verdict.lower()
        zero_dets = bool(detections) and detections.startswith("0")
        if inconclusive or zero_dets:
            out.append(Contradiction(
                title="Investigator malware suspicion vs. inconclusive hash reputation",
                claim_a=(
                    "Investigator notes (if present) describe a malware diagnosis."
                ),
                claim_b=(
                    f"Hash reputation lookup is inconclusive (Source: {source.path}); "
                    f"no AV engine flags the binary and the verdict is '{verdict.strip()}'."
                ),
                status="Unresolved",
            ))

    if source.kind == "defender_scan":
        m = re.search(r"Threats Found\s*:\s*(\d+)", source.text)
        if m and m.group(1) == "0":
            persistence_active = any(
                "persistence" in h.title.lower() for h in prior_hypotheses
            )
            ioc_present = bool(prior_iocs)
            if persistence_active or ioc_present:
                out.append(Contradiction(
                    title="Suspicious activity vs. clean AV scan",
                    claim_a=(
                        "Suspicious autostart and/or process activity has been "
                        "recorded in the wiki."
                    ),
                    claim_b=(
                        f"Windows Defender full scan reported 0 threats "
                        f"(Source: {source.path})."
                    ),
                    status="Unresolved",
                ))

    if source.kind == "investigator_notes":
        if re.search(r"\bmalware\b", source.text, flags=re.IGNORECASE):
            out.append(Contradiction(
                title="Investigator suspicion vs. limited objective evidence",
                claim_a=(
                    f"Investigator notes describe a possible malware "
                    f"diagnosis (Source: {source.path})."
                ),
                claim_b=(
                    "Wiki evidence so far supports suspicious behaviour and "
                    "possible persistence only; the malware diagnosis remains "
                    "a Medium-confidence hypothesis."
                ),
                status="Unresolved",
            ))

    return out


def extract_open_questions(source: ParsedSource) -> list[str]:
    if source.kind == "registry_reg":
        return [
            "Were the autostart entries created by an installer or by post-exploit activity?",
        ]
    if source.kind == "sysmon_csv":
        return [
            "Is the suspicious spawned binary signed?",
            "Does its hash have a reputation hit?",
        ]
    if source.kind == "network_csv":
        return [
            "Is the public destination IP attributed to a known service?",
        ]
    if source.kind == "defender_scan":
        return [
            "Should a second-opinion scanner be run against the suspicious binary?",
        ]
    return []


def _exe_name(value: str) -> str | None:
    m = re.search(r"([A-Za-z0-9_.\-]+\.exe)", value)
    return m.group(1) if m else None


def _first_match(pattern: str, text: str) -> str | None:
    m = re.search(pattern, text)
    return m.group(1).strip() if m else None
