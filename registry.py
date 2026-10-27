"""
The one list of every Map's Edge tool, read by both the panel window
(tool_panel_window.py) and the dispatcher (panel_run.py). To put a new tool
on the panel, add one Tool(...) line here.

Two kinds of tool:
 - a tool the dispatcher runs: give its folder, module and class;
 - a tool that opens a window of its own: give action=, the name Inkscape
   exposes its extension under (the .inx id with dots kept and underscores
   turned into hyphens; add ".noprefs" to skip Inkscape's own dialog).

This module imports nothing from inkex or GTK, so either side can load it.
"""
import os
import tempfile

EXTENSIONS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The (section, group) tab that shows the Expanded Groups list instead of buttons.
GROUPS_TAB = ('General', 'Groups')

# How the panel window hands one request to the dispatcher.
REQUEST_PATH = os.path.join(tempfile.gettempdir(), 'maps_edge_panel_request.json')
REQUEST_MAX_AGE = 15.0  # seconds; an older request is ignored
RUN_ACTION = 'maps-edge.panel-run.noprefs'

# Last values of settings marked remember=True, kept in the Inkscape config dir.
REMEMBER_PATH = os.path.join(os.path.dirname(EXTENSIONS_DIR), 'maps_edge_panel_remembered.json')


def run_id(key):
    """Extension id of a tool's own dispatcher entry (run/<key>.inx, from
    make_run_inx.py), so its Undo History entry carries the tool's name."""
    return f'maps_edge.panel_run_{key}'


def run_action(key):
    # Inkscape turns an extension id into an action name with - for _.
    return run_id(key).replace('_', '-') + '.noprefs'

# Single-instance bookkeeping for the window (same scheme as Expanded Groups).
PANEL_PID_PATH = os.path.join(tempfile.gettempdir(), 'maps_edge_panel.pid')
PANEL_FOCUS_REQUEST_PATH = os.path.join(tempfile.gettempdir(), 'maps_edge_panel_focus_request')


class Setting:
    """One value the user sets on the panel before running a tool.
    kind: 'float', 'int', 'choice' (choices = [(value, label), ...]) or 'bool' (a checkbox).
    show_when: (setting name, values) to show it only while that choice
    setting is one of those values."""

    def __init__(self, name, label, kind, default, low=None, high=None,
                 step=1.0, digits=0, choices=None, show_when=None, remember=False):
        self.name = name
        self.label = label
        self.kind = kind
        self.default = default
        self.low = low
        self.high = high
        self.step = step
        self.digits = digits
        self.choices = choices or []
        self.show_when = show_when
        self.remember = remember   # the panel keeps the last value between sessions


class Tool:
    def __init__(self, key, label, folder=None, module=None, cls=None,
                 action=None, settings=(), fixed=None, tip=None, beside=False):
        self.key = key
        self.beside = beside       # shown to the right of the tool before it, same row
        self.label = label
        self.folder = folder
        self.module = module
        self.cls = cls
        self.action = action
        self.settings = list(settings)
        self.fixed = fixed or {}   # option values this button always sends
        self.tip = tip


SATIN = 'rung-rail-satin'
ROUTE = 'route-satin-group'
QUICK = 'inkstitch-quickset'
LAYERS = 'LayerGroupManager'


def _layer(key, label, option, tip):
    return Tool(key, label, LAYERS, 'layergroupmanager', 'LayersCmdDeck',
                fixed={option: True}, tip=tip)


ORDER = 'stitch-order'


def _order(key, label, action, tip, settings=()):
    return Tool(key, label, ORDER, 'stitch_order', 'StitchOrder',
                settings=settings, fixed={'action': action}, tip=tip)


# (section, group, [tools]) in the order shown. section is the top-level
# tab, group the tab under it. Every tool has a tip: what to select and what
# the button then does. It is shown as the button's tooltip.
LAYOUT = [
    ('Embroidery', 'Satin', [
        Tool('rungs', 'Ladder Rungs', SATIN, 'edit_ladder_rungs', 'EditLadderRungs',
             settings=[Setting('mode', 'Mode', 'choice', 'add',
                               choices=[('add', 'Add'), ('decimate', 'Decimate'), ('fit', 'Fit to rails'), ('remove', 'Remove all'),
                                        ('angle', 'Angle'), ('number', 'Number subpaths'), ('unnumber', 'Remove numbers')]),
                       Setting('angle', 'Degrees', 'float', 30.0, -80, 80, 1.0, 1,
                               show_when=('mode', ('angle',)))],
             tip='Select one or more ladders (two rails plus rungs), and/or separate rail paths in pairs. Shift+click rails in order: 1 and 2 become one ladder, 3 and 4 the next. '
                 'Add: builds the rungs, or when rungs exist puts a new rung between each pair. '
                 'Decimate: removes every other rung. The rungs at each end are left alone. '
                 'Fit to rails: trims or extends every rung so it ends 0.125 mm past each rail, keeping its position and angle. New rungs also end 0.125 mm past each rail. '
                 'Where a column curls back on itself, rung ends reach at most halfway across the gap to the next turn. Leave at least 0.6 mm between turns.'
                 ' Remove all: deletes every rung, keeping the two rails.'
                 ' Angle: sets every rung to Degrees across the column (0 is square across, positive leans clockwise). '
                 'Number subpaths: tiny numbers beside each subpath, from 1 in path order, in a layer Ink/Stitch ignores; number again after edits. '
                 'Remove numbers: from the selection, or from everything when nothing is selected.'),
        Tool('add_rung', 'Add Rung at Node', SATIN, 'add_rung_at_node', 'AddRungAtNode',
             tip='Node tool: select one node on a rail to add a rung there, or two nodes on '
                 'the same rail to add a rung halfway between them.'),
        Tool('cross_splice', 'Cross-Splice Rails', SATIN, 'cross_splice_satin', 'CrossSpliceSatin',
             tip='Select 2 or 4 open strokes at one crossing. Joins the nearest open ends into '
                 'continuous paths, to change which path carries on into which past the crossing.'),
        Tool('cut_satin', 'Cut Satin', SATIN, 'cut_satin_at_nodes', 'CutSatinAtNodes',
             tip='Select a satin column plus a cut line or closed shape drawn across it, or '
                 'select the cut nodes on its rails in the Node tool. Splits the column into '
                 'separate satin columns at each cut. Or select only a column already in '
                 'separate pieces to make each piece its own satin column.'),
        Tool('join_satin', 'Join Satin', SATIN, 'join_satin', 'JoinSatin', beside=True,
             tip='Select two or more satin columns that meet end to end (rail end nodes on '
                 'top of each other). Joins them into one satin column, keeping all rungs.'),
        Tool('center_line', 'Satin Center Line', SATIN, 'satin_center_line', 'SatinCenterLine',
             tip='Select one or more satin columns. Draws a line down the middle of each, in '
                 'the satin\'s own style, just under it in the stacking order. The satin is kept.'),
        Tool('normalize', 'Normalize Direction', SATIN, 'normalize_stitch_direction',
             'NormalizeStitchDirection',
             tip='Select two or more ladders. Reverses rails where needed so the selection '
                 'stitches in one continuous direction, each object starting near where the '
                 'one before it ended.'),
        Tool('route', 'Route Satin Group', ROUTE, 'route_satin_group', 'RouteSatinGroup',
             tip='Select one group; each group inside it is a layer, routed on its own. Points each '
                 'column\'s rails the same way so it ends nearest the next column\'s start. A move that '
                 'would leave the shape or cross stitched work gets, in this order: a travel path, '
                 'a new order within the layer, or a trim. Clears every trim in the group first. Run again, it redoes only from the first changed column.'),
        Tool('outset', 'Outset / Inset', SATIN, 'outset_satin', 'OutsetSatin',
             settings=[Setting('distance', 'Distance', 'float', 1.0, -1000, 1000, 0.1, 3)],
             tip='Select one or more ladders. Moves each rail away from the other by this '
                 'distance, and the rungs follow. A negative distance makes the column thinner.'),
        Tool('taper_join', 'Taper Join at Crossing', SATIN, 'taper_join', 'TaperJoin',
             tip='Select 2 satin columns that meet at one crossing. Tapers the two rails of the '
                 'under piece to one shared point on the over column. Older method: Clip Under '
                 'to Over replaces it.'),
        Tool('touch_rails', 'Touch Rails at Crossing', SATIN, 'touch_rails', 'TouchRails',
             tip='Select 2 satin columns that meet at one crossing. The one lower in the stacking '
                 'order is the under piece. Extends or trims each rail tip of the under piece '
                 'until it touches the near rail of the over column. '
                 'Older method: Clip Under to Over replaces it.'),
        Tool('weave', 'Weave Paths', SATIN, 'weave_paths', 'WeavePaths',
             tip='Select 2 or more open paths that cross. Cuts a gap in the under path at every '
                 'crossing, alternating over and under along each path, in the order selected.'),
        Tool('clip_over', 'Clip Under to Over', SATIN, 'clip_to_over', 'ClipToOver',
             tip='Select 2 satin columns at one crossing. Ends the under piece at the over '
                 'piece: its shorter rail is carried along the over piece so both rails end '
                 'together and the satin fills to the tip.'),
    ]),
    ('Embroidery', 'Stitch Settings', [
        Tool('ties_before', 'Lock Stitches: Before', QUICK, 'ties_before', 'TiesBefore',
             tip='Sets Ink/Stitch lock stitches on every selected object to Before: '
                 'a lock stitch at the start only.'),
        Tool('ties_after', 'Lock Stitches: After', QUICK, 'ties_after', 'TiesAfter',
             tip='Sets Ink/Stitch lock stitches on every selected object to After: '
                 'a lock stitch at the end only.'),
        Tool('ties_both', 'Lock Stitches: Both', QUICK, 'ties_both', 'TiesBoth',
             tip='Sets Ink/Stitch lock stitches on every selected object to Both: '
                 'a lock stitch at the start and at the end.'),
        Tool('ties_neither', 'Lock Stitches: Neither', QUICK, 'ties_neither', 'TiesNeither',
             tip='Sets Ink/Stitch lock stitches on every selected object to Neither: '
                 'no lock stitch at either end.'),
        Tool('trim_true', 'Trim After: True', QUICK, 'trim_after_true', 'TrimAfterTrue',
             tip='Turns on Ink/Stitch "Trim after" for every selected object: the thread is '
                 'trimmed after the object is sewn.'),
        Tool('trim_false', 'Trim After: False', QUICK, 'trim_after_false', 'TrimAfterFalse',
             tip='Turns off Ink/Stitch "Trim after" for every selected object.'),
        Tool('sew_sequence', 'Set Sew Sequence', LAYERS, 'sew_sequence', 'SewSequence',
             tip='Select 2 or more objects in the order they sew. First object: lock stitch '
                 'before. Objects in between: no lock stitch. Last object: lock stitch after, '
                 'plus a trim command. A trim command on any other object is removed.'),
    ]),
    ('Embroidery', 'Stitch Paths', [
        Tool('branch', 'Branch Out and Back', 'branch-out-and-back',
             'branch_out_and_back', 'BranchOutAndBack',
             tip='Node tool: select the end node of a branch and the trunk node it attaches '
                 'to. Folds the branch into the trunk so both stitch as one line: out along '
                 'the branch, back the same way, then on along the trunk.'),
        Tool('snowflake', 'Snowflake Stitching', 'snowflake-stitching',
             'snowflake_stitching', 'SnowflakeStitching',
             settings=[Setting('gap', 'Join gap mm', 'float', 0.1, 0.0, 5.0, 0.05, 2)],
             tip='Select a branching path (or several, or groups; each group is routed on its own). Replaces it with one continuous path '
                 'that covers every line, doubling back over the least length possible. '
                 'Ends and crossings closer than the join gap count as touching.'),
        Tool('snowflake_explode', 'Snowflake Explode', 'snowflake-stitching',
             'snowflake_explode', 'SnowflakeExplode',
             settings=[Setting('separation', 'Separation mm', 'float', 0.15, 0.01, 20.0, 0.05, 2)],
             tip='Select a Snowflake Stitching result. Where the route runs over the same line '
                 'more than once, each pass moves into its own lane, side by side, so the route '
                 'can be followed by eye. Changes the path; for looking, not for sewing.'),
    ]),
    ('Embroidery', 'Stitch Order', [
        _order('order_add', 'Add to Stitch Order', 'add',
               settings=[Setting('sel_order', 'Selection order', 'choice', 'document', choices=[
                   ('document', 'Document order'), ('click', 'Click order')], remember=True)],
               tip='Select objects or groups. Gives them the next numbers in the stitch order, '
                   'in document order or in the order you clicked them (the dropdown). '
                   'Nothing is moved in the layers.'),
        _order('order_insert', 'Insert into Stitch Order', 'insert',
               settings=[Setting('place', 'Where', 'choice', 'position', choices=[
                   ('start', 'Beginning'), ('end', 'End'), ('position', 'Position')]),
                         Setting('position', 'Position', 'int', 1, 1, 9999)],
               tip='Puts the selected objects or groups into the stitch order at the beginning, '
                   'at the end, or at the position number (used for Position), in the order '
                   'you selected them. Numbers after them move up.'),
        _order('order_remove', 'Remove from Stitch Order', 'remove',
               tip='Takes the stitch order number off the selected objects or groups.'),
        _order('order_clear', 'Clear Stitch Order', 'clear',
               tip='Takes the stitch order number off every object in the document.'),
        _order('order_list', 'List Stitch Order', 'list',
               tip='Shows every numbered object or group in stitch order.'),
        _order('order_preview', 'Preview in Stitch Order', 'preview',
               tip='Opens the Ink/Stitch simulator on a copy arranged in stitch order. '
                   'Objects without a number are left out. The document is not changed.'),
        _order('order_plan_preview', 'Stitch Plan Preview', 'plan_preview',
               settings=[Setting('plan_place', 'Put the plan', 'choice', 'side', choices=[
                   ('side', 'Beside the canvas'), ('over', 'On top of the design')]),
                         Setting('render_mode', 'Render mode', 'choice', 'realistic-600', choices=[
                   ('realistic-600', 'Realistic View (High Quality)'), ('realistic-300', 'Realistic View'),
                   ('simple', 'Stitch Plan'), ('realistic-vector', 'Realistic Vector (slow)')], remember=True)],
               tip='Nothing needs to be selected. Draws Ink/Stitch\'s stitch plan, sewn in stitch '
                   'order, as a layer beside the canvas or on top of the design (the dropdown), in the chosen render mode (Realistic View (High Quality) by default). '
                   'Objects without a number are left out. Replaces an earlier stitch plan.'),
        _order('order_export', 'Export in Stitch Order', 'export',
               settings=[Setting('format', 'Format', 'choice', 'dst', choices=[
                   ('dst', 'DST'), ('exp', 'EXP'), ('jef', 'JEF'), ('pes', 'PES'),
                   ('vp3', 'VP3'), ('xxx', 'XXX'), ('svg', 'SVG')])],
               tip='Saves an embroidery file sewn in stitch order next to the SVG, with the same '
                   'name. Objects without a number are left out. The SVG must be saved first. '
                   'The document is not changed.'),
    ]),
    ('Embroidery', 'Info', [
        Tool('stitch_count', 'Stitch Count Label', 'stitch-count-label',
             'stitch_count_label', 'StitchCountLabel',
             tip='Select embroidery objects. Counts the stitches Ink/Stitch makes for them '
                 'and writes the total as text just above and to the left of the selection.'),
    ]),
    ('General', 'Paths', [
        Tool('split_fill_outline', 'Split Fill and Outline', 'split-fill-outline',
             'split_fill_outline', 'SplitFillOutline',
             settings=[Setting('stitchable', 'Mode', 'choice', 'false', choices=[
                 ('false', 'Split'), ('true', 'Make stitchable')])],
             tip='Select objects or groups. Split: duplicates each one, outline only on the copy '
                 'on top, fill only on the bottom. Make stitchable: merges the fills into one '
                 'shape and joins the visible outlines (cut where shapes in front hide them) into '
                 'one continuous line on top.'),
        Tool('divide_stroke', 'Divide Stroke', 'divide-stroke-parallel',
             'divide_stroke_parallel', 'DivideStrokeParallel',
             settings=[Setting('n', 'Paths', 'int', 2, 2, 100, 1, 0)],
             tip='Replaces each selected path with this many parallel paths, which together '
                 'cover the band its stroke covered.'),
        Tool('circular_arc', 'Circular Arc Between Nodes', 'circular-arc-nodes',
             'circular_arc_nodes', 'CircularArcNodes',
             tip='Node tool: select two or more nodes on one path. Everything between the '
                 'first and last selected node is replaced by one true circular arc.'),
        Tool('join_near', 'Join Near Endpoints', 'join-near-endpoints',
             'join_near_endpoints', 'JoinNearEndpoints',
             settings=[Setting('tolerance', 'mm', 'float', 0.3, 0.001, 100, 0.05, 3)],
             tip='Select paths. Inside each one, subpath ends closer than this many mm are '
                 'joined into one node, so the pieces become continuous subpaths.'),
        Tool('cut_along', 'Cut Along Shape', 'cut-along-shape', 'cut_along_shape',
             'CutAlongShape',
             settings=[Setting('mode', 'Mode', 'choice', 'delete_inside',
                               choices=[('delete_inside', 'Delete Inside'),
                                        ('cut_only', 'Cut Only')])],
             tip='Delete Inside: select one closed shape plus open paths. The paths are cut at '
                 'the outline of the shape, the pieces inside it are deleted, and the shape is '
                 'removed. Cut Only: the topmost selected object cuts the other selected paths '
                 'where it crosses them and is then removed. No piece is deleted.'),
    ]),
    ('General', 'Layers', [
        _layer('hide_others', 'Hide all but selected', 'hide_others',
               'Hides every object except the selected ones and what is inside them.'),
        _layer('show_others', 'Show all but selected', 'show_others',
               'Shows every object except the selected ones and what is inside them.'),
        _layer('lock_others', 'Lock all but selected', 'lock_others',
               'Locks every object except the selected ones and what is inside them.'),
        _layer('unlock_others', 'Unlock all but selected', 'unlock_others',
               'Unlocks every object except the selected ones and what is inside them.'),
        _layer('toggle_visible', 'Toggle Visible', 'toggle_visible',
               'Hides each selected object if it is shown, shows it if it is hidden, '
               'together with everything inside it.'),
        _layer('toggle_lock', 'Toggle Lock', 'toggle_lock',
               'Locks each selected object if it is unlocked, unlocks it if it is locked, '
               'together with everything inside it.'),
        _layer('show_all', 'Show All', 'show_all',
               'Shows every hidden object in the document. Needs no selection.'),
        _layer('unlock_all', 'Unlock All', 'unlock_all',
               'Unlocks every locked object in the document. Needs no selection.'),
        Tool('expand_recursive', 'Expand Recursively', LAYERS, 'expand_recursive',
             'ExpandRecursive',
             tip='Opens each selected layer or group, and every layer and group inside it, '
                 'in the Layers and Objects panel.'),
        Tool('move_above', 'Move 1st Selected Above 2nd', LAYERS, 'move_above', 'MoveAbove',
             settings=[Setting('stitch_order', 'Also change stitch order', 'bool', False)],
             tip='Select two or more layers or objects. The last one clicked is the target. '
                 'The others are stacked directly above it, in the order they were clicked. '
                 'With Also change stitch order checked, they also get stitch order numbers '
                 'right after the target\'s, in the same order (the target needs a number).'),
    ]),
    # No buttons: this tab holds the Expanded Groups list itself (GROUPS_TAB).
    ('General', 'Groups', []),
    ('General', 'Inkscape', [
        Tool('restart_inkscape', 'Restart Inkscape', 'restart-inkscape',
             'restart_inkscape', 'RestartInkscape',
             tip='Closes Inkscape and opens it again with the active file, for example to '
                 'load changed extensions. Inkscape still asks about unsaved changes; '
                 'Cancel there stops the restart.'),
    ]),
    ('General', 'Export', [
        # No tip: private to the author.
        Tool('borb', 'BORB Exporter...', action='borb-exporter'),
    ]),
]


def all_tools():
    return [t for _, _, tools in LAYOUT for t in tools]


def find_tool(key):
    for t in all_tools():
        if t.key == key:
            return t
    return None
