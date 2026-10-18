# Map's Edge Tool Panel

A floating window for Inkscape with a button for every Map's Edge Tools extension, so a tool is one click away instead of three menu levels down. The window can stay open beside Inkscape while you work.

Menu: **Extensions > Map's Edge Tools > Tool Panel** (extension ID `maps_edge.tool_panel`).

## Using it

- Pick **Tool Panel** from the menu once. The window opens and Inkscape stays usable. Picking it again brings the open window to the front.
- Two tabs across the top, **Embroidery** and **General**, each hold a tab per tool group, matching the menu.
- Each button has a tooltip saying what to select and what the button does.
- A tool that has settings shows them on the same row as its button.
- A button runs its tool on the current document and selection, as one undo step, the same as picking the tool from the menu.
- Tools that open a window of their own are opened through Inkscape, the same as from the menu.

The panel has no live preview. The menu entries keep theirs.

## What it needs

The panel runs the tools from their own folders. Install the ones you want, with these folder names, in the same extensions directory as this panel:

| Folder name | Repository |
|---|---|
| `rung-rail-satin` | [inkstitch-satin-tools](https://github.com/theRoadLessOrdinary/inkstitch-satin-tools) |
| `inkstitch-quickset` | [inkstitch-quickset](https://github.com/theRoadLessOrdinary/inkstitch-quickset) |
| `LayerGroupManager` | [layer-group-manager](https://github.com/theRoadLessOrdinary/layer-group-manager) |
| `branch-out-and-back` | [branch-out-and-back](https://github.com/theRoadLessOrdinary/branch-out-and-back) |
| `snowflake-stitching` | [snowflake-stitching](https://github.com/theRoadLessOrdinary/snowflake-stitching) |
| `circular-arc-nodes` | [circular-arc-nodes](https://github.com/theRoadLessOrdinary/circular-arc-nodes) |
| `cut-along-shape` | [cut-along-shape](https://github.com/theRoadLessOrdinary/cut-along-shape) |
| `divide-stroke-parallel` | [divide-stroke-parallel](https://github.com/theRoadLessOrdinary/divide-stroke-parallel) |
| `join-near-endpoints` | [join-near-endpoints](https://github.com/theRoadLessOrdinary/join-near-endpoints) |
| `stitch-count-label` | [stitch-count-label](https://github.com/theRoadLessOrdinary/stitch-count-label) |
| `ExpandedGroups` | [expanded-groups-inkscape](https://github.com/theRoadLessOrdinary/expanded-groups-inkscape) (required: the panel uses its code to talk to Inkscape) |

A button whose tool is not installed does nothing useful, so install the folders you use.

- Inkscape 1.x (developed and used on Inkscape 1.4.4, Flatpak, on Linux; other platforms have not been tried)
- Python 3 with GTK 3 bindings (`gi`) and D-Bus, as the Linux Flatpak build of Inkscape provides. Only Linux has been tried.

## How it works

The window cannot edit the open document itself. When a button is pressed, the window writes a small request file (which tool, which settings) and asks the running Inkscape, over D-Bus, to run the hidden extension `maps_edge.panel_run`. Inkscape runs it on the current document and selection like any other extension. That script loads the requested tool's own code from its folder and runs it unchanged.

`registry.py` holds the one list of tools: labels, groups, tooltips and settings. To add a tool to the panel, add one line there.

## Install

Copy the files in this repository into a folder of their own inside Inkscape's user extensions directory, then restart Inkscape. To find that directory, open **Edit > Preferences > System** and look at **User extensions**. Typical locations:

| Install type | User extensions folder |
|---|---|
| Linux (native) | `~/.config/inkscape/extensions/` |
| Linux (Flatpak) | `~/.var/app/org.inkscape.Inkscape/config/inkscape/extensions/` |
| macOS | `~/Library/Application Support/org.inkscape.Inkscape/config/inkscape/extensions/` |
| Windows | `%APPDATA%\inkscape\extensions\` |

For example, on native Linux:

```bash
git clone https://github.com/theRoadLessOrdinary/maps-edge-panel.git \
    ~/.config/inkscape/extensions/maps-edge-panel
```

To uninstall, delete the folder and restart Inkscape.
