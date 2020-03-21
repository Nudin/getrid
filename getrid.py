#!/usr/bin/env python3
import os
import subprocess
from curses import wrapper
from functools import lru_cache
from shutil import get_terminal_size

import urwid

from pacgraph import Arch, human_si, packs_by_size, toplevel_packs


def get_package_list(keep):
    tree = Arch().local_load()
    packages = packs_by_size(tree, toplevel_packs(tree))
    return filter(lambda pkg: pkg[1] not in keep, packages)


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

    def set_state(self, state):
        self.set_label((state, self.label))


class Tui:
    to_remove = []
    keep = []
    palette = [
        ("reversed", "standout", ""),
        ("rm", "black", "dark red"),
        ("keep", "light gray", "dark blue"),
    ]

    def __init__(self, keep=[]):
        self.keep = keep
        body = [urwid.Text("Packages"), urwid.Divider()]
        packages = get_package_list(keep)
        for pkg in packages:
            button = PkgButton(pkg)
            button.connect_signal(self.mark_for_deletion)
            body.append(urwid.AttrMap(button, None, focus_map="reversed"))
        self.list = urwid.ListBox(urwid.SimpleFocusListWalker(body))
        self.left = urwid.Padding(self.list, left=2, right=2)

        self.info = urwid.Text("")
        self.right = urwid.Filler(
            urwid.Pile([urwid.Text("Package info"), urwid.Divider(), self.info]), "top",
        )
        self.cols = urwid.Columns([self.left, self.right])
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
        return self.get_selected().base_widget.pkgName

    def show_info(self, pkg):
        text = get_info(pkg, get_terminal_size().columns // 2)
        self.info.set_text(text)

    def exit(self):
        raise urwid.ExitMainLoop()

    def handle_input(self, key):
        if key in ("q", "Q"):
            tui.exit()

        button = tui.get_selected()
        name = tui.get_selected_pkg()
        if key == "right":
            self.show_info(name)
        elif key == "h":
            self.hide(button, name)
        elif key == "k":
            self.mark_as_keep(button, name)
        elif key == "K":
            self.keep.append(name)
            self.hide(button, name)

    def toggle_state(self, button, name, stateset, state):
        if name in stateset:
            stateset.remove(name)
            button.set_state("")
        else:
            stateset.append(name)
            button.set_state(state)

    def mark_as_keep(self, button, name):
        self.toggle_state(button.base_widget, name, self.keep, "keep")

    def hide(self, button, name):
        self.list.body.remove(button)

    def mark_for_deletion(self, button, name):
        self.toggle_state(button, name, self.to_remove, "rm")


if __name__ == "__main__":
    home = os.path.expanduser("~")
    conf_file = os.path.join(home, ".keep")
    try:
        with open(conf_file) as file:
            keep = file.readlines()
            keep = [x.strip() for x in keep]
    except OSError:
        keep = []

    tui = Tui(keep)
    tui.run()

    with open(conf_file, "w") as file:
        file.write("\n".join(tui.keep))

    if len(tui.to_remove) > 0:
        print()
        print("Selected for removal: " + " ".join(tui.to_remove))
        if input("Remove packages? [y/N] ").lower() == "y":
            if os.geteuid() != 0:
                subprocess.run(["sudo", "pacman", "-Rs", *tui.to_remove])
            else:
                subprocess.run(["pacman", "-Rs", *tui.to_remove])
