#!/usr/bin/env python3
import os
import subprocess
from curses import wrapper

import urwid

from pacgraph import Arch, human_si, packs_by_size, toplevel_packs


def get_package_list(keep):
    tree = Arch().local_load()
    packages = packs_by_size(tree, toplevel_packs(tree))
    return filter(lambda pkg: pkg[1] not in keep, packages)


def get_info(softwarename):
    subp = subprocess.run(["pacman", "-Qi", softwarename], capture_output=True)
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
        self.main = urwid.Padding(self.list, left=2, right=2)
        self.info = urwid.Text("")
        self.right = urwid.Filler(self.info, "top")
        self.cols = urwid.Columns([self.main, self.right])
        self.loop = urwid.MainLoop(
            self.cols, palette=self.palette, unhandled_input=self.handle_input
        )

    def __run__(self, stdscr):
        self.loop.run()

    def run(self):
        wrapper(self.__run__)

    def get_selected(self):
        return self.main.base_widget.get_focus_widgets()[0].base_widget

    def get_selected_pkg(self):
        return self.get_selected().pkgName

    def show_text(self, text):
        self.info.set_text(text)

    def exit(self):
        raise urwid.ExitMainLoop()

    def handle_input(self, key):
        if key in ("q", "Q"):
            tui.exit()

        button = tui.get_selected()
        name = tui.get_selected_pkg()
        if key == "right":
            self.show_text(get_info(name))
        elif key == "h":
            self.hide(button, name)

    def toggle_state(self, button, name, stateset, state):
        if name in stateset:
            stateset.remove(name)
            button.set_state("")
        else:
            stateset.append(name)
            button.set_state(state)

    def hide(self, button, name):
        self.toggle_state(button, name, self.keep, "keep")

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
