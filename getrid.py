#!/usr/bin/env python3
import subprocess
from curses import wrapper

import urwid

from pacgraph import Arch, human_si, packs_by_size, toplevel_packs

to_remove = []
keep = []

info = urwid.Text("")


def get_package_list():
    arch = Arch()
    tree = arch.local_load()
    strings = []
    for s, n in packs_by_size(tree, toplevel_packs(tree)):
        strings.append("%s %s" % (human_si(s), n))
    return strings


def show_text(text):
    info.set_text(text)


def show_or_exit(key):
    if key in ("q", "Q"):
        raise urwid.ExitMainLoop()
    selected_button = main.base_widget.get_focus_widgets()[0].base_widget
    if repr(key) == "'right'":
        softwarename = selected_button.label.split()[1]
        subp = subprocess.run(["pacman", "-Qi", softwarename], capture_output=True)
        show_text(subp.stdout)
    elif repr(key) == "'h'":
        softwarename = selected_button.label.split()[1]
        keep_item(selected_button, selected_button.label)
    else:
        show_text(repr(key))


def menu(title, choices):
    body = [urwid.Text(title), urwid.Divider()]
    for c in choices:
        button = urwid.Button(c)
        urwid.connect_signal(button, "click", item_chosen, c)
        body.append(urwid.AttrMap(button, None, focus_map="reversed"))
    return urwid.ListBox(urwid.SimpleFocusListWalker(body))


def keep_item(button, choice):
    size, name = choice.split()
    if name in keep:
        keep.remove(name)
        button.set_label(("", choice))
    else:
        keep.append(name)
        button.set_label(("keep", choice))


def item_chosen(button, choice):
    size, name = choice.split()
    if name in to_remove:
        to_remove.remove(name)
        button.set_label(("", choice))
    else:
        to_remove.append(name)
        button.set_label(("rm", choice))


def exit_program(button):
    raise urwid.ExitMainLoop()


palette = [
    ("reversed", "standout", ""),
    ("rm", "black", "dark red"),
    ("keep", "light gray", "dark blue"),
]

main = urwid.Padding(menu("Title", get_package_list()), left=2, right=2)
right = urwid.Filler(info, "top")
cols = urwid.Columns([main, right])
loop = urwid.MainLoop(cols, palette=palette, unhandled_input=show_or_exit)


def run(stdscr):
    loop.run()


wrapper(run)
print(to_remove)
