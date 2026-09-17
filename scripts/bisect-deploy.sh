#!/usr/bin/env bash
# bisect-deploy.sh -- localize which top-level widget section trips the HXL
# Beta deploy NPE, by deploying progressively larger prefixes of the section
# list until one fails.
#
# WHY: the Beta validator reports authoring errors as a generic server-side NPE
# with no JSON path. When lint-widget.py comes back clean but deploy still NPEs
# (a NEW live-validator delta we haven't catalogued yet), this automates the
# manual "strip sections, redeploy, see where it breaks" bisect we ran by hand.
#
# Run lint-widget.py FIRST -- this script is the fallback for unknown deltas,
# not the first line of defense (deploys are slow; the linter is instant).
#
# Usage:
#   bisect-deploy.sh <widget.json> <widget-dir> <org-alias> [--confirm-prod]
#     <widget.json>  path to the bundle JSON (inside <widget-dir>)
#     <widget-dir>   the uiWidgets/<name>/ dir passed to --source-dir
#     <org-alias>    target org
#     --confirm-prod prefix CONFIRM_PROD=1 (needed for .build/trial orgs)
#
# Requires: jq, sf CLI v2. Assumes the section list lives at
#   .contentBody.widgetBody.children[0].children[0].children
# (the standard clientProfileCard shape). Edit SECTION_PATH if yours differs.

set -euo pipefail

WIDGET_JSON="${1:-}"
WIDGET_DIR="${2:-}"
ORG="${3:-}"
CONFIRM="${4:-}"
SECTION_PATH='.contentBody.widgetBody.children[0].children[0].children'

if [ -z "$WIDGET_JSON" ] || [ -z "$WIDGET_DIR" ] || [ -z "$ORG" ]; then
  echo "usage: bisect-deploy.sh <widget.json> <widget-dir> <org-alias> [--confirm-prod]" >&2
  exit 2
fi

PREFIX=""
if [ "$CONFIRM" = "--confirm-prod" ]; then
  PREFIX="CONFIRM_PROD=1"
fi

BACKUP="$(mktemp)"
cp "$WIDGET_JSON" "$BACKUP"
restore() { cp "$BACKUP" "$WIDGET_JSON"; rm -f "$BACKUP"; }
trap restore EXIT

N=$(jq "$SECTION_PATH | length" "$WIDGET_JSON")
echo "[INFO] $(date -u +%FT%TZ) widget has $N top-level sections; bisecting against $ORG"

FIRST_BAD=-1
for ((k=1; k<=N; k++)); do
  # Write a variant keeping only the first k sections.
  jq "${SECTION_PATH} |= .[0:$k]" "$BACKUP" > "$WIDGET_JSON"
  echo "[INFO] $(date -u +%FT%TZ) deploying prefix of $k/$N section(s)..."
  if eval "$PREFIX sf project deploy start --source-dir '$WIDGET_DIR' --target-org '$ORG' --wait 30 --json" \
       > /tmp/bisect_deploy_out.json 2>&1; then
    echo "[INFO]   -> $k sections OK"
  else
    echo "[ERROR]  -> FAILED at section index $((k-1)) (the ${k}th section)."
    echo "[ERROR]     Offending section definition:"
    jq -r "${SECTION_PATH}[$((k-1))].definition // \"(no definition key)\"" "$BACKUP"
    echo "[ERROR]     Deploy output: /tmp/bisect_deploy_out.json"
    FIRST_BAD=$((k-1))
    break
  fi
done

if [ "$FIRST_BAD" -lt 0 ]; then
  echo "[INFO] All $N sections deployed clean -- no single-section culprit. The"
  echo "[INFO] NPE may need a nested-attribute bisect (recurse into the bad row)."
else
  echo ""
  echo "[RESULT] First failing section = index $FIRST_BAD. Inspect its attributes"
  echo "[RESULT] against references/live-validator-deltas.md, add the new delta,"
  echo "[RESULT] and extend lint-widget.py so the next author gets an instant error."
fi
echo "[INFO] widget JSON restored from backup."
