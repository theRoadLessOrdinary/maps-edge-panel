#!/usr/bin/env python3
"""
Map's Edge Panel Run (dispatcher, no menu entry)

The Tool Panel window cannot edit the open document itself. Instead it
writes a small request file (which tool, which settings) and asks Inkscape,
over D-Bus, to run this extension. Inkscape then runs this script on the
current document and selection like any other extension, so the result
lands in the live document as one undo step.

This script adds no tool logic. It builds the requested tool's own
EffectExtension subclass, points its .svg at the already-loaded document and
its .options at that tool's own defaults plus the requested settings, then
calls the tool's unmodified .effect(). Same technique as satin_tools.py in
rung-rail-satin, for every folder.
"""
import importlib
import json
import os
import sys
import time
from argparse import Namespace

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import inkex
from inkex import EffectExtension

import registry

# Values Inkscape gave this run, which the tool must see as its own.
PASS_THROUGH = ("ids", "selected_nodes", "input_file", "output")


def read_request():
    try:
        with open(registry.REQUEST_PATH) as f:
            request = json.load(f)
    except (OSError, ValueError):
        return None
    finally:
        try:
            os.remove(registry.REQUEST_PATH)
        except OSError:
            pass
    if time.time() - float(request.get("time", 0)) > registry.REQUEST_MAX_AGE:
        return None
    return request


def build_tool(spec, svg, document, own_options, settings):
    """The tool's extension object, ready for .effect()."""
    sys.path.insert(0, os.path.join(registry.EXTENSIONS_DIR, spec.folder))
    module = importlib.import_module(spec.module)
    tool = getattr(module, spec.cls)()

    options = vars(tool.arg_parser.parse_args([]))
    for name in PASS_THROUGH:
        if hasattr(own_options, name):
            options[name] = getattr(own_options, name)
    options.update(spec.fixed)
    options.update(settings)

    tool.options = Namespace(**options)
    tool.svg = svg
    tool.document = document
    return tool


class PanelRun(EffectExtension):
    def effect(self):
        request = read_request()
        if request is None:
            raise inkex.AbortExtension(
                "This runs tools for the Map's Edge Tool Panel. Open the panel "
                "(Extensions > Map's Edge Tools > Tool Panel) and use its buttons.")
        spec = registry.find_tool(request.get("tool"))
        if spec is None or spec.folder is None:
            raise inkex.AbortExtension(
                f"The Tool Panel asked for an unknown tool: {request.get('tool')}")

        allowed = {s.name for s in spec.settings}
        settings = {k: v for k, v in request.get("settings", {}).items() if k in allowed}
        build_tool(spec, self.svg, self.document, self.options, settings).effect()


if __name__ == "__main__":
    PanelRun().run()
