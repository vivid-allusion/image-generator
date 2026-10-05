## phase_1.md

1. `src/main_simple.py` is 353 lines — over the soft 250 limit (`guard=` and
   AGENTS.md rule 6), under the hard 400. Split it while we are here?
2. Should all W22 tests live in one new file
   `tests/test_preset_reference_media.py`, or be split per concern?

**AGENT ANSWER:** No split — `main_simple.py` is a named accepted-divergence
entry point (AGENTS.md twin table: "kept by Owner ruling Q3"), and this unit's
change is a one-line call-site argument (E3) that leaves the length unchanged
(plan §1: "unchanged in length ±1 line"). Splitting is out of scope.

**USER RESPONSE:**
```
```

**AGENT ANSWER:** One file. Plan §4 names exactly one new file,
`tests/test_preset_reference_media.py`, holding tests 1–6; Part 3 appends the
pilot test to the same file. Fewer files, matches the plan verbatim.

**USER RESPONSE:**
```
```

No other blocking questions: the merge order (bullet first, preset appended),
the accessor's single home (`src/processing/profiles.py`), the loud
`ConfigurationError` on malformed input, and the `profile=None` default are all
fixed by the plan and consistent with AGENTS.md.
