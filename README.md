# hxl-widget-build (Claude Code skill)

A [Claude Code](https://claude.com/claude-code) **skill** for building, linting,
deploying, and **actually rendering** Headless Experience Layer (HXL) custom UI
widgets — the rich cards that render Salesforce org data in Agentforce (LEX) and
in external AI clients (Claude, Slackbot, ChatGPT).

This is the skill counterpart to the
[hxl-widget-gallery](https://github.com/sfdc-qbranch-emu/hxl-widget-gallery)
reference build.

## What it gives you

- **A pre-deploy linter** — the HXL Beta validator reports authoring mistakes as
  a cryptic server-side NullPointerException with no location. The linter turns
  each known mistake into an instant, named, local error (saves ~10 deploy
  round-trips per bug).
- **A scaffolder** — generate all seven metadata pieces from one spec, with the
  binding anchor threaded byte-identically across the files that require it.
- **A render-surfaces playbook** — the enablement gates that decide whether a
  clean-deploying widget actually draws vs. shows as text: the `/custom/` gateway
  URL for external clients, the **AEA requirement** for native LEX, and why
  Coworker is engineering-gated today. Includes the disproven dead ends so you
  don't chase them.

## Install

Clone into your Claude Code user skills folder:

```bash
git clone https://github.com/afrank520/hxl-widget-build-skill.git \
  ~/.claude/skills/hxl-widget-build
```

Then in any Claude Code session, ask to build/set up an HXL widget — the skill
triggers automatically. To update later: `git -C ~/.claude/skills/hxl-widget-build pull`.

The scripts are dependency-free Python 3.9+ and run standalone, so you can also
use them without Claude Code:

```bash
python3 ~/.claude/skills/hxl-widget-build/scripts/lint-widget.py <widget>.json
```

## Contents

| Path | Purpose |
|---|---|
| `SKILL.md` | The skill entry point / runbook. |
| `scripts/lint-widget.py` | Standalone pre-deploy linter. |
| `scripts/scaffold.py` | Spec → the seven metadata pieces. |
| `scripts/bisect-deploy.sh` | Localizes an unknown deploy NPE by section prefix. |
| `references/render-surfaces-playbook.md` | Surface-enablement gates + dead ends. |
| `references/live-validator-deltas.md` | Where the live Beta validator diverges from the docs. |
| `references/binding-anchor.md` | The four-file byte-identity contract. |
| `assets/templates/` | Copy-paste skeletons for the seven pieces. |

## Note

HXL is a Beta API; the live deploy validator is the ultimate source of truth and
has diverged from the published docs in places. The `references/` files record
what was verified, against which org, and when.
