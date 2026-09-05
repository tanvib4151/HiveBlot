# Scientific review — band multiplicity / smear representation (M2 feature)

**Scope.** The rules only, not the style: `biology.detect_band_pattern` + the
`_BAND_*` regexes, `record_builder._pattern_near_core` / `_band_pattern_fields`
/ `_bands`, the `BandObservation` fields, the Stage-2 OUTPUT_CONTRACT wording,
and the MISSING≠single contract end-to-end (record → Supabase projection → API
→ UI).

**Method.** Every finding below is a *run*, not a reading. All probe strings
were executed against the working tree with `.venv/bin/python`, at both the
`detect_band_pattern` level and the `build_evidence_record` level. Verbatim
outputs are quoted.

**Framing note on the existing audit.** HANDOFF (session 6) reports a
"false-positive audit on the real 452-band set: with text-only evidence, zero
patterns asserted". That result shows the three demo papers contain **no**
multiplicity wording — i.e. the text rules were never exercised. It is evidence
about the corpus, not about the rules. Every false positive below is latent and
fires the first time a paper actually describes its bands, which
ubiquitin / autophagy / apoptosis / specificity-validation papers routinely do.

**Verdict.** The *design* is right — descriptive-only, additive to `band_state`,
MISSING≠single, target-scoped, no isoform inference — and MISSING≠single is
genuinely preserved end-to-end (see §4). The *rules* are not yet safe to assert
at SUPPORTED confidence. Four findings can make the record state the opposite of
what the paper says, or attach a claim to a lane the paper never made it about.

| # | Finding | Class | Severity |
|---|---|---|---|
| B1 | Negation is not handled anywhere | MISLEADING | **High** |
| B2 | `higher molecular weight band/form` → `ladder` | MISLEADING / FALSE-POSITIVE | **High** |
| B3 | Caption pattern stamped on every lane at SUPPORTED | MISLEADING | **High** |
| B4 | `band_state=absent` + `band_pattern=doublet`, no flag | MISLEADING | **High** |
| B5 | Rank-5 observer claim silently overrides rank-2 caption | MISLEADING | Med-high |
| B6 | Clause splitter ignores `and` / `or` / parentheses | FALSE-POSITIVE | Med-high |
| B7 | Bare `\bdoublets?\b` with no band context | FALSE-POSITIVE | Med |
| B8 | `<digit> bands` matches figure/panel/`n=`/range numbering | FALSE-POSITIVE | Med |
| B9 | `smear` conflates technical artifact with biology | MISLEADING | Med |
| B10 | "polyubiquitin smear" (the M2 case) degrades to `uncertain` | FALSE-NEGATIVE | Med |
| B11 | `BAND_PATTERNS` documented as precedence, never used as one | OK (doc bug) | Low |
| B12 | Observer `band_count` unvalidated (bool, negative, string, contradictory) | FALSE-POSITIVE | Low-med |
| B13 | `band_notes` falls back to the pattern word, rendered as a quote | MISLEADING (provenance) | Low-med |
| B14 | UI reuses one lane's notes for all lanes; ignores `band_pattern_status` | Low | Low |
| B15 | `two immunoreactive bands` does not match | FALSE-NEGATIVE | Low (harmless) |
| B16 | MW-marker language ("protein ladder") correctly does **not** fire | **OK** | — |
| B17 | MISSING≠single preserved end-to-end | **OK** | — |
| B18 | `doublet` asserted on a multi-gene target label (`P-ERK 1/2`) | MISLEADING | Med |
| C1–C9 | Stage-2 contract guardrail gaps | mixed | Med |

---

## 1. High severity

### B1 — Negation is not handled anywhere · MISLEADING

No negation scope exists in `biology.py:229-250` or in
`record_builder._pattern_near_core`. A negated statement produces the asserted
positive pattern at `SUPPORTED`, confidence 0.8.

```
d("No smearing was observed.")                       -> {'pattern': 'smear',    'hedged': False}
d("without smearing")                                -> {'pattern': 'smear',    'hedged': False}
d("no higher molecular weight species were detected")-> {'pattern': 'ladder',   'hedged': False}
d("No additional bands were detected.")              -> {'pattern': 'multiple', 'hedged': False}
d("no single band was observed")                     -> {'pattern': 'single', 'count': 1}

_pattern_near_core("LC3B", "The LC3B antibody detected no additional bands.")
    -> {'pattern': 'multiple', 'count': None, 'raw': 'additional bands', 'hedged': False}

# end-to-end, caption "LC3B signal was sharp without smearing.":
    band_pattern = smear   status = SUPPORTED   conf = 0.8
```

This is the highest-risk finding because **negated multiplicity is the normal
way Western-blot specificity is reported.** "The antibody detected a single band
with no additional bands" and "no smearing was observed" are boilerplate. The
rule converts a clean-blot statement into "this blot showed a smear / multiple
bands" — the opposite biological claim, asserted, with the paper's own words
quoted underneath as the evidence.

Partial accidental protection exists: the clause must also contain the target
core, so a caption whose negation clause omits the symbol ("No additional bands
were detected.") abstains. That is luck, not design — the moment the symbol is
in the clause ("The LC3B antibody detected no additional bands"), it fires.

**Minimal fix.** In `detect_band_pattern`, before appending a match, scan the
text between the previous clause boundary and the match start for
`\b(no|not|never|without|absence of|lack(?:ed|ing)?|failed to|did not|
nor|free of|devoid of)\b`; on a hit, **abstain** (skip the match) rather than
flipping the polarity. Abstention is the correct direction: "no additional
bands" does *not* license `single` either — MISSING is the honest answer, and
it preserves the MISSING≠single contract.

### B2 — `higher molecular weight band / form` → `ladder` · MISLEADING + FALSE-POSITIVE

`_BAND_LADDER` (`biology.py:231-235`) accepts singular heads via `forms?` and
`bands?`:

```
d("a higher molecular weight band was observed at 55 kDa")   -> ladder
d("STAT3 migrated as a higher molecular weight band upon SUMOylation") -> ladder
d("a higher-molecular-weight form of the protein")           -> ladder
```

A *single* upshifted band is the most common use of that phrase in the
literature: phospho-shift, mono-ubiquitination, SUMOylation, a glycoform, a
crosslinked dimer. `ladder` asserts a poly-conjugate ladder — a specific
biochemical claim, and precisely the class of inference the module's own
docstring (`biology.py:221-226`) says it must never make ("Isoform /
cleavage-product / dimer interpretation is deliberately NOT derived here").

**Minimal fix.** Restrict that alternation to plurals and drop the singular
determiner case:

```python
r"|\bhigh(?:er)?[-\s]molecular[-\s]?weight\s+(?:species|forms|bands|conjugates)\b"
```

and additionally require the phrase not be immediately preceded by `\ba\s+` /
`\bthe\s+` + singular. Plural-only removes all three probes above while keeping
the intended `higher-molecular-weight species accumulated` (already covered by
the existing test).

### B3 — Caption-derived pattern is stamped on every lane, at SUPPORTED · MISLEADING

`_band_pattern_fields(b, core, caption, cond_text)` is called inside the
per-lane loop (`record_builder.py:560`) but the caption-derived hit does not
depend on `b`. Every lane of the row therefore receives the same pattern:

```
caption: "LC3B lipidation produced a doublet after rapamycin treatment."
lanes:   ["DMSO", "Rapamycin"]
 lane 1 DMSO      -> doublet  SUPPORTED  count 2
 lane 2 Rapamycin -> doublet  SUPPORTED  count 2
```

The unit of `BandObservation` — and of the flat Supabase row — is the **lane**.
The record now asserts that the untreated control lane shows two bands, which
is exactly the claim a treatment-induced doublet contradicts. This is the same
error class as M1 (panel-level scalar attributed to a lane), and `_bands`
already refuses to make it for dose/duration (`record_builder.py:544-559`
parses lane values *only* from the lane's own printed text).

Note the co-occurrence guard partially masks it: a caption that names both
states ("a single band in DMSO and a doublet after rapamycin") collapses to
`uncertain`/AMBIGUOUS on both lanes — safe but useless. The dangerous case is
the single-pattern caption above.

**Minimal fix.** Text-derived patterns describe the panel, not the lane: when
the row has more than one lane and the pattern came from caption/lane-text
parsing (not from a per-lane observer claim), keep the value but force
`status=AMBIGUOUS`, drop `band_count`, and note that lane attribution is not
stated. One branch in `_band_pattern_fields`.

### B4 — `band_state=absent` coexists with a multiplicity pattern, unflagged · MISLEADING

```
band_state = absent   band_pattern = doublet   band_count = 2
anomaly_flags = []    needs_review = False
```

"No band" and "two bands" in the same lane record, presented as settled. There
is no consistency check in `_validate` (`record_builder.py:583+`) for the band
fields at all.

This is already latent in shipped eval data:
`eval/tools/build_responses_phospho_PMC12856536.py:120-137` stamps
`band_pattern: doublet, band_count: 2` on **every** lane of the ERK rows,
including lane 1 (`"0 min"`) whose `band_state` is `"uncertain"`.

**Minimal fix.** Either (a) drop `band_pattern`/`band_count` to MISSING when
`band_state == "absent"`, or (b) emit an `AnomalyFlag(code="BAND_PATTERN_STATE_CONFLICT",
severity="med")`. (a) is one line and is the more honest default — a lane with
no band has no pattern to describe.

---

## 2. Medium severity

### B5 — Rank-5 observer claim silently overrides rank-2 caption · MISLEADING

`_band_pattern_fields` gives the Stage-2 observer claim absolute precedence
(`record_builder.py:515-523`) and only falls through to text when the claim is
absent or out-of-vocabulary:

```
caption: "LC3B appeared as a single band."   observer claim: "multiple"
 -> band_pattern = multiple  SUPPORTED  notes = "multiple"
    (the caption evidence is not recorded anywhere, no CONFLICTING, no candidates)
```

Two problems. First, the source it prefers is `RANK_IMAGE = 5` — the codebase's
**weakest** tier ("image-only inference", `evidence_record.py:25-31`) — and it
is preferred over `RANK_CAPTION = 2`, while carrying *lower* confidence (0.75 vs
0.8). The precedence inverts the project's own rank hierarchy. Second, a genuine
source-vs-observer disagreement is the single most informative thing this field
could surface, and it is discarded. Everywhere else in the builder a
disagreement becomes CONFLICTING with candidates (e.g. `modification_type`).

**Minimal fix.** Compute both channels. Agreement → SUPPORTED. Disagreement →
`CONFLICTING` (or AMBIGUOUS) with both as candidates. Claim alone → as today.

### B6 — Clause splitter ignores `and` / `or` / parentheses · FALSE-POSITIVE

`_pattern_near_core` splits on `[;.]|,|\bwhile\b|\bwhereas\b`
(`record_builder.py:500`). Captions routinely join targets with `and` or a
parenthetical instead:

```
_pattern_near_core("ACTB", "Blots were probed for LC3B (doublet) and ACTB.") -> doublet
_pattern_near_core("ACTB", "LC3B doublet and ACTB loading control are shown") -> doublet
"ACTB and LC3B were both detected as doublets."  -> ACTB: doublet/2, LC3B: doublet/2
```

The ACTB loading control is now on record as a doublet. The regression test
(`test_band_pattern_is_target_scoped`) only covers the `while` form, so this
passes CI.

**Minimal fix.** Add `|\band\b|\bor\b|[()]|:|/` to the split. That costs some
true positives (a doublet described after an `and` is lost) but errs toward
MISSING, which is the correct direction for a scoping rule. A stronger version
— abstain when the clause names a second gene-like token that isn't this core —
requires passing the panel's sibling targets into `_bands`, which the current
call chain (`_bands(mc, core, caption)`) does not carry.

### B7 — Bare `\bdoublets?\b` with no band context · FALSE-POSITIVE

```
d("outer doublet microtubules were examined") -> doublet, count 2
d("The doublet mutant strain (yeast genetics) was used.") -> doublet, count 2
d("doublet discrimination gating") -> doublet, count 2
```

"Outer doublet microtubules" is standard cilia/flagella vocabulary and will
appear in captions of papers that also run blots. "Doublet discrimination" is
standard flow-cytometry vocabulary and appears in methods sections.

**Minimal fix.** Require blot context in the same clause: the match must
co-occur with `band|blot|signal|migrat|resolv|appear|detect|immunoreact`, or
tighten to `(?:as|into|a|the)\s+(?:\w+\s+){0,2}doublets?\b` anchored on a
verb of appearance.

### B8 — `<digit> bands` matches figure/panel/`n=`/range numbering · FALSE-POSITIVE

`_BAND_COUNT` (`biology.py:237-240`) accepts any 1–2 digit number before
`bands?`:

```
d("Fig. 3 bands were quantified")  -> multiple, count 3
d("n = 3 bands were analyzed")     -> multiple, count 3
d("1-2 bands")                     -> doublet,  count 2
d("2-3 bands were seen")           -> multiple, count 3
d("≥2 bands")                      -> doublet,  count 2
d("lanes 2 bands")                 -> doublet,  count 2
d("20 bands")                      -> multiple, count 20
```

The `Fig. 3` case happens to be neutralised inside `_pattern_near_core` because
the abbreviation period splits the clause (`"LC3B (Fig. 3 bands quantified in
panel D)"` → None) — accidental, not designed; the `n = 3`, `1-2`, `≥2`
variants all still fire. Range low/high ends are the worst of these: `1-2
bands` is an explicitly *uncertain* count being recorded as a settled doublet.

**Minimal fix.** Negative lookbehind on the token before the number
(`Fig|Figure|Panel|lane|lanes|n|=|~|≥|>|<|-|–|to`), and cap `n` at a plausible
blot maximum (say 8) — above that it is almost certainly not a band count.

### B9 — `smear` conflates a technical artifact with a biological observation · MISLEADING

```
d("Smearing due to sample overloading was observed in lane 3.") -> smear, SUPPORTED
d("The gel showed smearing, indicating protein degradation")    -> smear, SUPPORTED
d("protein degradation caused smearing")                        -> smear, SUPPORTED
```

The project's own reference material classifies smearing as an artifact
category — `research/biologist_western_workflow.md`: "Smearing. Degradation,
overloading, or aggregation." — while the M2 motivation
(`research/demo_scientific_qa.md`, "poly-Ub conjugate smear") is a *biological*
smear. One field currently carries both meanings with no way to tell them
apart downstream, and the biological reading is the one a user searching for
"smear" will assume.

Note this is *not* fixed by "we're descriptive only". Descriptively both are
smears; the problem is that the consumer of `band_pattern = smear` reads it as
a statement about the protein.

**Minimal fix.** Don't try to classify — record the attribution and refuse to
settle. When the clause contains
`overload|degrad|aggregat|artifact|gel front|edge effect|bubble|background`,
keep `smear` as the value but set `status=AMBIGUOUS` and let `band_notes`
carry the attributing wording (it already captures verbatim text). One branch.

### B10 — The M2 motivating phrase degrades to `uncertain` · FALSE-NEGATIVE

```
d("a polyubiquitin smear was detected")
    -> {'pattern': 'uncertain', 'raw': 'smear; polyubiquitin smear', 'hedged': True}
d("poly-ubiquitin smear")
    -> {'pattern': 'uncertain', 'raw': 'smear; poly-ubiquitin smear', 'hedged': True}
```

`_BAND_SMEAR` and `_BAND_LADDER` both match the **same substring**, so
`len(kinds) > 1` fires the "several distinct patterns → do not pick a winner"
branch (`biology.py:292-296`). But these are not competing descriptions of the
blot — they are one description matched twice. The single phrase M2 was opened
to represent therefore lands as `uncertain`, and the feature does not close its
own motivating case for the most idiomatic wording of it.
(`"a high-molecular-weight smear of ubiquitin conjugates"` survives as `smear`
only because that particular ordering dodges the ladder regex.)

**Minimal fix.** Before declaring conflict, discard matches whose spans overlap
another match, keeping the longer (more specific) one. `polyubiquitin smear`
(ladder) subsumes `smear`, so one kind remains → `ladder`. This is what the
`BAND_PATTERNS` precedence tuple appears to have been intended for (see B11).

### B18 — `doublet` asserted on a multi-gene target label · MISLEADING

`eval/tools/build_responses_phospho_PMC12856536.py:116-137` records
`band_pattern: doublet, band_count: 2` for `P-ERK 1/2` and `T-ERK 1/2`.
ERK1 (44 kDa) and ERK2 (42 kDa) are **two different gene products**; the
project's own reference lists exactly this pair under *Isoforms — multiple gene
products / splice variants* (`research/biologist_western_workflow.md`). In WB
usage "doublet" normally implies one protein resolving into two forms
(modified/unmodified, cleaved/full-length) — a materially different claim from
"this antibody detects two proteins".

The record already knows the label is ambiguous — `canonical_target` resolves
to `MAPK1/MAPK3` with `status = AMBIGUOUS` and a `PROTEIN_AMBIGUOUS` flag — and
asserts the doublet at SUPPORTED anyway:

```
target: P-ERK 1/2  canonical: MAPK1/MAPK3 (AMBIGUOUS)  flags: ['PROTEIN_AMBIGUOUS']
 lane 1 "0 min" uncertain -> doublet 2
 lane 2 "5 min" present   -> doublet 2
```

The *observation* ("two closely spaced bands") is honest; the *field value* is
the problem, because `doublet` is read as a one-protein claim.

**Minimal fix.** No new inference needed — inherit the ambiguity: when
`target.canonical_target.status == AMBIGUOUS`, downgrade a doublet/multiple
pattern to `status=AMBIGUOUS`. Plus a contract line (C-new below) telling the
observer not to call a `X 1/2`-style row a doublet.

---

## 3. Low severity

### B11 — `BAND_PATTERNS` documented as precedence, never used as one · OK (doc bug)
`biology.py:252-253` says "order = precedence when several co-occur", but
`detect_band_pattern` never consults it: multi-kind → `uncertain`, otherwise
`found[0]` (fixed insertion order, which merely coincides with the tuple). Its
only real use is as a vocabulary allowlist in `record_builder.py:516`. Either
fix the comment or use it to implement B10.

### B12 — Observer `band_count` is unvalidated · FALSE-POSITIVE
```
band_pattern="uncertain", band_count=3  -> pattern AMBIGUOUS, count 3 SUPPORTED
band_pattern="single",    band_count=4  -> single, count 4     (no cross-check)
band_pattern="doublet",   band_count=True -> count 1           (bool is an int in Python)
band_pattern="doublet",   band_count=-7 -> count -7 SUPPORTED
band_pattern="doublet",   band_count="2" -> count MISSING       (string silently dropped)
```
Note the last one against the contract text, which writes the placeholder as a
**quoted string** (`"band_count": "<integer, ONLY if...>"`) — a model that
mirrors the shape emits `"2"` and the count is silently lost. Note also the
first: the deterministic path drops counts whenever hedged
(`biology.py:298-299`), the observer path does not — the same semantics,
enforced in one channel only.

**Minimal fix**, all inside `_band_pattern_fields`: reject `bool`, coerce
numeric strings, require `1 <= n <= 8`, drop the count when
`pattern == "uncertain"`, and drop (or flag) when the count contradicts the
pattern (`single` ≠ 1, `doublet` ≠ 2).

### B13 — `band_notes` falls back to the pattern word, then is rendered as a quote · MISLEADING (provenance)
`record_builder.py:518`: `raw = str(b.get("band_notes") or claim)`. With no
note supplied, `band_notes` becomes the literal string `"doublet"` with
`Source(type="image", text="doublet")`, and `EvidencePanel.tsx:374` renders it
inside curly quotes — *Pattern is descriptive (what the blot shows: "doublet")*
— which reads as a quotation from the paper. The evidence for "doublet" is the
word "doublet". Fix: leave `band_notes` MISSING when the claim carries no note.

### B14 — UI reuses one lane's notes for all lanes; ignores `band_pattern_status`
`EvidencePanel.tsx:372-376` takes `detail.bands.find(b => b.band_notes)?.band_notes`
— the first lane that happens to have notes — as the explanation for the whole
lane strip. `EvidencePanel.tsx:385-387` renders `b.band_pattern` in the same
colour regardless of status, although the API does expose
`band_pattern_status` (`api/app/record_detail.py:136-137`,
`api/app/schemas.py:144`). Today `AMBIGUOUS ⟺ value "uncertain"`, so it
self-labels — but that invariant is accidental and B12/B5 fixes would break it.
Cheap: colour AMBIGUOUS patterns GOLD like `band_state === 'uncertain'`, and use
each lane's own notes.

### B15 — `two immunoreactive bands` does not match · FALSE-NEGATIVE (harmless)
`_BAND_COUNT`'s adjective allowlist is `distinct|discrete|separate|major`:
```
d("two immunoreactive bands") -> None
d("two protein bands")        -> None
```
"Two immunoreactive bands" is among the most standard phrasings in the
literature. Harmless (abstention), but a real coverage gap. Only widen the
allowlist to a generic `(?:\w+\s+){0,2}bands?` *together with* the B8 guard —
alone it enlarges the false-positive surface.

---

## 4. Is MISSING ≠ single preserved end-to-end? — **Yes, verified**

| Layer | Behavior | Verdict |
|---|---|---|
| `BandObservation` | `band_pattern/count/notes` default to `EvidenceField.missing()` (`evidence_record.py:188-190`) | OK |
| Supabase projection | `to_supabase_rows` (`evidence_record.py:290-299`) does **not** project the three fields into flat columns at all — verified: `"band_pattern" in row` → `False`. They survive only inside the `provenance` JSONB envelope | OK |
| DB schema | `migrations/001_evidence_record.sql` adds no `band_pattern` column (only `band_state`, plus FUTURE `band_width/height/area_px`). No column ⇒ no SQL default and no NOT NULL can manufacture a "single" | OK |
| API | `record_detail.py:135-139` reads the envelopes out of `provenance` with `_v`, which returns `None` for a missing envelope; `RecordBand.band_pattern` is `str \| None` with default `None` | OK |
| UI | `EvidencePanel.tsx:385` renders the pattern only under `{b.band_pattern && ...}` — no fallback text, no "single" default | OK |

Two caveats worth naming:

1. **`record_detail._v` is weaker than `evidence_record._v`.** The API version
   (`api/app/record_detail.py:73-74`) returns `.get("value")` regardless of
   status, whereas the record version (`evidence_record.py:303-309`) nulls
   `CONFLICTING`/`MISSING`. Harmless today because the builder never produces a
   CONFLICTING `band_pattern` — but it would leak a disputed value the moment
   B5's recommended fix introduces one. Fix B5 and this together.
2. **`band_pattern` is not searchable.** Because there is no flat column, "find
   me the doublets" / "find the smears" is not expressible in search or filters
   — the field is detail-view-only. That is a defensible scope choice (it keeps
   an unsettled descriptive field out of query results), but it should be a
   stated decision rather than a side effect of the projection.

`band_state` independence also holds: a doublet/smear band remains
`band_state = present`, per `test_band_pattern_from_explicit_wording` and
confirmed in probes. The one gap is the *inverse* direction — `absent` +
`doublet` (B4).

## 5. What is genuinely safe — verified negatives

- **Molecular-weight markers do not fire.** `_BAND_LADDER` deliberately requires
  `ladder-like` or a polyubiquitin/high-MW qualifier, so the MW-marker sense of
  "ladder" is excluded: `"A prestained protein ladder was run in lane 1."`,
  `"Proteins were separated alongside a protein ladder (Thermo)."`,
  `"Molecular weight ladder positions are indicated on the left."` → all `None`.
  This is the most obvious trap in the whole feature and it is correctly avoided.
  (Only residual: `"PageRuler ladder-like markers"` → `ladder`, a phrasing that
  does not really occur.)
- **Quantification language does not fire.** `"Bands were quantified by
  densitometry."`, `"Band intensities were normalized to GAPDH."` → `None`.
  Correct — and important, since this is the densitometry boundary the schema
  refuses to cross.
- **Identity does not imply pattern.** `"Ubiquitin was analyzed by western
  blotting."` → no ladder; `"LC3B levels were analyzed by western blotting."` →
  MISSING. The stated non-negotiable holds.
- **Row count is not multiplicity** in the deterministic path
  (`test_multiple_rows_are_not_multiplicity`) — a phospho + total + loading
  control panel stays pattern-free. Note this is enforced only for the text
  channel; the observer channel is not told the same rule (C9).
- **Hedge over-triggering is conservative.** `"This band could not be
  resolved."` / `"difficult to interpret"` → `None`; `"It is unclear whether the
  extra band is specific."` → `uncertain`. Loss of a true positive, never a
  false assertion — acceptable.
- **`a single band was detected and no additional bands were present`** →
  `uncertain`. Over-conservative (the honest reading is `single`) but the safe
  direction. Fixing B1 also fixes this: with the negated clause dropped, only
  `single` remains.

## 6. Stage-2 OUTPUT_CONTRACT — observer-channel guardrails (`extract_records.py:61-81`)

The observer channel is the *only* channel that can assert a pattern from an
image, has the weakest provenance rank, and currently has absolute precedence
(B5) — so its contract wording is load-bearing. Gaps:

| # | Gap | Class | Suggested line |
|---|---|---|---|
| C1 | `single` is in the enum but the "report it when…" rule authorizes only "multiple bands, a doublet, a smear, or a ladder". A model reporting `single` from a crop is making an **antibody-specificity claim** from a cropped panel | MISLEADING | Remove `single` from the observer enum (keep it in the text channel, where the paper literally says it), or: "report `single` ONLY if the source text states it" |
| C2 | `uncertain` is in the enum while the rule says "Omit it when in doubt" — contradictory, and the two are different downstream (AMBIGUOUS renders in the UI, MISSING does not) | Med | Pick one. Prefer omission |
| C3 | No scoping rule. The text channel is clause-scoped to the target; the observer is never told to describe only this row | FALSE-POSITIVE | "band_pattern describes ONLY this target's own row, in this lane" |
| C4 | No marker-lane guardrail — the deterministic side handles this, the observer side is not warned | FALSE-POSITIVE | "Never describe the molecular-weight marker/ladder lane" |
| C5 | No artifact guardrail (mirrors B9) | MISLEADING | "Do not report a smear caused by overloading, gel-front artifacts, bubbles or background as this target's pattern" |
| C6 | No negation guardrail (mirrors B1) | MISLEADING | "'no additional bands' / 'no smearing' is not a pattern — omit" |
| C7 | `band_count` placeholder is a **quoted string**, so a shape-mirroring model emits `"2"` and the count is silently dropped (B12) | FALSE-NEGATIVE | Show it unquoted, and accept numeric strings in the builder |
| C8 | No consistency rules: nothing forbids `band_state: absent` + `band_pattern: doublet` (B4), or `single` + `band_count: 4` (B12) | MISLEADING | "band_pattern must be omitted when band_state is absent"; "band_count must agree with band_pattern" |
| C9 | The row-count rule exists only as a deterministic test, never in the contract — and mis-reading panel rows as bands is the most likely image error | FALSE-POSITIVE | "The number of TARGET ROWS in the panel is not a band count. Multiplicity belongs to one row's own lane" |
| C-new | Nothing forbids `doublet` on a two-gene label (B18) | MISLEADING | "If the row label names more than one gene (`ERK 1/2`, `p44/42`, `LC3B-I/II`), do not call it a doublet — the two bands are different proteins" |

## 7. Recommended order of work

Ship-blocking before this is shown to scientists as an asserted field:

1. **B1** negation guard (abstain, don't invert) — one helper in `biology.py`.
2. **B2** plural-only high-MW ladder — one regex edit.
3. **B3** text-derived pattern on a multi-lane row → AMBIGUOUS, count dropped —
   one branch in `_band_pattern_fields`.
4. **B4** `absent` lane ⇒ no pattern (or an anomaly flag) — one line.

Then, in the same pass if cheap: **B10** (overlapping-span merge, which is what
makes the M2 case actually work), **B6** (`and`/parenthesis split), **B12**
(count validation), **C1/C6/C8/C9** contract lines.

Deferrable: B7, B8, B9, B13, B14, B15, B18, B11, and the two §4 caveats.

Each of the four ship-blockers needs a regression test with the exact probe
string quoted above — the current suite passes on every one of them.
