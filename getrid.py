#!/usr/bin/env python3
import subprocess
from curses import wrapper

import urwid

from pacgraph import Arch, human_si, packs_by_size, toplevel_packs

to_remove = []
keep = []


def get_package_list():
    arch = Arch()
    tree = arch.local_load()
    strings = []
    for s, n in packs_by_size(tree, toplevel_packs(tree)):
        strings.append("%s %s" % (human_si(s), n))
    return strings


def get_info(softwarename):
    subp = subprocess.run(["pacman", "-Qi", softwarename], capture_output=True)
    return subp.stdout


def hide(button, name):
    if name in keep:
        keep.remove(name)
        button.set_state("")
    else:
        keep.append(name)
        button.set_state("keep")


def on_click(button, choice):
    size, name = choice.split()
    if name in to_remove:
        to_remove.remove(name)
        button.set_state("")
    else:
        to_remove.append(name)
        button.set_state("rm")


def menu(title, choices):
    body = [urwid.Text(title), urwid.Divider()]
    for c in choices:
        button = Button(c)
        urwid.connect_signal(button, "click", on_click, c)
        body.append(urwid.AttrMap(button, None, focus_map="reversed"))
    return urwid.ListBox(urwid.SimpleFocusListWalker(body))


class Button(urwid.Button):
    def set_state(self, state):
        self.set_label((state, self.label))


class Tui:
    palette = [
        ("reversed", "standout", ""),
        ("rm", "black", "dark red"),
        ("keep", "light gray", "dark blue"),
    ]

    def __init__(self):
        self.main = urwid.Padding(menu("Title", get_package_list()), left=2, right=2)
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

    def get_selected_text(self):
        return self.get_selected().label.split()[1]

    def show_text(self, text):
        self.info.set_text(text)

    def exit(self):
        raise urwid.ExitMainLoop()

    def handle_input(self, key):
        if key in ("q", "Q"):
            tui.exit()

        button = tui.get_selected()
        name = tui.get_selected_text()
        if key == "right":
            self.show_text(get_info(name))
        elif key == "h":
            hide(button, name)


tui = Tui()
tui.run()
print(to_remove)
