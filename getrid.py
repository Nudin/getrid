#!/usr/bin/env python3
import copy
import os
import subprocess
from curses import wrapper
from functools import lru_cache
from shutil import get_terminal_size

import urwid

from pacgraph import Arch, human_si, packs_by_size, toplevel_packs

NAME = "getrid"
VERSION = 0.2
HELP_TEXT = f"""
{NAME} {VERSION}

- Press <Enter>, <Space> or 'd' to mark a package for deletion
- Press 't' to temporally hide (keep) a package
- Press 'e' to hide (keep) a package also in future calls of {NAME}
- Press 's' to show/hide all hidden packages
- Pressing the same key again will unset the status.

- Use j/k, arrow keys or the mouse for movements.
- Press q to exit.
"""


class States:
    TO_KEEP = "to_keep"
    TO_KEEP_FOR_NOW = "to_keep_for_now"
    TO_REMOVE = "to_remove"


def get_package_list():
    tree = Arch().local_load()
    packages = packs_by_size(tree, toplevel_packs(tree))
    return packages


@lru_cache()
def get_info(softwarename, size=40):
    env = os.environ.copy()
    env["COLUMNS"] = str(size)
    subp = subprocess.run(["pacman", "-Qi", softwarename], capture_output=True, env=env)
    return subp.stdout


class PkgButton(urwid.Button):
    def __init__(self, package):
        self.pkgSize = package[0]
        self.pkgName = package[1]
        label = "{} {}".format(human_si(self.pkgSize), self.pkgName)
        super().__init__(label)

    def connect_signal(self, call):
        urwid.connect_signal(self, "click", call, self.pkgName)

    def set_state(self, state=None):
        self.set_label((state, self.label))


class Tui:
    to_remove = []
    to_keep = []
    to_keep_for_now = []
    storage_counter = {
        States.TO_REMOVE: 0,
        States.TO_KEEP: 0,
        States.TO_KEEP_FOR_NOW: 0,
    }
    hidden = True
    palette = [
        ("reversed", "standout", "default"),
        (States.TO_REMOVE, "black", "dark red"),
        (States.TO_KEEP, "light gray", "dark green"),
        (States.TO_KEEP_FOR_NOW, "light gray", "dark blue"),
    ]

    def __init__(self, to_keep=[]):
        self.to_keep = to_keep
        body = [urwid.Text("Packages"), urwid.Divider()]
        self.packages = get_package_list()
        for pkg in self.packages:
            button = PkgButton(pkg)
            button.connect_signal(self.toggle_to_remove)
            body.append(urwid.AttrMap(button, None, focus_map="reversed"))
            if pkg[1] in self.to_keep:
                button.set_state(States.TO_KEEP)
        focuswalker = urwid.SimpleFocusListWalker(body)
        self.list = urwid.ListBox(focuswalker)
        self.backup = copy.copy(self.list.body)
        self.left = urwid.Padding(self.list, left=2, right=2)

        self.help = urwid.Text(HELP_TEXT)
        self.stats = urwid.Text("")
        self.info = urwid.Text("")
        self.right = urwid.Filler(
            urwid.Pile(
                [
                    self.help,
                    urwid.Divider("-"),
                    self.stats,
                    urwid.Divider("-"),
                    urwid.Text("Package info"),
                    urwid.Divider(),
                    self.info,
                ]
            ),
            "top",
        )
        self.cols = urwid.Columns([self.left, self.right])
        urwid.connect_signal(focuswalker, "modified", self.handle_input)

        # Hide the elements from to_keep and initialise stats
        self.hide_all()
        self.show_stats()

        # Start the MainLoop
        self.loop = urwid.MainLoop(
            self.cols, palette=self.palette, unhandled_input=self.handle_input
        )

    def __run__(self, stdscr):
        self.loop.run()

    def run(self):
        wrapper(self.__run__)

    def get_selected(self):
        return self.left.base_widget.get_focus_widgets()[0]

    def get_selected_pkg(self):
        if type(self.get_selected()) == urwid.widget.Text:
            return self.get_selected().text
        return self.get_selected().base_widget

    def up(self):
        focus = self.left.base_widget.focus_position
        if focus <= 2:
            return
        self.left.base_widget.set_focus(focus - 1)

    def down(self):
        focus = self.left.base_widget.focus_position
        try:
            self.left.base_widget.set_focus(focus + 1)
        except IndexError:
            # We are already at the lowest entry
            pass

    def show_info(self, pkg):
        text = get_info(pkg, get_terminal_size().columns // 2)
        self.info.set_text(text)

    def show_stats(self):
        self.stats.set_text(
            f"""Statics:
Number removable packages: {len(self.packages)}
Number packages marked for deletion: {len(self.to_remove)}
Number packages marked to keep: {len(self.to_keep)}
Number packages marked to keep for now: {len(self.to_keep_for_now)}

Space being freed: >={human_si(self.storage_counter[States.TO_REMOVE])}
            """
        )

    def exit(self):
        raise urwid.ExitMainLoop()

    def handle_input(self, key=None):
        if key in ("q", "Q"):
            self.exit()

        # This will most likely fail due to a race condition in __init__
        # Doesn't matter, just ignore it
        try:
            button = self.get_selected()
            name = self.get_selected_pkg().pkgName
        except AttributeError:
            return

        # On every movement: show package info
        if key is None:
            self.show_info(name)
        # Keep for this runtime
        elif key == "t":
            self.toggle_to_keep_for_now(button, name)
        # Keep "forever"
        elif key == "e":
            self.toggle_to_keep(button, name)
        # Delete
        elif key == "d":
            self.toggle_to_remove(button, name)
        # show/hide packages that will be kept
        elif key == "s":
            self.toggle_hidden()
        # Vim-movements
        elif key == "j":
            self.down()
        elif key == "k":
            self.up()

    def toggle_hidden(self):
        if self.hidden:
            self.unhide_all()
        else:
            self.hide_all()

    def hide_all(self):
        to_remove = []
        # self.list.body is subtype of MonitoredList: removing an element will
        # skip the next element in the iterator, therefore we have to loop twice
        for button in self.list.body:
            if type(button) != urwid.decoration.AttrMap:
                continue
            name = button.base_widget.pkgName
            if name in self.to_keep or name in self.to_keep_for_now:
                to_remove.append(button)
        for button in to_remove:
            self.list.body.remove(button)
        self.hidden = True

    def unhide_all(self):
        focused_element = self.list.body.get_focus()[0]
        self.list.body = copy.copy(self.backup)
        focus = self.list.body.index(focused_element)
        self.list.set_focus(focus)
        self.hidden = False

    def toggle_state(self, button, name, stateset, state):
        if name in stateset:
            stateset.remove(name)
            button.set_state()
            self.storage_counter[state] -= button.base_widget.pkgSize
        else:
            if name in self.to_keep:
                self.toggle_state(button, name, self.to_keep, States.TO_KEEP)
            if name in self.to_keep_for_now:
                self.toggle_state(
                    button, name, self.to_keep_for_now, States.TO_KEEP_FOR_NOW
                )
            if name in self.to_remove:
                self.toggle_state(button, name, self.to_remove, States.TO_REMOVE)
            stateset.append(name)
            button.set_state(state)
            self.storage_counter[state] += button.base_widget.pkgSize
        if self.hidden:
            self.hide_all()
        self.show_stats()

    def toggle_to_keep_for_now(self, button, name):
        self.toggle_state(
            button.base_widget, name, self.to_keep_for_now, States.TO_KEEP_FOR_NOW
        )

    def toggle_to_keep(self, button, name):
        self.toggle_state(button.base_widget, name, self.to_keep, States.TO_KEEP)

    def toggle_to_remove(self, button, name):
        self.toggle_state(button.base_widget, name, self.to_remove, States.TO_REMOVE)


if __name__ == "__main__":
    if os.environ.get("XDG_CONFIG_HOME"):
        conf_file = os.path.join(os.environ.get("XDG_CONFIG_HOME"), f"{NAME}")
    else:
        home = os.path.expanduser("~")
        conf_file = os.path.join(home, f".{NAME}")
    try:
        with open(conf_file) as file:
            keep = file.readlines()
            keep = [x.strip() for x in keep]
    except OSError:
        keep = []

    tui = Tui(keep)
    tui.run()

    with open(conf_file, "w") as file:
        file.write("\n".join(tui.to_keep))

    if len(tui.to_remove) > 0:
        print()
        print("Selected for removal: " + " ".join(tui.to_remove))
        if input("Remove packages? [y/N] ").lower() == "y":
            if os.geteuid() != 0:
                subprocess.run(["sudo", "pacman", "-Rs", *tui.to_remove])
            else:
                subprocess.run(["pacman", "-Rs", *tui.to_remove])
