# `getrid` of arch packages you don't need anymore

Having a rolling release distribution if one of the big advantages of Arch
compared to other distributions: no outdated software nor being forced to do
lengthy and risky upgrades or fresh installs every X months/years.  The
downside of this is that there are never any "clear cuts" and the amounts of
packages once installed but not needed anymore constantly grows.

Removing old packages is annoying, so I wrote `getrid` a tool that makes it to
find packages that unnecessary fill up your disk. A terminal user interface
allows you to decide which packages to keep and which to remove.

Dependencies: python, pacgraph, urwid
