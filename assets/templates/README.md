# Seven-piece templates

Swap the `<PLACEHOLDERS>` and keep the shapes. The one token that must be
byte-identical across `Action.cls`, `payloadCLT.schema.json`,
`genAiFunction.output.schema.json`, and `wrapperCLT.renderer.json` is `<ANCHOR>`
(see `../../references/binding-anchor.md`).

Placeholders:
- `<WIDGET>`   widget / uiWidget API name (e.g. `myCard`)
- `<ACTION>`   Apex class name (e.g. `MyAction`)
- `<PAYLOAD>`  Apex inner payload class (e.g. `Payload`)
- `<ANCHOR>`   the binding-anchor field name (e.g. `data`)
- `<CLT>`      CLT base name (e.g. `myCard` -> `myCardOutputValues` / `myCardResult`)
- `<FUNC>`     GenAiFunction developer name (e.g. `Get_My_Card`)
- `<LABEL>`    human label (e.g. `Get My Card`)

Files:
- `Action.cls` -- Apex invocable, single-field wrapped return
- `payloadCLT.schema.json` -- Payload CLT
- `wrapperCLT.schema.json` + `wrapperCLT.renderer.json` -- Wrapper CLT (+ mapping)
- `genAiFunction.output.schema.json` + `genAiFunction.input.schema.json` -- displayable output
- `mcpServerDefinition.xml` -- publishes the tool, points at the wrapper CLT

The UiWidgetBundle JSON itself is composition-specific; author it from the
`tile/*` palette. The HXL Widget Gallery repo's `clientProfileCard` /
`opportunityCard` bundles are the worked references if you have it checked out.
Always run `../../scripts/lint-widget.py` on the bundle JSON before deploy.
