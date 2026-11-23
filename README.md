# header-diff-web

Compare two blocks of HTTP headers in the browser. Each block keeps the text you
pasted; the app aligns both into one row per header name, so matching headers sit
on the same line and only the differences break the alignment. Any block can be
copied back out as pasted, cleaned up and sorted, or exactly as it appears.

Python 3.9+. One dependency, `header-sorter`, committed here as a source tarball
(`vendor/header_sorter-0.2.0.tar.gz`) and installed from `requirements.txt`.
Nothing comes from a package index and nothing outside this repository is
needed.

## Setup

```bash
cd header-diff-web
python3 -m pip install -r requirements.txt
python3 server.py
```

Open <http://127.0.0.1:8000/>; `Ctrl-C` stops it. Run pip from inside this
directory: `requirements.txt` names the tarball by relative path, and pip
resolves that from the working directory, not from the file.

### Options

```bash
python3 server.py --port 9000
python3 server.py --host 127.0.0.1
python3 server.py --host localhost --port 8080
```

The default is **`0.0.0.0` port `8000`**, because that is what a host such as
Render expects. `0.0.0.0` is every interface, so other machines on your network
can reach it. This app has no accounts and no authentication — anyone who can
reach the port can read and overwrite every block — so **for local use pass
`--host 127.0.0.1`** (or `--host localhost`).

`--host` and `--port` always win. Without them, `HOST` and `PORT` are read from
the environment when set, falling back to `0.0.0.0:8000`; that is how a deployed
instance follows the port its platform assigns.

## Using it

The screen is split in half. Each half has a menu bar of blocks, an `Edit`
overlay holding the raw header text, the aligned rows, and a footer with the pair
count and the copy buttons. The half you last clicked is active — marked by an
accent line — and the keyboard shortcuts act on it.

- **Menu bar** — `1: Request | 2: Response | 3: Session`. Click a chip to show
  that block on this side, double-click its name to rename, `×` to remove it.
  A block can only be on one side at a time.
- **Edit** — slides the textarea over the half. `Esc`, clicking outside, or the
  button closes it; typing re-runs the comparison immediately. A block with no
  headers is deleted when you close it.
- **Rows** — one row per header name. Hover lights the matching row in the other
  half; click pins the pair.
- **Notes** — free-text notes under the rows, one per block, 40,000 characters,
  never parsed and never exported with the copies.
- **Settings** (top right) — downcase field names, wrap long values, line
  numbers, difference highlighting, remember blocks in this browser, clear
  stored data, export/import JSON.

| Copy | What you get |
| --- | --- |
| **Copy original** | Exactly what you pasted — order, casing, blank lines and all. |
| **Copy altered** | One normalised `Name: value` per line, sorted, downcased if that setting is on, no alignment padding. |
| **Copy presented** | What is on screen, including the empty rows caused by headers only the other side has. |

Blocks and names survive a reload via `localStorage`. **Export JSON** downloads
every block, its name, its note and the settings; **Import JSON** *replaces* the
current set rather than merging. `headers` in the file is informational and
ignored on import — `text` is the source of truth.

### What the colours mean

| State | Looks like | Means |
| --- | --- | --- |
| same | no colour | on both sides, same value |
| changed | amber row, bar before the value, filled middle | on both sides, different values |
| only | violet row, diagonal hatching on the other side | on one side only |

Names that differ only in case (`Content-Type` / `content-type`) are the same
field, so they are underlined rather than coloured.

### Keyboard shortcuts

Unmodified keys act on the active half and are ignored while typing in a field.
`?` opens the same list inside the page.

| Key | Action |
| --- | --- |
| `1` – `9` | Show that numbered block on the active half |
| `[` / `]` | Previous / next block |
| `Tab` / `Shift+Tab` | Switch the active half |
| `S` | Swap the two sides |
| `N` | Add a block and start editing it |
| `E` | Edit the active half, caret on the pinned row |
| `M` | Focus the active half's note |
| `F2` | Rename the selected block |
| `Delete` | Remove the selected block, after confirming |
| `W` / `L` / `D` | Toggle wrap / line numbers / downcasing |
| `H` | Toggle difference highlighting |
| `,` | Open or close settings |
| `?` | Show or hide this list |
| `Esc` | Close edit area, then settings, then shortcuts |

## API

The page talks to one endpoint, which you can also call directly:

```bash
curl -s http://127.0.0.1:8000/api/diff \
  -H 'Content-Type: application/json' \
  -d '{"left":"Host: a\nAccept: */*","right":"accept: */*\nCookie: s=1","downcase":true}'
```

```json
{
  "rows": [
    {"key": "accept", "status": "only", "nameCaseDiffers": false, "cells": ["Accept: */*", null]},
    {"key": "cookie", "status": "only", "nameCaseDiffers": false, "cells": [null, "cookie: s=1"]},
    {"key": "host", "status": "only", "nameCaseDiffers": false, "cells": ["Host: a", null]}
  ],
  "sides": [
    {"error": null, "count": 2, "altered": "...", "presented": "..."},
    {"error": null, "count": 2, "altered": "...", "presented": "..."}
  ]
}
```

`cells` is always `[left, right]`, `null` where that side has no such header.
`status` is `same`, `changed`, `only`, or `none` when a side could not be parsed.
A side that cannot be parsed gets `error` and null derived copies while the other
side still renders. Bad JSON, a wrong content type and an oversized body return
400, 415 and 413.

## Deploying to Render

`render.yaml` is a Render blueprint with the two commands a manual setup would
use: build `pip install -r requirements.txt`, start `python server.py`, health
check `/`. Push the repository to GitHub, then choose **New → Blueprint** and
pick the repository, or create a Web Service by hand with those commands. The
server already binds `0.0.0.0` and reads the injected `PORT`.

A deployed instance is reachable by anyone with the URL, and has no accounts or
authentication either.

## Updating `header-sorter`

The tarball is a build artifact, committed on purpose so a clone installs
without the `header-sorter` project and without a package index. For a new
version: build the sdist there, copy it into `vendor/`, update the file name on
the only line of `requirements.txt`, and commit both. See `header-sorter`'s
README for the build command.

## Layout

```
header-diff-web/
├── README.md
├── requirements.txt          # installs the vendored header-sorter tarball
├── render.yaml               # Render blueprint: build + start command
├── vendor/
│   └── header_sorter-0.2.0.tar.gz   # header-sorter sdist, committed on purpose
├── server.py                 # serves the page and POST /api/diff
└── static/index.html         # the whole UI: menus, rows, notes band, settings
```
