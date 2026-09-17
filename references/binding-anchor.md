# The binding anchor -- the one thing that silently breaks everything

An HXL widget threads ONE field name through FOUR files. Call it `<anchor>`
(e.g. `clientProfile`). It MUST be byte-identical in all four, or the tool fires
but the client falls back to a generic auto-card (no error, just wrong output).

| # | File | What holds the anchor |
|---|------|-----------------------|
| 1 | **Apex** `classes/<Action>.cls` | the `@InvocableMethod` returns `List<Response>` where `Response` has ONE `@InvocableVariable` field named `<anchor>`, typed as the payload inner class |
| 2 | **Payload CLT** `lightningTypes/<x>OutputValues/schema.json` | a single property `<anchor>` typed `@apexClassType/c__<Class>$<Payload>` |
| 3 | **GenAiFunction** `genAiFunctions/<Name>/output/schema.json` | a single property `<anchor>`, same apexClassType, with `copilotAction:isDisplayable: true` |
| 4 | **Wrapper CLT** `lightningTypes/<x>Result/renderer.json` | every mapping reads `{!$attrs.outputValues.<anchor>.<field>}` |

## The classic trap: a FLAT `List<Payload>` return

A flat list produces `outputValues.<field>` directly, but the CLTs/renderer
expect `outputValues.<anchor>.<field>`. Result: silent no-bind even though the
widget renders. ALWAYS wrap the return in a single-field response class.

## What the linter can and cannot check

- `lint-widget.py` best-effort checks the wrapper `renderer.json`: if it finds
  more than one distinct `outputValues.<X>.` prefix, it WARNs (there should be
  exactly one anchor).
- It CANNOT cross-check the Apex field name or the CLT property names without
  parsing Apex + two schema files -- that stays a manual review step. When
  scaffolding, the generator writes the same `<anchor>` token into all four,
  which is the reliable way to keep them in sync.

## Deploy order (separate deploys, top-down)

Apex -> LightningTypes (payload + wrapper) + UiWidget -> GenAiFunction ->
McpServerDefinition. A single-package deploy auto-resolves the order.
