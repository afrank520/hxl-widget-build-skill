#!/usr/bin/env python3
# scaffold.py -- generate the 7-piece HXL widget stack from one spec.
#
# WHY THIS EXISTS: an HXL widget is not one file, it is SEVEN metadata pieces
# wired by ONE binding anchor -- a single field name that must be BYTE-IDENTICAL
# across four of them (Apex response field -> payload CLT property -> GenAiFunction
# output property -> wrapper CLT renderer path). Hand-authoring the set and keeping
# that anchor in lockstep is the #1 failure mode (a one-character drift = a silent
# no-bind that looks like "the widget didn't render"). This generator emits all
# seven from a spec so the anchor is threaded correctly by construction, then lints
# the widget JSON it produced.
#
# 3.9-SAFE ON PURPOSE: system python3 on the author's Mac is 3.9.6. No `X | None`
# hints, no 3.10+ syntax, no deps. Mirrors lint-widget.py so CI/Codex can call it.
#
# USAGE:
#   scaffold.py --spec <spec.json> --out force-app/main/default
#   scaffold.py --widget myCard --action MyAction --anchor data \
#               --label "Get My Card" [--payload Payload] [--clt myCard] \
#               [--func Get_My_Card] --out force-app/main/default
#   scaffold.py --print-spec        # write a starter spec to stdout
#
# EXIT CODES: 0 = generated + lint clean, 1 = generated but lint found ERRORs,
#             2 = usage / bad spec.

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATES = os.path.join(HERE, "..", "assets", "templates")

# Spec keys and how to default the optional ones off the required base names.
# Required: widget, action, anchor, label. Derived if omitted: payload, clt, func.
REQUIRED = ("widget", "action", "anchor", "label")

# API-name shape guard: start with a letter, then letters/digits/underscore. This
# is what the anchor + developer names must satisfy to survive the validator.
API_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


def die(msg, code=2):
    sys.stderr.write("scaffold.py: %s\n" % msg)
    sys.exit(code)


def starter_spec():
    return {
        "widget": "myCard",
        "action": "MyAction",
        "payload": "Payload",
        "anchor": "data",
        "clt": "myCard",
        "func": "Get_My_Card",
        "label": "Get My Card",
    }


def load_spec(args):
    if args.spec:
        try:
            with open(args.spec) as fh:
                spec = json.load(fh)
        except (IOError, ValueError) as exc:
            die("cannot read --spec %s: %s" % (args.spec, exc))
    else:
        spec = {}
    # CLI flags override / fill the spec.
    for key in ("widget", "action", "payload", "anchor", "clt", "func", "label"):
        val = getattr(args, key, None)
        if val:
            spec[key] = val
    # Defaults for the optional pieces.
    spec.setdefault("payload", "Payload")
    spec.setdefault("clt", spec.get("widget", ""))
    if not spec.get("func") and spec.get("label"):
        # "Get My Card" -> "Get_My_Card"
        spec["func"] = re.sub(r"\s+", "_", spec["label"].strip())
    return spec


def validate_spec(spec):
    missing = [k for k in REQUIRED if not spec.get(k)]
    if missing:
        die("spec is missing required key(s): %s" % ", ".join(missing))
    # The anchor and developer-name fields must be safe API names. The label is
    # free text; everything else feeds a metadata identifier.
    for key in ("widget", "action", "payload", "anchor", "clt", "func"):
        if not API_NAME.match(spec[key]):
            die("spec.%s = %r is not a valid API name "
                "(letter, then letters/digits/underscore)" % (key, spec[key]))


def substitute(text, spec):
    """Replace every <PLACEHOLDER> token. Order is irrelevant -- tokens are
    disjoint. The anchor lands byte-identically wherever <ANCHOR> appears."""
    return (text
            .replace("<WIDGET>", spec["widget"])
            .replace("<ACTION>", spec["action"])
            .replace("<PAYLOAD>", spec["payload"])
            .replace("<ANCHOR>", spec["anchor"])
            .replace("<CLT>", spec["clt"])
            .replace("<FUNC>", spec["func"])
            .replace("<LABEL>", spec["label"]))


def read_template(name):
    path = os.path.join(TEMPLATES, name)
    try:
        with open(path) as fh:
            return fh.read()
    except IOError as exc:
        die("cannot read template %s: %s (run from a repo checkout with "
            "assets/templates/ present)" % (name, exc))


def write_out(path, content, written):
    d = os.path.dirname(path)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    with open(path, "w") as fh:
        fh.write(content)
        if not content.endswith("\n"):
            fh.write("\n")
    written.append(path)


def minimal_widget_json(spec):
    """A minimal, deploy-valid UiWidgetBundle. One tile/container (variant
    'default' + the borderless boolean, both verified on 262) holding a
    tile/markdown bound to the anchor's title. The author fleshes out the
    tile/* tree from here; this is the smallest thing that binds + deploys.
    The id values are fixed placeholders -- swap for real uuids if you deploy
    two scaffolds side by side (duplicate ids in one bundle are fine, across
    bundles they don't collide)."""
    return {
        "type": "lightning__agentforceWidget",
        "title": spec["label"],
        "contentBody": {
            "widgetBody": {
                "definition": "tile/widget",
                "id": "00000000-0000-0000-0000-000000000000",
                "children": [
                    {
                        "definition": "tile/container",
                        "attributes": {"variant": "default", "borderless": False},
                        "id": "00000000-0000-0000-0000-000000000001",
                        "children": [
                            {
                                "definition": "tile/markdown",
                                "attributes": {"source": "{!$attrs.title}"},
                                "id": "00000000-0000-0000-0000-000000000002",
                            }
                        ],
                    }
                ],
            }
        },
    }


def minimal_widget_schema(spec):
    """The widget schema.json. Shape verified against the live cards on 262:
    top-level type=object with a `properties.attributes.properties` map. The
    scaffold declares the two attrs the minimal composition binds (title, rows).
    Add more as the composition grows -- but note you can ADD but never DELETE a
    property from a deployed schema (see live-validator-deltas.md Delta 6)."""
    # The validator requires `attributes` to carry a schema keyword
    # (`type`/`lightning:type`/`oneOf`/...). `"type": "object"` is the minimum
    # -- omitting it fails validate with "$.properties.attributes.type is
    # missing but it is required" (proven on 262, 2026-09-02).
    return {
        "title": "%s Widget" % spec["label"],
        "description": spec["label"],
        "type": "object",
        "properties": {
            "attributes": {
                "type": "object",
                "properties": {
                    "title": {
                        "title": "Title",
                        "description": "Card title",
                        "lightning:type": "lightning__textType",
                    }
                }
            }
        },
    }


def widget_meta_xml(spec):
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<UiWidgetBundle xmlns="http://soap.sforce.com/2006/04/metadata">\n'
        '    <masterLabel>%s</masterLabel>\n'
        '    <description>%s</description>\n'
        '    <widgetType>JSON</widgetType>\n'
        '</UiWidgetBundle>\n' % (spec["label"], spec["label"])
    )


def class_meta_xml():
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<ApexClass xmlns="http://soap.sforce.com/2006/04/metadata">\n'
        '    <apiVersion>67.0</apiVersion>\n'
        '    <status>Active</status>\n'
        '</ApexClass>\n'
    )


def genaifunction_meta_xml(spec):
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<GenAiFunction xmlns="http://soap.sforce.com/2006/04/metadata">\n'
        '    <description>%s</description>\n'
        '    <developerName>%s</developerName>\n'
        '    <invocationTarget>%s</invocationTarget>\n'
        '    <invocationTargetType>apex</invocationTargetType>\n'
        '    <isConfirmationRequired>false</isConfirmationRequired>\n'
        '    <isIncludeInProgressIndicator>false</isIncludeInProgressIndicator>\n'
        '    <localDeveloperName>%s</localDeveloperName>\n'
        '    <masterLabel>%s</masterLabel>\n'
        '</GenAiFunction>\n'
        % (spec["label"], spec["func"], spec["action"], spec["func"], spec["label"])
    )


def generate(spec, out_dir):
    """Emit the full stack under out_dir (expected: force-app/main/default).
    Returns (written_paths, widget_json_path)."""
    written = []
    widget = spec["widget"]
    action = spec["action"]
    clt = spec["clt"]
    func = spec["func"]

    # 1. UiWidgetBundle: <widget>.json + schema.json + -meta.xml
    wdir = os.path.join(out_dir, "uiWidgets", widget)
    widget_json = os.path.join(wdir, "%s.json" % widget)
    write_out(widget_json,
              json.dumps(minimal_widget_json(spec), indent=2), written)
    write_out(os.path.join(wdir, "schema.json"),
              json.dumps(minimal_widget_schema(spec), indent=2), written)
    write_out(os.path.join(wdir, "%s.uiwidget-meta.xml" % widget),
              widget_meta_xml(spec), written)

    # 2. Apex action + meta
    cdir = os.path.join(out_dir, "classes")
    write_out(os.path.join(cdir, "%s.cls" % action),
              substitute(read_template("Action.cls"), spec), written)
    write_out(os.path.join(cdir, "%s.cls-meta.xml" % action),
              class_meta_xml(), written)

    # 3. Payload CLT (lightningType): <clt>OutputValues/schema.json
    payload_dir = os.path.join(out_dir, "lightningTypes", "%sOutputValues" % clt)
    write_out(os.path.join(payload_dir, "schema.json"),
              substitute(read_template("payloadCLT.schema.json"), spec), written)

    # 4. Wrapper CLT: <clt>Result/schema.json + renderer.json  (MCP path)
    wrapper_dir = os.path.join(out_dir, "lightningTypes", "%sResult" % clt)
    write_out(os.path.join(wrapper_dir, "schema.json"),
              substitute(read_template("wrapperCLT.schema.json"), spec), written)
    write_out(os.path.join(wrapper_dir, "renderer.json"),
              substitute(read_template("wrapperCLT.renderer.json"), spec), written)

    # 5. GenAiFunction: <func>/{input,output}/schema.json + -meta.xml
    fdir = os.path.join(out_dir, "genAiFunctions", func)
    write_out(os.path.join(fdir, "output", "schema.json"),
              substitute(read_template("genAiFunction.output.schema.json"), spec),
              written)
    write_out(os.path.join(fdir, "input", "schema.json"),
              substitute(read_template("genAiFunction.input.schema.json"), spec),
              written)
    write_out(os.path.join(fdir, "%s.genAiFunction-meta.xml" % func),
              genaifunction_meta_xml(spec), written)

    # 6. McpServerDefinition (one per scaffold; merge tools by hand if sharing a
    #    server across widgets -- the shipped gallery uses ONE server, many tools).
    mdir = os.path.join(out_dir, "mcpServerDefinitions")
    write_out(os.path.join(mdir, "%s.mcpServerDefinition-meta.xml" % widget),
              substitute(read_template("mcpServerDefinition.xml"), spec), written)

    return written, widget_json


def run_linter(widget_json):
    """Best-effort: run the sibling lint-widget.py on the emitted bundle so a
    scaffold that somehow produced a bad tile is caught immediately. Returns the
    linter's exit code, or None if it couldn't run."""
    linter = os.path.join(HERE, "lint-widget.py")
    if not os.path.isfile(linter):
        return None
    import subprocess
    proc = subprocess.run(
        [sys.executable, linter, widget_json],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    sys.stdout.write(proc.stdout.decode("utf-8", "replace"))
    return proc.returncode


def main(argv):
    ap = argparse.ArgumentParser(
        description="Generate the 7-piece HXL widget stack from one spec.")
    ap.add_argument("--spec", help="path to a spec JSON file")
    ap.add_argument("--out", default="force-app/main/default",
                    help="output root (default: force-app/main/default)")
    ap.add_argument("--print-spec", action="store_true",
                    help="print a starter spec to stdout and exit")
    # Inline spec flags (override the file).
    ap.add_argument("--widget"); ap.add_argument("--action")
    ap.add_argument("--payload"); ap.add_argument("--anchor")
    ap.add_argument("--clt"); ap.add_argument("--func"); ap.add_argument("--label")
    ap.add_argument("--no-lint", action="store_true",
                    help="skip the post-generate lint pass")
    args = ap.parse_args(argv[1:])

    if args.print_spec:
        print(json.dumps(starter_spec(), indent=2))
        return 0

    spec = load_spec(args)
    validate_spec(spec)

    written, widget_json = generate(spec, args.out)

    print("Scaffolded %d files for widget '%s' (anchor '%s'):"
          % (len(written), spec["widget"], spec["anchor"]))
    for p in written:
        print("  %s" % p)
    print("\nBinding anchor '%s' is threaded byte-identically through:" % spec["anchor"])
    print("  - classes/%s.cls  (Response.%s)" % (spec["action"], spec["anchor"]))
    print("  - lightningTypes/%sOutputValues/schema.json  (property %s)"
          % (spec["clt"], spec["anchor"]))
    print("  - genAiFunctions/%s/output/schema.json  (property %s)"
          % (spec["func"], spec["anchor"]))
    print("  - lightningTypes/%sResult/renderer.json  ($attrs.outputValues.%s.*)"
          % (spec["clt"], spec["anchor"]))

    if args.no_lint:
        print("\n(lint skipped)")
        return 0

    print("\nLinting the emitted widget JSON:")
    rc = run_linter(widget_json)
    if rc is None:
        print("  (lint-widget.py not found alongside scaffold.py -- skipped)")
        return 0
    return 1 if rc == 1 else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
