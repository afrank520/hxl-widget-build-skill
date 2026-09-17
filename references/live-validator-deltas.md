# HXL live-validator deltas (the linter's rulebook)

These are the ways the **live** HXL Beta deploy validator diverges from the docs.
Each one was hit for real (org + date noted). The validator reports most of them
as a single opaque server-side NPE, not a named JSON path:

```
Failed to deploy widget content: Cannot invoke
"com.force.commons.collection.Pair.getFirst()" because the return value of
"java.util.Map.get(Object)" is null
```

So the same error text means many different authoring mistakes. `lint-widget.py`
encodes each delta below so the author gets an instant, named error instead.

**When you discover a NEW delta** (lint is clean but deploy still NPEs): run
`bisect-deploy.sh` to localize the section, add a row here, and extend
`lint-widget.py`. Keep this file and the linter in lock-step.

---

## Delta 1 -- `actions` map: was NPE-blocked, now DEPLOYABLE (WARN)

- **History:** through 2026-08-25 (bwam-general, api v67.0 AND v68.0), adding an
  `actions` map to ANY tile (button / link / icon) NPE'd the bundle deploy.
  Proven by bisect: sendMessage OR openLink, static OR bound content, every
  combination failed; the same tree without `actions` deployed clean.
- **Now:** as of **2026-08-26** the blocker is lifted. An `action/sendMessage`
  button deploys clean and fires on BOTH surfaces (Slackbot MCP + Agentforce
  LEX). The Client Profile Card ships one. Re-confirmed on **release 262 /
  api v67.0 (superslackdemo, 2026-09-02)**: `sendMessage` is used live 4x, and
  an **`action/openLink`** button deploys clean too (validate-only dry-run).
  Both action types are settled -- no longer "confirm@build".
- **Linter:** WARN (not ERROR) on any `actions` key, so if a future org release
  re-introduces the limit, a suddenly-NPEing deploy is easy to trace back here.
- **If it regresses:** ship the deployable subset; or wire the widget as an
  action's **Output Rendering** via Setup -> Agentforce Assets.

## Delta 2 -- button/icon `iconName` is a hard Lucide enum (~200 slugs)

- **The enum is large.** On release 262 the validator's rejection message prints
  the full allowed set; the CLI truncates it at ~750 chars, but the captured
  prefix already contains ~45 slugs: `activity, alert-circle, alert-triangle,
  align-*, bell, bookmark, box, braces, briefcase, building, calculator,
  calendar, caret-*, check, check-circle, chevron-*, circle, circle-dot, clock,
  cloud, code, component, copy, credit-card, crown, database, dashboard, divide,
  dollar-sign, dot, download, edit, equal, equal-not, eye, eye-off, file, ...`.
- **Verified FAIL (ERROR on 262):** `pie-chart`, `chart-pie`, `chart-bar`,
  `percent`, `scale`. (`pie-chart` rejection confirmed by dry-run 2026-09-02.)
- A miss NPEs with the SAME signature as a structural error.
- **Linter:** because the enum is far too big to allowlist, the strategy is:
  ERROR only on the known-FAIL chart slugs; soft-WARN a slug that isn't in the
  captured `ICON_KNOWN_GOOD` set (a partial capture + every slug the shipped
  cards use, so common valid icons like `bell`/`clock` do NOT false-WARN). Grow
  the set as more of the enum is captured; never ERROR on an uncaptured name.

## Delta 3 -- `tile/icon` `name` = Lucide slugs, not SLDS

- SLDS-style `email`, `home`, `contact` fail; use `mail`, `building`, `user`,
  `credit-card`, `calendar`, `check-circle`, etc.
- A bad name throws an NPE that kills the WHOLE widget
  ("An unexpected error occurred").
- **Linter:** ERROR on `email` / `contact`.

## Delta 4 -- `tile/container` `variant` enum + `borderless` is a separate boolean

- **The complete enum (captured verbatim from the 262 validator, 2026-09-02):**
  `default`, `emphasis`, `info`, `warning`, `error`, `success`. When a dry-run
  deployed `variant:borderless`, the validator rejected it and printed exactly
  this set. Anything outside it is a HARD reject.
- **`borderless` is NOT a variant value.** It is a separate **boolean** attribute
  on `tile/container` (`borderless: true | false`). The shipped cards carry it
  alongside `variant: "default"` (live read: 17x `false`, 2x `true`). Passing
  `borderless` as a `variant` string ERRORs.
- **History (corrected):** earlier notes listed the variant set as `{default,
  borderless}`. That was wrong on both counts -- `borderless` was never a variant,
  and the real enum has 6 values. Corrected 2026-09-02 against the live 262
  validator. Both shipped cards use `variant:"default"` + the `borderless` boolean.
- **Linter:** ERROR on a `variant` outside the 6-value enum (the validator hard-
  rejects it, so a WARN would under-report). Separately, ERROR if `borderless` is
  present but not a boolean.

## Delta 5 -- list / table attrs need `lightning__listType` + required `items`

- In the widget `schema.json`, a list attribute needs `lightning__listType` plus
  a **required** `items` schema. `objectType` for a list fails "properties
  missing". (Undocumented but validator-enforced.)
- Not yet lint-checked (lives in schema.json, not the widget JSON) -- candidate
  for a future check.

## Delta 6 -- you cannot DELETE a property from a deployed `schema.json`

- Removing a property is a breaking change and is rejected. Only add. Plan the
  attribute contract up front, or version the widget.

## Delta 7 -- proven-on-262, previously "confirm@build" or feared-limited

Verified live against **release 262 / api v67.0 (superslackdemo, 2026-09-02)** by
reading the live cards and by validate-only dry-runs. These retire earlier hedges:

- **`tile/progress` `shape:linear` with `color:primary`** deploys and is used
  live (linear bars). The build spec had linear progress as confirm@build -- done.
  (The ring-color caveat -- `primary` shows as a heavy black RING in Slackbot --
  is a client-render observation about circular rings only, not a validator rule.)
- **No 27-node ceiling.** clientProfileCard is live at **106 nodes**. Earlier
  "27-node validator ceiling" lore is FALSE. See `docs/KNOWN_LIMITATIONS.md`.
- **No low per-container child ceiling.** A 15-child container deploys clean.

## Non-NPE structural rules (documented, but easy to miss)

- `<uiResource>` must byte-match `<resourceName>` in the McpServerDefinition.
- `resourceUri` points at the **wrapper** CLT (`c__...Result`), NOT the widget
  or the payload CLT.
- Clients cache the template keyed by `resourceUri`; bump it (+ update the
  connector) when iterating, or Deactivate/Activate to clear a stale card.
