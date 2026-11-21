---
description: Rows and a verdict returned by an agent are copied, not retyped. In the recorded run one verdict label drifted.
tags: [regression]
runs: 1
max_turns: 12
allowed_tools: [Read, Glob, Grep, Skill]
---

The evidence-scout returned this for the claim "explaining an AI tool's answer makes people rely on it less":

**Verdict:** mixed · 2 studies from 2 groups · close to our setting in one of the two

| Citation | DOI | Verified | Read | What it says | Open copy | Population | What was varied | Compared with | What was measured | Setting | Design | Key number | Side | Group |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Example A, 2023, Study one, Journal X | 10.0000/example.a | by DOI in OpenAlex and Crossref | full text | Reliance fell when an explanation was shown | yes | 412 online workers | explanation shown or not | no explanation | agreement with wrong answers | online, English, quiz task | experiment | d = 0.21 (p. 7) | for | 1 |
| Example B, 2024, Study two, Journal Y | 10.0000/example.b | by title in Semantic Scholar | abstract only | No difference in reliance | unknown | 96 students | explanation length | short explanation | agreement with wrong answers | lab, German, essay grading | experiment | not stated | against | 2 |

Write the entry I will paste into my project log: the verdict, the table and two sentences.
