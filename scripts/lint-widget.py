#!/usr/bin/env python3
# lint-widget.py -- static pre-deploy checks for an HXL UiWidgetBundle.
#
# WHY THIS EXISTS: the HXL Beta deploy validator reports authoring mistakes as
# a cryptic server-side NullPointerException
# ("Cannot invoke ...Pair.getFirst() because ...Map.get(Object) is null")
# instead of naming the bad JSON path. Localizing one takes ~10 deploy
# round-trips of manual bisecting. Every check here maps to a failure mode we
# have hit live in bwam-general (2026-08-25) and turns it into an instant,
# named, local error.
#
# 3.9-SAFE ON PURPOSE: system python3 on the author's Mac is 3.9.6. No `X | None`
# type hints, no 3.10+ syntax. Runs standalone (no deps) so the Codex side and
# CI can call it directly:  python3 lint-widget.py <path-to-widget.json> [more...]
#
# EXIT CODES: 0 = clean (warnings allowed), 1 = at least one ERROR, 2 = usage.

import json
import re
import sys

# --- verified-live enums (superslackdemo, HXL Beta, release 262 / api v67.0, 2026-09-02) ---
# Button/icon iconName is a HARD Lucide enum (~200 slugs). A miss NPEs with the
# same signature as a structural error. The enum is far too large to allowlist,
# so the strategy is: ERROR on the known-bad chart slugs, and only soft-WARN a
# name that isn't in the captured-known-good set below (the set is a partial
# capture of the 262 validator enum + every slug the shipped cards use live, so
# a common valid icon like `bell`/`clock` does NOT false-WARN).
#
# ICON_FAIL: proven to ERROR on 262 (validator rejected `pie-chart`; the rest are
# the same chart-family SLDS-isms that share its failure mode).
ICON_FAIL = {"pie-chart", "chart-pie", "chart-bar", "percent", "scale"}

# ICON_KNOWN_GOOD: partial capture of the 262 tile/icon `name` Lucide enum (the
# CLI truncates the validator's full list at ~750 chars) UNION the slugs the two
# shipped gallery cards use live. Anything here is silent; anything outside is a
# soft-WARN, never an ERROR (we can't prove a name is invalid unless it's in
# ICON_FAIL). Grow this set as more of the enum is captured.
ICON_KNOWN_GOOD = {
    # live-used by the shipped cards
    "activity", "bell", "building", "calendar", "check-circle", "clock",
    "credit-card", "trending-up", "user", "users", "mail",
    # captured prefix of the 262 validator enum
    "alert-circle", "alert-triangle", "align-center",
    "align-horizontal-space-between", "align-left", "align-right",
    "align-vertical-space-between", "bookmark", "box", "braces", "briefcase",
    "calculator", "caret-down", "caret-left", "caret-right", "caret-up",
    "check", "chevron-down", "chevron-left", "chevron-right", "chevron-up",
    "circle", "circle-dot", "cloud", "code", "component", "copy", "crown",
    "database", "dashboard", "divide", "dollar-sign", "dot", "download",
    "edit", "equal", "equal-not", "eye", "eye-off", "file",
}

# tile/container `variant`: the COMPLETE enum, captured verbatim from the 262
# validator (it rejected `variant:borderless` and printed the full allowed set).
# Anything outside this set is an ERROR -- the validator hard-rejects it.
CONTAINER_VARIANT_OK = {"default", "emphasis", "info", "warning", "error", "success"}
# `borderless` is NOT a variant value -- it is a SEPARATE boolean attribute on
# tile/container (`borderless: true|false`). The shipped cards carry it alongside
# `variant: "default"`. It was mistaken for a variant value in earlier docs.


class Finding(object):
    def __init__(self, level, path, msg):
        self.level = level      # "ERROR" | "WARN"
        self.path = path        # JSON pointer-ish path for the operator
        self.msg = msg

    def render(self):
        return "  [%s] %s\n         %s" % (self.level, self.path, self.msg)


def walk(node, path, findings):
    """Recurse the tile tree, applying per-component checks."""
    if isinstance(node, list):
        for i, item in enumerate(node):
            walk(item, "%s[%d]" % (path, i), findings)
        return
    if not isinstance(node, dict):
        return

    definition = node.get("definition")
    attrs = node.get("attributes")
    if isinstance(attrs, dict):
        _check_attrs(definition, attrs, path + ".attributes", findings)

    # Recurse every dict/list value so we catch tiles at any depth.
    for key, val in node.items():
        walk(val, "%s.%s" % (path, key), findings)


def _check_attrs(definition, attrs, path, findings):
    # 1. actions map -- deployable as of 2026-08-26 (bwam-general, api v67).
    # It was previously blocked (server-side NPE via bisect on 2026-08-25); the
    # blocker was lifted, and an `action/sendMessage` button now deploys and
    # fires on BOTH surfaces (Slackbot MCP + Agentforce LEX). We WARN only so a
    # new org release regressing this surfaces as a reminder to retest.
    if "actions" in attrs:
        findings.append(Finding(
            "WARN", path + ".actions",
            "An `actions` map is present. This is deployable as of 2026-08-26 "
            "(verified in bwam-general, api v67, sendMessage). It was NPE-blocked "
            "before then, so if a deploy suddenly NPEs on the bundle after an org "
            "release, re-bisect this map and check for a re-introduced Beta limit."))

    # 2. iconName Lucide enum (button + icon tiles).
    icon = attrs.get("iconName")
    if isinstance(icon, str):
        if icon in ICON_FAIL:
            findings.append(Finding(
                "ERROR", path + ".iconName",
                "iconName '%s' is a known-BAD chart slug that the validator "
                "rejects (NPEs the bundle). Use a valid Lucide slug." % icon))
        elif icon not in ICON_KNOWN_GOOD:
            findings.append(Finding(
                "WARN", path + ".iconName",
                "iconName '%s' is not in the captured-known-good Lucide set. "
                "Lucide slugs only (not SLDS). The set is a partial capture of "
                "the full ~200-slug enum, so a valid icon can land here -- this "
                "is a soft reminder to verify, not a block." % icon))

    # 3. tile/icon `name` is also Lucide (email/home/contact fail; use mail etc).
    if definition == "tile/icon":
        name = attrs.get("name")
        if isinstance(name, str) and name in {"email", "contact"}:
            findings.append(Finding(
                "ERROR", path + ".name",
                "tile/icon name '%s' is an SLDS slug and NPEs the widget. Use a "
                "Lucide slug (mail, user, building, ...)." % name))

    # 4. tile/container `variant`: ERROR on a value outside the captured enum.
    # The 262 validator printed the COMPLETE allowed set when it rejected
    # `variant:borderless`, so anything outside it is a hard reject, not a maybe.
    if definition == "tile/container":
        variant = attrs.get("variant")
        if isinstance(variant, str) and variant not in CONTAINER_VARIANT_OK:
            findings.append(Finding(
                "ERROR", path + ".variant",
                "tile/container variant '%s' is not in the validator enum (%s). "
                "The 262 validator hard-rejects any other value. NOTE: "
                "`borderless` is NOT a variant -- it is a separate boolean attr "
                "(`borderless: true|false`)." % (
                    variant, ", ".join(sorted(CONTAINER_VARIANT_OK)))))

        # borderless must be a boolean attribute, not a string/variant.
        borderless = attrs.get("borderless")
        if borderless is not None and not isinstance(borderless, bool):
            findings.append(Finding(
                "ERROR", path + ".borderless",
                "tile/container `borderless` must be a boolean (true|false), got "
                "%r. It is an attribute in its own right, distinct from `variant`."
                % (borderless,)))


def check_binding_anchor(widget_path, findings):
    """
    The binding anchor is one field name threaded byte-identical through four
    files. This checks the two we can see from the widget dir: the wrapper CLT
    renderer.json path prefix vs the payload CLT property. Best-effort -- it
    only fires if it can locate sibling lightningTypes dirs.
    """
    import os
    # widget: force-app/main/default/uiWidgets/<name>/<name>.json
    default_dir = os.path.abspath(os.path.join(os.path.dirname(widget_path), "..", ".."))
    lt_dir = os.path.join(default_dir, "lightningTypes")
    if not os.path.isdir(lt_dir):
        return
    renderers = []
    for root, _dirs, files in os.walk(lt_dir):
        if "renderer.json" in files:
            renderers.append(os.path.join(root, "renderer.json"))
    for rj in renderers:
        try:
            with open(rj) as fh:
                data = json.load(fh)
        except (ValueError, IOError):
            continue
        text = json.dumps(data)
        anchors = set(re.findall(r"outputValues\.([A-Za-z0-9_]+)\.", text))
        if len(anchors) > 1:
            findings.append(Finding(
                "WARN", rj,
                "renderer.json references more than one anchor under "
                "outputValues (%s). The binding anchor must be ONE field name "
                "byte-identical across all four files." % ", ".join(sorted(anchors))))


def lint_file(widget_path):
    findings = []
    try:
        with open(widget_path) as fh:
            data = json.load(fh)
    except ValueError as exc:
        findings.append(Finding("ERROR", widget_path, "Not valid JSON: %s" % exc))
        return findings
    except IOError as exc:
        findings.append(Finding("ERROR", widget_path, "Cannot read: %s" % exc))
        return findings

    walk(data, "$", findings)
    check_binding_anchor(widget_path, findings)
    return findings


def main(argv):
    if len(argv) < 2:
        sys.stderr.write("usage: lint-widget.py <widget.json> [more.json ...]\n")
        return 2

    total_errors = 0
    for wp in argv[1:]:
        findings = lint_file(wp)
        errors = [f for f in findings if f.level == "ERROR"]
        warns = [f for f in findings if f.level == "WARN"]
        total_errors += len(errors)
        status = "FAIL" if errors else ("WARN" if warns else "OK")
        print("== %s  [%s]" % (wp, status))
        for f in findings:
            print(f.render())
        if not findings:
            print("  (no issues)")
    print("\n%d error(s) across %d file(s)." % (total_errors, len(argv) - 1))
    return 1 if total_errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
