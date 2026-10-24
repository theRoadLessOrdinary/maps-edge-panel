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

VERSION = "1.4.0"


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
        win.set_default_size(360, 600)
        win.set_keep_above(True)
        win.connect("destroy", self.on_destroy)
        self.window = win

        try:
            with open(registry.PANEL_PID_PATH, 'w') as f:
                f.write(str(os.getpid()))
        except OSError:
            pass

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        win.add(outer)

        sections = Gtk.Notebook()
        sections.set_margin_top(8)
        outer.pack_start(sections, True, True, 0)

        group_tabs = {}
        for sec_name, group_name, tools in registry.LAYOUT:
            if sec_name not in group_tabs:
                groups = Gtk.Notebook()
                groups.set_margin_top(10)
                group_tabs[sec_name] = groups
                sections.append_page(groups, Gtk.Label(label=sec_name))

            if (sec_name, group_name) == registry.GROUPS_TAB:
                group_tabs[sec_name].append_page(self.groups_list(), Gtk.Label(label=group_name))
                continue

            rows = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            rows.set_margin_top(16)
            rows.set_margin_bottom(16)
            rows.set_margin_start(12)
            rows.set_margin_end(12)
            widths = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)
            for tool in tools:
                rows.pack_start(self.tool_row(tool, widths), False, False, 0)

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
            snapshot_path=EMBED_SNAPSHOT_PATH, group_styles=snap.get('group_styles', {}))
        box = self.groups.widget
        box.set_margin_top(8)
        return box

    def tool_row(self, tool, widths):
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
                widget.set_active_id(s.default)
                readers[s.name] = widget.get_active_id
                combos[s.name] = widget
            else:
                adj = Gtk.Adjustment(value=s.default, lower=s.low, upper=s.high,
                                     step_increment=s.step, page_increment=s.step * 10)
                widget = Gtk.SpinButton(adjustment=adj, digits=s.digits)
                widget.set_width_chars(6)
                readers[s.name] = (widget.get_value_as_int if s.kind == 'int'
                                   else widget.get_value)
            widget.set_tooltip_text(s.label)
            row.pack_start(widget, False, False, 0)
            if s.show_when:
                self.show_only_when(widget, combos[s.show_when[0]], s.show_when[1])

        button.connect("clicked", lambda _b: self.run(tool, readers))
        return row

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
