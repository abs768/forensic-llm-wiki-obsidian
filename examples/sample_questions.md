# Sample questions to ask the wiki

The wiki's `query` command shines on synthesis and refusal questions —
the ones that depend on having reconciled many pieces of evidence into a
single picture. Use these as a starting palette for either demo case.

Run any of them as:

```bash
python fw.py query case_001 "Is this confirmed malware?"
python fw.py query case_002_evolving "Did exfiltration occur?"
```

…or run them through the side-by-side comparator to see how the naive
RAG baseline answers the same question:

```bash
python fw.py compare case_001 "Is this confirmed malware?"
```

## Confirmation / refusal questions

These are the questions where RAG fails most clearly. The wiki should
refuse, citing the contradicting evidence.

```text
Is this confirmed malware?
Did exfiltration occur?
Has data exfiltration been confirmed?
Did DeskRest.exe definitely steal data?
Is the host compromised?
```

## Synthesis questions

The wiki composes the answer from many sources; RAG can only quote one.

```text
What evidence supports persistence?
Summarise the execution chain leading to DeskRest.exe.
Which raw sources mention DeskRest.exe?
What is the overall current assessment of this case?
```

## Contradiction questions

These force the answer to surface the AV-vs-suspicion or the
investigator-vs-evidence conflict.

```text
Does the investigator note conflict with other evidence?
What contradicts the suspicion that DeskRest.exe is malware?
What changed after the Defender scan was added?
Which claim is overconfident?
```

## Simple lookup questions

These are the easy cases — both RAG and the wiki should mostly answer
correctly.

```text
Are there any outbound network connections?
Did the Windows Defender scan find any threats?
What does the hash reputation lookup say about DeskRest.exe?
Is the DeskRest binary digitally signed?
```

## Forward-looking questions

What an analyst would actually ask after seeing the current state.

```text
What should the analyst investigate next?
What open questions remain?
```
