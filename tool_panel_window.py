#!/usr/bin/env python3
"""
The Map's Edge Tool Panel window: every tool from registry.py as a button,
grouped as in the Extensions > Map's Edge Tools menu. Each section is a tab,
and each group a tab under it, so every group is one click away and none
sits below the bottom edge of the window. A tool with settings has its
fields on the same row as its button.

Launched detached by tool_panel.py, so it can stay open beside Inkscape.
It never touches the SVG file. A button click writes a request file and
asks the running Inkscape (over D-Bus) to run panel_run.py, which runs the
tool on the live document and selection. Tools that open a window of their
own are started through their own Inkscape action instead.

The launcher passes Inkscape's process id as the first argument; the window
closes itself once that process has ended.
"""
import json
import os
import sys
import time
import warnings
warnings.filterwarnings('ignore')  # before the gi import

os.environ.setdefault('NO_AT_BRIDGE', '1')

HERE = os.path.dirname(os.path.abspath(__file__))


def _remembered():
    try:
        with open(registry.REMEMBER_PATH) as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def remembered_value(tool_key, name, default):
    return _remembered().get(f'{tool_key}.{name}', default)


def remember_value(tool_key, name, value):
    data = _remembered()
    data[f'{tool_key}.{name}'] = value
    try:
        with open(registry.REMEMBER_PATH, 'w') as f:
            json.dump(data, f)
    except OSError:
        pass
sys.path.insert(0, HERE)
# D-Bus helpers are reused from Expanded Groups, not copied.
sys.path.insert(1, os.path.join(os.path.dirname(HERE), 'ExpandedGroups'))

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, Gio, GLib

# Use Inkscape's window class so the taskbar groups this panel under the Inkscape icon
GLib.set_prgname('org.inkscape.Inkscape')
Gdk.set_program_class('Inkscape')

import registry
from expanded_groups_dbus import run_extension_live, quiet_stderr, DBUS_NAME, DBUS_PATH
from expanded_groups_data import EMBED_SNAPSHOT_PATH
from expanded_groups_panel import ExpandedGroupsPanel

VERSION = "1.7.0"


def action_exists(name):
    """Whether the running Inkscape has this action (asked over D-Bus)."""
    try:
        conn = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        conn.call_sync(DBUS_NAME, DBUS_PATH, 'org.gtk.Actions', 'Describe',
                       GLib.Variant('(s)', (name,)), None,
                       Gio.DBusCallFlags.NONE, 5000, None)
    except GLib.Error:
        return False
    return True


class ToolPanel:
    def __init__(self, inkscape_pid=None):
        self.inkscape_pid = inkscape_pid
        self.last_focus_mtime = self._focus_mtime()
        with quiet_stderr():
            self.build()

    def build(self):
        win = Gtk.Window(title=f"Map's Edge Tools v{VERSION}")
        win.set_default_size(430, 600)
        win.set_keep_above(True)
        win.connect("destroy", self.on_destroy)
        self.window = win

        try:
            with open(registry.PANEL_PID_PATH, 'w') as f:
                f.write(str(os.getpid()))
        except OSError:
            pass

        self.setting_widgets = {}  # (tool key, setting name): widget
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        win.add(outer)

        sections = Gtk.Notebook()
        sections.set_margin_top(8)
        outer.pack_start(sections, True, True, 0)
        sections.set_action_widget(self.toolbar(), Gtk.PackType.END)

        group_tabs = {}
        for sec_name, group_name, tools in registry.LAYOUT:
            if (sec_name, group_name) == registry.GROUPS_TAB:
                sections.append_page(self.groups_list(), Gtk.Label(label=sec_name))
                continue
            if sec_name not in group_tabs:
                groups = Gtk.Notebook()
                groups.set_margin_top(10)
                group_tabs[sec_name] = groups
                sections.append_page(groups, Gtk.Label(label=sec_name))


            rows = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            rows.set_margin_top(16)
            rows.set_margin_bottom(16)
            rows.set_margin_start(12)
            rows.set_margin_end(12)
            note = registry.TAB_NOTES.get((sec_name, group_name))
            if note:
                label = Gtk.Label(label=note, xalign=0)
                label.set_line_wrap(True)
                label.set_margin_bottom(10)
                rows.pack_start(label, False, False, 0)
            widths = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)
            row = None
            for tool in tools:
                if tool.beside and row is not None:
                    self.tool_row(tool, widths, row)
                else:
                    row = self.tool_row(tool, widths)
                    rows.pack_start(row, False, False, 0)

            # A group taller than the window scrolls. The scrollbar is always
            # drawn when it is needed, not only while the pointer is over it.
            scroll = Gtk.ScrolledWindow()
            scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            scroll.set_overlay_scrolling(False)
            scroll.add(rows)
            group_tabs[sec_name].append_page(scroll, Gtk.Label(label=group_name))

        self.statusbar = Gtk.Statusbar()
        self.status_ctx = self.statusbar.get_context_id("status")
        outer.pack_start(self.statusbar, False, False, 0)

        self.follow_order_selection()
        win.show_all()
        GLib.timeout_add(500, self.poll_focus)

    def groups_list(self):
        """The Expanded Groups list, read from the snapshot tool_panel.py wrote."""
        try:
            with open(EMBED_SNAPSHOT_PATH) as f:
                snap = json.load(f)
        except (OSError, ValueError):
            snap = {}
        self.groups = ExpandedGroupsPanel(
            snap.get('by_name', {}), snap.get('by_id', {}), snap.get('states', {}),
            snap.get('stitch_order', []), None, snap.get('group_order', []),
            snap.get('labels', {}), host_window=self.window, status=self.show_status,
            snapshot_path=EMBED_SNAPSHOT_PATH, group_styles=snap.get('group_styles', {}),
            item_order=snap.get('item_order', {}),
            stitch_sections=snap.get('stitch_sections', {}))
        box = self.groups.widget
        box.set_margin_top(8)
        return box

    def toolbar(self):
        """Icon buttons for TOOLBAR_TOOLS, at the right end of the top tab bar."""
        # Our own symbolic icons; GTK draws them in the theme's text color.
        Gtk.IconTheme.get_default().append_search_path(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'icons'))
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        box.set_margin_end(6)
        for tool in registry.TOOLBAR_TOOLS:
            button = Gtk.Button()
            button.set_image(Gtk.Image.new_from_icon_name(
                registry.TOOLBAR_ICONS.get(tool.key, 'system-run'), Gtk.IconSize.LARGE_TOOLBAR))
            button.set_relief(Gtk.ReliefStyle.NONE)
            button.set_tooltip_text(tool.tip or tool.label)
            button.connect("clicked", lambda _b, t=tool: self.run(t, {}))
            box.pack_start(button, False, False, 0)
        box.show_all()
        return box

    def tool_row(self, tool, widths, row=None):
        """A row with the tool's button and settings, or, given row, the
        button and settings added to the right end of that row."""
        if row is None:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        button = Gtk.Button(label=tool.label)
        button.get_child().set_xalign(0)
        if tool.tip:
            button.set_tooltip_text(tool.tip)
        # As wide as the longest label in its group, not as wide as the window.
        widths.add_widget(button)
        row.pack_start(button, False, False, 0)

        readers = {}
        combos = {}
        for s in tool.settings:
            if s.kind == 'choice':
                widget = Gtk.ComboBoxText()
                for value, text in s.choices:
                    widget.append(value, text)
                widget.set_active_id(
                    remembered_value(tool.key, s.name, s.default) if s.remember else s.default)
                if s.remember:
                    widget.connect("changed", lambda w, k=tool.key, n=s.name:
                                   remember_value(k, n, w.get_active_id()))
                readers[s.name] = widget.get_active_id
                combos[s.name] = widget
            elif s.kind == 'bool':
                widget = Gtk.CheckButton(label=s.label)
                widget.set_active(bool(s.default))
                readers[s.name] = widget.get_active
            else:
                adj = Gtk.Adjustment(value=s.default, lower=s.low, upper=s.high,
                                     step_increment=s.step, page_increment=s.step * 10)
                widget = Gtk.SpinButton(adjustment=adj, digits=s.digits)
                widget.set_width_chars(6)
                readers[s.name] = (widget.get_value_as_int if s.kind == 'int'
                                   else widget.get_value)
            widget.set_tooltip_text(s.label)
            row.pack_start(widget, False, False, 0)
            self.setting_widgets[(tool.key, s.name)] = widget
            if s.enable_when:
                self.enable_only_when(widget, combos[s.enable_when[0]], s.enable_when[1])
            if s.show_when:
                self.show_only_when(widget, combos[s.show_when[0]], s.show_when[1])

        button.connect("clicked", lambda _b: self.run(tool, readers))
        return row

    @staticmethod
    def enable_only_when(widget, combo, values):
        """Gray widget out unless combo's value is one of values."""
        def sync(_c=None):
            widget.set_sensitive(combo.get_active_id() in values)
        combo.connect("changed", sync)
        sync()

    def follow_order_selection(self):
        """Add's position takes the highest stitch order number selected in
        Groups > Stitch Order."""
        spin = self.setting_widgets.get(('order_add', 'position'))
        groups = getattr(self, 'groups', None)
        if spin is None or groups is None:
            return

        def changed(_sel):
            numbers = [groups.stitch_order.index(i) + 1
                       for kind, item_id, _ in groups.selected_rows() if kind in ('order-object', 'section')
                       for i in groups.members(kind, item_id) if i in groups.stitch_order]
            if numbers:
                spin.set_value(max(numbers))
        groups.tree.get_selection().connect("changed", changed)

    @staticmethod
    def show_only_when(widget, combo, values):
        # Shown only while the combo holds one of values; no_show_all keeps
        # the window's show_all from showing it anyway.
        widget.set_no_show_all(True)

        def sync(_c=None):
            widget.set_visible(combo.get_active_id() in values)
        combo.connect("changed", sync)
        sync()

    def show_status(self, msg):
        self.statusbar.pop(self.status_ctx)
        self.statusbar.push(self.status_ctx, msg)

    def run(self, tool, readers):
        if tool.action:
            ok = run_extension_live(tool.action)
        else:
            # A spin button only takes typed text into its value on Enter or
            # focus loss, so make it do that before reading.
            focus = self.window.get_focus()
            if isinstance(focus, Gtk.SpinButton):
                focus.update()
            request = {'tool': tool.key, 'time': time.time(),
                       'settings': {name: read() for name, read in readers.items()}}
            with open(registry.REQUEST_PATH, 'w') as f:
                json.dump(request, f)
            # The call below holds the panel until the tool finishes, so show
            # that it is running first.
            self.show_status(f"Running: {tool.label}...")
            while Gtk.events_pending():
                Gtk.main_iteration()
            # The tool's own entry names the Undo History step after the tool.
            # Until Inkscape is restarted after make_run_inx.py, use the
            # shared one.
            action = registry.run_action(tool.key)
            if not action_exists(action):
                action = registry.RUN_ACTION
            ok = run_extension_live(action)
        self.show_status(f"Ran: {tool.label}" if ok
                         else f"Could not reach Inkscape for: {tool.label}")

    @staticmethod
    def _focus_mtime():
        try:
            return os.stat(registry.PANEL_FOCUS_REQUEST_PATH).st_mtime_ns
        except OSError:
            return 0

    def inkscape_gone(self):
        if self.inkscape_pid is None:
            return False
        try:
            os.kill(self.inkscape_pid, 0)
        except ProcessLookupError:
            return True
        except OSError:
            return False
        return False

    def poll_focus(self):
        if self.inkscape_gone():
            self.window.destroy()
            return False
        mtime = self._focus_mtime()
        if mtime != self.last_focus_mtime:
            self.last_focus_mtime = mtime
            self.window.present()
        return True

    def on_destroy(self, *args):
        try:
            os.remove(registry.PANEL_PID_PATH)
        except OSError:
            pass
        Gtk.main_quit()


def main():
    try:
        inkscape_pid = int(sys.argv[1])
    except (IndexError, ValueError):
        inkscape_pid = None
    ToolPanel(inkscape_pid)
    Gtk.main()


if __name__ == '__main__':
    main()
