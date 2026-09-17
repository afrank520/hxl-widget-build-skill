---
name: hxl-widget-build
description: >-
  Build, lint, and deploy a Headless Experience Layer (HXL) custom UI widget --
  a UiWidgetBundle that renders real Salesforce org data as a rich card in an MCP
  client (Slackbot, Claude Desktop, ChatGPT) AND/OR as Agentforce action output
  in Lightning Experience. TRIGGER on: HXL, UiWidgetBundle, "widget", MCP widget,
  Agentforce widget, .uiwidget, CLT / renderer.json, "binding anchor", tile/*
  components, or any request to render org data as a card in an AI client, OR
  "set up HXL for this demo org" / "get HXL rendering" end-to-end. Use this to
  scaffold the seven metadata pieces, LINT a widget JSON before deploy (catches
  the cryptic Beta-validator NPEs instantly), deploy/activate, get the card
  actually RENDERING across surfaces (external Claude/Slack/ChatGPT + native LEX;
  Coworker is engineering-gated -- see the render-surfaces playbook), and localize
  a deploy failure by bisect.
version: 1.1.0
---

# hxl-widget-build

Build an HXL custom UI widget end to end. An HXL widget is **seven metadata
pieces** wired by ONE field name (the binding anchor). The value of this skill is
the **pre-deploy linter**: the HXL Beta validator reports authoring mistakes as a
cryptic server-side NullPointerException with no JSON path, so localizing one
costs ~10 slow deploy round-trips. The linter turns each known mistake into an
instant, named, local error.

## Freshness first

This skill is self-contained. Its own `references/` are the portable source of
truth -- read them first:
- `references/live-validator-deltas.md` -- the linter's rulebook (each way the
  live validator diverges from the docs, with the org + date it was verified).
- `references/binding-anchor.md` -- the four-file byte-identity contract.
- `references/render-surfaces-playbook.md` -- **read this whenever a widget
  deploys clean but shows as text, or the task is "get it rendering / set up HXL
  for this demo org."** The surface-enablement gates (AEA for LEX, `/custom/` URL
  for external clients, Coworker's engineering gate) and the disproven dead ends.

HXL is a Beta API, so the **live deploy validator is the ultimate source of
truth**; it has diverged from the published docs in several places, which is why
the deltas file exists and stays in lock-step with `lint-widget.py`.

Optional local enrichment (use if present on this machine -- NOT required, the
skill stands alone without it): the `hxl-widgets` playbook and the on-disk
`hxl-docs` vendor set carry the full `tile/*` component palette and the
end-to-end narrative. The gallery repo's own `docs/` (ARCHITECTURE, RUNBOOK,
MCP_ENABLEMENT) cover the same ground and ship alongside the widgets.

## Workflow

### 1. Spec
Gather: widget name, the binding-anchor field name, data source (existing Apex
class or "scaffold a stub"), channel (MCP / Agentforce LEX / both), and the
attribute contract (the fields the card shows).

### 2. Scaffold
Generate all seven pieces from one spec, with the binding anchor threaded
byte-identically across the four files that carry it (see
`references/binding-anchor.md`):
```bash
python3 scripts/scaffold.py --widget myCard --action MyAction --anchor data \
        --label "Get My Card" --out force-app/main/default
# or from a spec file (scaffold.py --print-spec writes a starter):
python3 scripts/scaffold.py --spec my-widget.json --out force-app/main/default
```
It emits UiWidgetBundle (JSON + schema + meta), Apex `@InvocableMethod`
(single-field wrapped return), Payload CLT, Wrapper CLT + renderer.json,
GenAiFunction (+ meta), and McpServerDefinition from `assets/templates/`, then
self-lints the emitted widget JSON. The generated UiWidgetBundle is a MINIMAL
one-container/one-markdown card that binds + deploys clean on 262 -- flesh out
the `tile/*` tree from there. The generated widget `schema.json` sets
`attributes.type: object` (the validator requires a schema keyword on
`attributes`, else it fails with "$.properties.attributes.type is missing").
To hand-author instead, the copy-paste skeletons are in `assets/templates/`
(see that folder's `README.md` for the placeholder list).

### 3. Lint (the big win -- ALWAYS run before deploy)
```bash
python3 scripts/lint-widget.py <path-to-widget>.json
```
- Exit 0 = clean (WARNs allowed). Exit 1 = at least one ERROR; fix before deploy.
- It ERRORs on hard NPE triggers: known-bad chart icon slugs, SLDS icon names, a
  `tile/container variant` outside the enum (`default, emphasis, info, warning,
  error, success`), and a non-boolean `borderless`. It WARNs on the softer stuff:
  an icon slug outside the captured Lucide set (the enum is ~200, too big to
  allowlist, so this is a reminder, not a block), multi-anchor renderer paths, and
  an `actions` map (deployable as of 2026-08-26, re-confirmed on release 262:
  sendMessage & openLink both deploy; the WARN flags it so a future Beta regression
  is caught, not silently blocked). Rulebook: `references/live-validator-deltas.md`.

### 4. Deploy
```bash
# .build / trial orgs are prod-classified -> set CONFIRM_PROD=1, and do NOT pass --test-level
CONFIRM_PROD=1 sf project deploy start --source-dir <widget-dir> --target-org <ORG> --wait 30 --json
```
Deploy order for separate deploys: Apex -> LightningTypes + UiWidget ->
GenAiFunction -> McpServerDefinition. Verify the Apex payload returns the
`<anchor>`-wrapped shape BEFORE blaming the widget.

### 5. Repair (only if deploy NPEs despite a clean lint)
That means a NEW live-validator delta the linter doesn't know yet. Localize it:
```bash
scripts/bisect-deploy.sh <widget>.json <widget-dir> <ORG> --confirm-prod
```
Then add the finding to `references/live-validator-deltas.md` AND extend
`lint-widget.py` so the next author gets it for free.

### 6. Activate + connect (runtime, not metadata)
MCP servers ship disabled. Setup -> MCP Servers -> Activate. Connect a client via
an External Client App (auth-code + PKCE, scopes `mcp_api` + `refresh_token`).
Template cache: clients key on `resourceUri` -- bump it (+ update the connector)
when iterating, or Deactivate/Activate to clear a stale card. The gallery repo's
`docs/MCP_ENABLEMENT.md` + `docs/RUNBOOK.md` carry the full activate/connect
steps for both Slackbot and Claude.

### 7. Make it RENDER across surfaces (the part that wastes days if skipped)
Deploying clean is NOT the same as rendering. If a surface shows plain text / a
generic auto-card, it is a surface-enablement gate, not a widget bug. **Read
`references/render-surfaces-playbook.md`** -- it is the end-to-end enablement
recipe (this is what "set up HXL for this demo org" mostly is). Fast summary:
- **External (Claude/Slack/ChatGPT):** use the `/custom/` gateway URL
  (`.../platform/mcp/v1/custom/<serverName>`). 404 = URL, not entitlement.
- **Native LEX:** the agent MUST be an **AEA**, not the legacy Agentforce
  Default/`InternalCopilot` (that renders text). Set the action's **Output
  Rendering** to the agent-path CLT. Rendering is **per-Channel** -- check the
  *Agentforce (LEX)* channel preview specifically.
- **Coworker:** engineering-gated rollout, org-by-org, no ETA. Not fixable by
  config today. Set this expectation with the user up front.
- **Do NOT chase these dead ends** (all disproven): patch level 14.4+,
  the `LightningTypesMcpIntegration` perm, or an `agenticApps`/channel subfolder
  in `renderer.json`. Details + why in the playbook.
- **CLI publish bug:** if `sf agent publish authoring-bundle` fails at its final
  retrieve-back (`MetadataTransferError`, empty message), build the AEA in the
  Builder UI instead. See the playbook.

### Human-in-the-loop note (for "set up HXL for this demo org")
A few steps require a human clicking in Setup or an OAuth login and cannot be
fully automated: activating the MCP server, creating/authorizing the External
Client App (+ ~30-min propagation), assigning the access permset, and building/
selecting the AEA. When running the end-to-end setup, do everything scriptable,
then hand the user a short exact checklist for these manual clicks.

## Files in this skill
- `scripts/scaffold.py` -- spec -> the seven pieces, anchor byte-identical across the four binding files (no deps, python 3.9-safe).
- `scripts/lint-widget.py` -- standalone pre-deploy linter (no deps, python 3.9-safe).
- `scripts/bisect-deploy.sh` -- localizes an unknown deploy NPE by section prefix.
- `references/live-validator-deltas.md` -- the linter's rulebook (keep in lock-step).
- `references/binding-anchor.md` -- the four-file byte-identity contract.
- `assets/templates/` -- the seven-piece file templates.

## Note for the Codex side
Claude Code runs this skill via the frontmatter trigger. Codex cannot invoke a
Claude skill, but the scripts are standalone -- run them directly:
`python3 scripts/lint-widget.py <widget>.json`. Achieve the same outcomes by
following this SKILL.md as a runbook.
