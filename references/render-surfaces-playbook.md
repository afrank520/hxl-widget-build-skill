# Make it actually render: the surface-enablement playbook

A widget can deploy 100% clean and still show as **plain text / a generic
auto-card** instead of the rich card. That is almost never a widget bug -- it is
a **surface-enablement** problem. Rendering happens on THREE independent paths,
each gated by different things. Fixing one does NOT fix the others. Debug them
separately, and set expectations per surface up front.

This file is the hard-won knowledge from a Fins wealth-advisor demo build
(Sept 2026), where localizing these gates cost ~3 sessions. Follow it and skip that.

---

## The three render paths (what works, what to expect)

| Surface | Works today? | What gates it |
|---|---|---|
| **External: Claude / Slack / ChatGPT** | ✅ Yes | Correct hosted-MCP gateway URL + External Client App OAuth |
| **Native: Agentforce panel in Lightning Experience (LEX)** | ✅ Yes | **Agent type must be an AEA** (see below) + per-channel renderer |
| **Native: Coworker** | ❌ Not yet (as of 2026-09) | **Engineering-gated rollout, org-by-org, no ETA.** Nothing you configure fixes it. |

Tell the user this at the START so they don't chase Coworker. If the demo needs
Coworker, the only paths are: (a) get the org flagged for the CLT-in-Coworker
capability by the HXL team, or (b) use an org that already has it.

---

## Gate #1 (external clients): the `/custom/` URL segment

Custom hosted MCP servers are reached at:
- ✅ `https://api.salesforce.com/platform/mcp/v1/custom/<serverName>`
- ❌ `https://api.salesforce.com/platform/mcp/v1/<serverName>`  (404 "Server definition not found")

The bare `.../v1/<serverName>` form ONLY works for 1P servers (e.g. headless-360,
whose qualified name already carries its namespace). A custom server's qualified
name is `custom/<name>`. Sandbox variant: `https://test.api.salesforce.com/...`.

If tools/list 404s: it is the URL, not an entitlement/publish/stale-bean issue.
A 404 (not 401) means auth is fine. Diagnose the URL fully before escalating.

Reuse ONE localhost callback port across servers on the same External Client App
(mismatched port -> redirect_uri_mismatch). Log out of other SF orgs before the
client OAuth. ~30-min ECA propagation wait is normal after creating the app.

## Gate #2 (native LEX): use an AEA, not the legacy default agent

**This was THE fix for native LEX rendering.** If LEX shows the payload as text
even though the action fires and returns the full structured data:

- The gate is **agent type**. A legacy **Agentforce Default / `InternalCopilot`**
  agent renders the CLT as text. Rebuild as an **Agentscript AEA** (Agentforce
  Employee Agent) and the card renders in the LEX side panel.
- Building the AEA in the **Builder UI** sidesteps a CLI publish bug (see below).
- Confirm the action's **Output Rendering** is set to the agent-path CLT: Setup ->
  Agentforce Assets -> **Actions** -> open the action -> editable **Output
  Rendering** field. (The topic-side "View Action" panel is READ-ONLY and its
  "Map to Variable" box is NOT where rendering is set -- CLTs never appear there.)

**Rendering is per-Channel.** In Setup -> Lightning Types -> your CLT -> **UI
Configuration**, the Channel dropdown (Agentforce LEX / Enhanced Chat v2 /
Agentforce Mobile / ...) each has its own renderer preview. The SAME correct CLT
draws the full card on **Agentforce (LEX)** but flattens to text on **Enhanced
Chat v2** and shows "preview not supported" on **Mobile**. Text on one channel
does not mean the CLT is broken -- check the LEX channel preview.

## Gate #3 (Coworker): engineering-gated, out of your hands

Confirmed directly by the HXL team (Raveesh Raina, 2026-09): CLT-in-Coworker is
"currently gated by the engineering teams, rolling out to orgs worldwide, no
timeline." Corroborated by official docs: the HXL "Build Rich UI" supported-
platforms list is LEX + ChatGPT + Claude + Slackbot only (Coworker absent); the
official Coworker customize doc only covers Search Manager + search layouts.
Symptom on an ungated org: CLT resolves + data binds but the composed tile/
button/badge layout flattens. **No renderer.json change fixes this.**

---

## Dead ends -- do NOT spend time on these (all disproven in the field)

- **Patch level.** "Needs Summer '26 Patch 14.4+" is a red herring for the text
  problem. Org was on 262.14.17 and LEX still showed text until the AEA rebuild;
  another user saw Coworker flatten on 14.10. Patch is not the native-render gate.
- **`LightningTypesMcpIntegration` perm.** Enabling it did NOT fix native LEX text.
- **An `agenticApps` (or any channel-specific) subfolder in renderer.json.** An
  AXL support-bot suggested this; it is wrong for widget-backed CLTs. Per the HXL
  doc, widget CLTs use a **root-level** `renderer.json` with **NO** channel
  subfolders. Channel subfolders (e.g. `lightningDesktopGenAi/`) are an LWC-
  override pattern, not a widget pattern. Our root-level renderer is already correct.

---

## Known CLI bug on some orgs: `sf agent publish authoring-bundle`

On orgs with broken `AnswerQuestionsWithKnowledge` GenAiFunctions (missing
input/output schemas), `sf agent publish authoring-bundle` deterministically
fails at its final client-side metadata retrieve-back
(`MetadataTransferError: Metadata retrieval failed:` empty message) -- the broken
functions poison the org-wide retrieve. Server-side work still succeeds, leaving a
half-registered "ghost" agent (visible in legacy Setup, absent from Studio/
Builder, not editable). **Workaround: build the AEA in the Builder UI instead.**

---

## Post-wire verification (do this before declaring a surface "done")

For each surface the demo needs:
1. **External:** in the AI client, ask the question that triggers the tool; confirm
   the rich card draws (not text). If 404 -> check the `/custom/` URL (Gate #1).
2. **LEX:** open the relevant record -> agent side panel -> invoke the action;
   confirm the card draws. If text -> confirm agent is an AEA (Gate #2) and the
   action's Output Rendering points at the agent-path CLT.
3. **Coworker:** expect it NOT to render today (Gate #3). Only revisit if the HXL
   team confirms the org is flagged for the capability.
