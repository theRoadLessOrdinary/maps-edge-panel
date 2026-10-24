#!/usr/bin/env python3
"""
Writes run/<key>.inx for every panel tool that runs through panel_run.py.

Inkscape names an Undo History entry after the extension that made the
change. With one shared dispatcher, every panel click showed up as "Map's
Edge Panel Run". Each tool gets its own hidden dispatcher entry instead,
named after the tool's label and pointing at the same panel_run.py, so the
entry reads "Ladder Rungs", "Route Satin Group" and so on.

Run this after adding, removing or renaming a tool in registry.py, then
restart Inkscape so it loads the new files. Old files for tools that no
longer exist are removed.
"""
import os
import sys
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import registry

RUN_DIR = os.path.join(HERE, 'run')

TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<inkscape-extension xmlns="http://www.inkscape.org/namespace/inkscape/extension">

	<!-- Written by make_run_inx.py; edit registry.py instead. -->
	<name>{name}</name>
	<id>{id}</id>

	<effect needs-live-preview="false">
		<object-type>all</object-type>
		<effects-menu hidden="true" />
	</effect>

	<script>
		<command location="inx" interpreter="python">../panel_run.py</command>
	</script>

</inkscape-extension>
"""


def main():
    os.makedirs(RUN_DIR, exist_ok=True)
    wanted = set()
    for tool in registry.all_tools():
        if tool.folder is None:
            continue
        filename = f'{tool.key}.inx'
        wanted.add(filename)
        with open(os.path.join(RUN_DIR, filename), 'w') as f:
            f.write(TEMPLATE.format(name=escape(tool.label),
                                    id=registry.run_id(tool.key)))
    for filename in os.listdir(RUN_DIR):
        if filename.endswith('.inx') and filename not in wanted:
            os.remove(os.path.join(RUN_DIR, filename))
    print(f'{len(wanted)} files in {RUN_DIR}')


if __name__ == '__main__':
    main()
