#!/usr/bin/env python3
"""
Launcher for the Map's Edge Tool Panel. This is the script the Extensions
menu runs. It does no GTK of its own and makes no document edits: it starts
tool_panel_window.py as a fully detached process and returns at once, so
Inkscape is not blocked while the panel stays open. If a panel is already
open, it asks that one to come to the front instead.

The panel is given Inkscape's process id and closes itself when that
process ends, so it does not outlive Inkscape. Inkscape does not start
extensions as its own direct children (the parent can be process 1), so the
id is found by name: first among this script's ancestors, then among all
processes (in the Flatpak sandbox that is the one Inkscape).

Same launch scheme as ExpandedGroups/expanded_groups.py (double fork, PID
file, focus request file). It never imports gi, because importing gi writes
a warning to stderr and Inkscape shows a dialog for any stderr output.
"""
import os
import warnings
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import inkex

from registry import PANEL_PID_PATH, PANEL_FOCUS_REQUEST_PATH


def panel_already_running():
    """True if a panel process is alive and holding PANEL_PID_PATH. A PID
    file left by a crashed panel reads as not running, since kill(pid, 0)
    fails for a dead process."""
    try:
        with open(PANEL_PID_PATH) as f:
            pid = int(f.read().strip())
    except (OSError, ValueError):
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def request_panel_focus():
    with open(PANEL_FOCUS_REQUEST_PATH, 'w') as f:
        f.write(str(time.time()))


def _proc_stat(pid):
    """(name, parent pid) of a process, from /proc, or None."""
    try:
        with open(f'/proc/{pid}/stat') as f:
            data = f.read()
    except OSError:
        return None
    name = data[data.index('(') + 1:data.rindex(')')]
    return name, int(data[data.rindex(')') + 2:].split()[1])


def find_inkscape_pid():
    pid = os.getppid()
    while pid > 1:
        stat = _proc_stat(pid)
        if stat is None:
            break
        if stat[0].startswith('inkscape'):
            return pid
        pid = stat[1]
    found = []
    for entry in os.listdir('/proc'):
        if entry.isdigit():
            stat = _proc_stat(int(entry))
            if stat and stat[0].startswith('inkscape'):
                found.append(int(entry))
    return min(found) if found else None


def spawn_detached(argv):
    """Double-fork so the panel has no parent tracking it (see the same
    function in ExpandedGroups/expanded_groups.py for the full reasoning)."""
    # Python warns about fork() in a multi-threaded process; Inkscape would
    # show that warning in a dialog that has to be dismissed.
    warnings.simplefilter('ignore')
    pid = os.fork()
    if pid == 0:
        os.setsid()
        if os.fork() == 0:
            devnull_fd = os.open(os.devnull, os.O_RDWR)
            os.dup2(devnull_fd, 0)
            os.dup2(devnull_fd, 1)
            os.dup2(devnull_fd, 2)
            os.execv(sys.executable, [sys.executable] + argv)
            os._exit(127)  # only reached if execv itself failed
        os._exit(0)
    os.waitpid(pid, 0)


class ToolPanelLauncher(inkex.EffectExtension):
    def effect(self):
        if panel_already_running():
            request_panel_focus()
            return
        script_dir = os.path.dirname(os.path.abspath(__file__))
        argv = [os.path.join(script_dir, 'tool_panel_window.py')]
        inkscape_pid = find_inkscape_pid()
        if inkscape_pid is not None:
            argv.append(str(inkscape_pid))
        spawn_detached(argv)


if __name__ == '__main__':
    ToolPanelLauncher().run()
