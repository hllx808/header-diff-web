# header-diff-web

A local web UI for comparing two blocks of HTTP headers. Each block keeps its
original text; the app aligns both blocks into one row per header name so the
differences are visible as gaps, and lets you copy any of the three forms back
out.

No dependencies beyond Python 3.9+, and it reuses the `header-sorter` package in
`../python-packages/header-sorter` for parsing and ordering.

## Setup

Nothing to install. From the repository root:

```bash
python3 header-diff-web/server.py
```

Open <http://127.0.0.1:8001/>. Stop it with `Ctrl-C`.

Options:

```bash
python3 header-diff-web/server.py --port 9000       # different port
python3 header-diff-web/server.py --host 0.0.0.0   # listen on every interface
```

The default port is **8001**, so it can run alongside `header-sorter-web` on
8000. If you bind `0.0.0.0`, other machines on the LAN can open
`http://<your-lan-ip>:8001/` — there is no authentication, so keep it on a
network you trust.

## Using the page

The screen is split in half by a vertical rule. Each half shows one block, and
every half has the same four parts. Under both halves, between their rows and
their footers, sits the [notes](#notes) band. The half you last clicked is the *active*
one, marked by an accent line on its menu bar, and it is the half that
[keyboard shortcuts](#keyboard-shortcuts) act on:

- **Menu bar** — every block, as `1: Request | 2: Response | 3: Session`,
  separated by `|` bars with the active one underlined. Click a chip to show
  that block on this side, double-click the name to rename it in place (the
  label itself becomes editable, so the bar never changes shape; Enter or
  clicking away keeps the new name, `Esc` discards it). The `×` removes the block. A block can only be on one side at a time, so
  the other side's chip is dimmed while it is selected. Blocks are numbered by
  their position in the menu, so deleting one renumbers the rest; an unnamed
  block is just `Block`, and the number in front of it does the identifying.
- **Edit** — slides the input area down over this half. It overlays the rows
  instead of pushing the split down, and the button toggles between `Edit` and
  `Close`. Opening it focuses the textarea, with the caret at the end of the
  block so you can keep typing straight away. `Esc`, clicking outside the area,
  or clicking the button again all dismiss it. There is no double-click shortcut:
  `E` is the keyboard way in, and with a row pinned it puts the caret on that
  header's line instead of at the end. Typing updates the comparison as you go. If the block holds no
  headers at all, `Esc` deletes it instead of leaving an empty one behind — a
  just-added block, a block you cleared out, or one that was never filled in. A blank row still keeps
  its line height, so rows only one side has stay aligned even with line
  numbers turned off.
- **Rows** — the aligned comparison. A thin line-number gutter sits on the
  left of each half when enabled, and differences are coloured (see
  [what the colours mean](#what-the-colours-mean)). Hovering a row lights its
  counterpart; clicking pins the pair.
- **Footer** — the real number of `key: value` pairs in this block, and the
  three copy buttons.

Blocks and their names survive a reload through `localStorage` unless you turn
that off in Settings.

### Notes

Under the rows, spanning both halves and split by the same vertical rule, is the
notes band. Each side holds a free-text note for the block that side is showing,
because the note belongs to the block: point a half at another block and its
note changes with it.

- Prose, not headers. A note is never parsed, sorted, downcased or paired, is
  not counted in the pair total, and never appears in any of the three copies.
- **40,000 characters** per note. The count appears in the band's bar while a
  note has focus; past the limit, the text is trimmed back to the limit.
- Saved as you type, with the write to `localStorage` debounced so a long note
  does not stringify the whole block list on every keystroke.
- One resize for both sides: drag the bar. The height and the collapsed state
  are per browser and are not part of an export.
- The chevron in the bar collapses the band. `M` focuses the active half's note,
  expanding the band first if it was collapsed.
- A block with no headers is still deleted by `Esc`, but if it has a note a
  confirmation names what is about to be lost.
- An empty note shows the block's number and name with what the space is for.

### The three copies

Each block is held in three forms, and the footer copies whichever you ask for:

| Button | What you get |
| --- | --- |
| **Copy original** | The exact text you pasted — original order, casing, blank lines and all. Works even when the block cannot be parsed. |
| **Copy altered** | The cleaned one-header-per-line version: normalised `Name: value`, sorted, downcased if that setting is on, **no alignment padding**. |
| **Copy presented** | What you are looking at in that half, including the empty rows caused by headers the other side has. |

Only the original is stored; the other two are derived from it and the
settings, so changing the settings changes them without touching your paste. A
block's note is stored beside the original and exported with it, but it is not
part of any of the three.

### Settings (top right)

- **Downcase field names** — lowercases header names in the altered and
  presented copies. This applies to every block immediately, and turning it off
  brings your original casing back, because the raw text is never rewritten.
- **Wrap long values** — off means a long value runs past the edge of its half
  and you scroll that half horizontally (the line-number gutter stays put).
- **Line numbers** — the gutter on the left of each half. The pair count in the
  footer is separate and always shown.
- **Highlight differences** — the row colours, the bar beside a changed value,
  the hatched blocks and the name underlines. Turning it off leaves plain
  alignment; `H` toggles it.
- **Remember blocks in this browser** — turning this off stops writing to
  `localStorage`. It does not delete what is already there.
- **Clear stored data** — deletes the stored blocks and names. Settings are
  left alone.
- **Export JSON / Import JSON** — every block, its name and the settings as one
  file; see [Exporting and importing](#exporting-and-importing).

### Exporting and importing

**Export JSON** downloads `header-diff-<date>.json`:

```json
{
  "app": "header-diff-web",
  "version": 1,
  "exported": "2026-11-03T12:00:00.000Z",
  "settings": {"downcase": true, "wrap": true, "gutters": true, "highlight": true, "persist": true},
  "blocks": [
    {
      "id": "b1-abcde",
      "name": "Request",
      "note": "Captured before the retry.",
      "text": "Host: example.com\nAccept: */*",
      "headers": [{"name": "Host", "value": "example.com"}, {"name": "Accept", "value": "*/*"}]
    }
  ]
}
```

`headers` is derived from `text` for reading and grepping and is **ignored on
import**: `text` is the source of truth, so a hand-edited copy cannot change what
the page stores. `note` is carried with the block.

**Import JSON** reads a file and **replaces** the current blocks and settings,
because it is a restore rather than a merge — export first if you want to keep
both. Unusable entries are skipped and counted in the status line instead of
aborting the import, and any name the sanitiser had to change is reported the
same way. With **Remember blocks in this browser** off, the import applies to
this session only and the status line says so.

Blocks are numbered by position, so a file does not carry numbers: the order of
`blocks` is the numbering on load.

## Keyboard shortcuts

One half is **active** — the one you last clicked, marked by an accent line along
its menu bar. Unmodified keys act on that half. They are ignored while you are
typing in a field, and `?` opens the same list inside the page.

| Key | Action |
| --- | --- |
| `1` – `9` | Show that numbered block on the active half. A block already shown on the other side is skipped, like the dimmed chip. |
| `[` / `]` | Previous / next block on the active half, skipping the block on the other side. |
| `Tab` / `Shift+Tab` | Switch the active half. Only fires while a half's rows hold focus (click into a half first), so ordinary focus movement still works. |
| `S` | Swap the two sides. |
| `N` | Add a block and start editing it: it goes to an empty side, otherwise it replaces the active half's selection so you can paste straight in. |
| `E` | Edit the active half's headers, with the caret on the pinned row's line when a row is pinned. |
| `M` | Focus the active half's note, expanding the notes band first if it was collapsed. |
| `F2` | Rename the selected block, same as double-clicking its name. |
| `Delete` | Remove the selected block, after a confirmation. |
| `W` / `L` / `D` | Toggle word wrap / line numbers / downcasing. These are the settings you flip while reading, so they stay on one key. |
| `H` | Toggle difference highlighting. |
| `,` | Open or close settings. |
| `?` | Show or hide the shortcut list. |
| `Esc` | Close the edit area, then settings, then the shortcut list — one layer per press. On a block with no headers, it deletes the block, asking first when the block has a note. |

## How rows are matched

Every block is parsed into `(name, value)` pairs and sorted. Rows are grouped
by **lowercased field name**, and repeats of one name are paired **by value
before position**. When a side has no such header its cell is blank, and the
blank space is the point: identical headers sit on the same line and only the
differences are staggered.

### What the colours mean

| State | Looks like | Means |
| --- | --- | --- |
| same | no colour | on both sides, same value |
| changed | amber row, amber bar before the value, filled middle of the value | on both sides, different values |
| only | violet row, diagonal hatching on the other side | on one side only |

The row tint and the tinted line number are the coarse signal — you can scan a
long block and see the differences as bands. The bar and the filled middle are
the fine one. Only the divergent middle is filled, because a changed row is by
construction the same field name, so the name and any shared prefix or suffix
are noise.

A name that differs **only in case** (`Content-Type` vs `content-type`) is the
same field — HTTP names are case-insensitive — so it is not coloured; both names
are underlined instead. That cannot arise with *Downcase field names* on,
because both sides then print the same.

Hovering a row lights its counterpart in the other half, and clicking **pins**
the pair (a stronger accent tint, and the line number stays lit) until you click
it again, click another row, or press `Esc`. Pinning is immediate: the second
click of a double-click is ignored rather than unpinning what the first click
pinned. The pin is tied to the field name and which repeat it is, not to a row
number, so it survives re-parsing. This is what makes long wrapped values
checkable: a tall row on one side can push its counterpart off-screen, and a
hover cannot survive scrolling the other half.

With a pair pinned, `E` opens the active half's editor with the caret on that
header's line. The line is found by matching the value first and falling back to
the nth occurrence of the name, because repeats are paired by value rather than
position — so a reordered duplicate still lands on its own copy instead of the
first one. A half that has no such header (the hatched side of an `only` row)
opens at the end of the block as usual.

### Why repeats are paired by value

Pairing the third `Set-Cookie` with the third `Set-Cookie` sounds right until one
side has a cookie the other doesn't. Insert one near the top and every later
cookie shifts down by one, so the whole tail of the block reports as changed.

```text
left                     right
set-cookie: a            set-cookie: new
set-cookie: b            set-cookie: a
                         set-cookie: b
```

Only `new` actually differs. Under occurrence pairing:

```text
1  set-cookie: a          set-cookie: new    changed
2  set-cookie: b          set-cookie: a      changed
3                        set-cookie: b      only
```

Two rows are flagged that are in fact on both sides, and the one insertion —
the thing worth noticing — is buried. Pairing by value first gives:

```text
1  set-cookie: a          set-cookie: a      same
2  set-cookie: b          set-cookie: b      same
3                        set-cookie: new    only
```

The pairing runs in two passes per name:

1. **Equal values pair first**, in order, so a header untouched on both sides
   never moves.
2. **What is left pairs in order** — the old occurrence rule, kept as the
   fallback, so a value that genuinely changed still lands on one row beside its
   counterpart instead of splitting into an `only` pair.

That second pass is why a single changed header still reads as one row:

```text
left                     right                 rendered
set-cookie: a            set-cookie: z         1  set-cookie: a  |  set-cookie: z   changed
```

Two blocks holding the same cookies in a different order pair entirely by value,
so they read as matching rows rather than as two changes.

Sorting is case-insensitive and stable, always, regardless of the downcase
setting:

```text
banana   }  sorted as   Apple
Apple    }             apple
carrot   }             banana
apple    }             carrot
```

`A` and `a` are the same letter for ordering; two headers that lower to the
same name keep the order they were pasted in. Downcasing only decides whether
the output *prints* `Apple` or `apple`.

Header names are case-insensitive in HTTP (RFC 9110 §5.1), which is why matching
ignores case. Values are **not** touched: `Authorization: Bearer AbC123` keeps
its case, since field values are case-sensitive.

Duplicate field names are legal and are shown, not merged or rejected. RFC 9110
§5.2 treats repeated lines for one field as a comma-combined list (§5.3 allows
it for list-based fields), and `Set-Cookie` repeats in practice and cannot be
comma-combined. `Cookie` is the exception that may only appear once (RFC 6265
§5.4). Duplicate `Content-Length` or `Transfer-Encoding` is worth eyeballing —
that is the request-smuggling surface.

## API

The page talks to one endpoint, which you can use directly:

```bash
curl -s http://127.0.0.1:8001/api/diff \
  -H 'Content-Type: application/json' \
  -d '{"left":"Host: a\nAccept: */*","right":"accept: */*\nCookie: s=1","downcase":true}'
```

```json
{
  "rows": [
    {"key": "accept", "status": "only", "nameCaseDiffers": false,
     "cells": ["Accept: */*", null]},
    {"key": "cookie", "status": "only", "nameCaseDiffers": false,
     "cells": [null, "cookie: s=1"]},
    {"key": "host", "status": "only", "nameCaseDiffers": false,
     "cells": ["Host: a", null]}
  ],
  "sides": [
    {"error": null, "count": 2, "altered": "...", "presented": "..."},
    {"error": null, "count": 2, "altered": "...", "presented": "..."}
  ]
}
```

`cells` is always `[left, right]`; `null` means that side has no such header.
`status` is `same`, `changed` or `only`, or `none` when a side could not be
parsed and there is nothing to compare. `nameCaseDiffers` is true when the two
names differ only in casing. A side that cannot be parsed gets `error`,
`count: null`, and both derived copies `null`, while the other side still
renders. Request problems (bad JSON, wrong content type, oversized body) return
400/415/413 instead.

## Security

This is a local single-user tool: no accounts, no authentication, no TLS, and
the server listens on `127.0.0.1` unless you pass `--host`. Everything below
assumes that posture. Exposed with `--host 0.0.0.0`, anyone who can reach the
port can read and overwrite every block — the tool has no concept of users.

Every meaningful weak point is an **input**, so each one has a defined landing
place and handling:

| Input | Reaches | Handling |
| --- | --- | --- |
| Header text in the edit area | Your browser, `POST /api/diff` | Held as an opaque string and rendered only through `textContent`, never as markup. A block that fails to parse produces an error line, not an exception in the page. |
| Block names | Menu bar, the delete confirmation, `localStorage`, and any export | Cleaned at commit *and* at load by `normalizeName()` (see [Names](#names)). |
| `localStorage` on boot | The page's state | Settings accepted only as booleans, block text only as strings, block numbers only as integers, selections checked against the blocks that exist. Anything else is ignored and the defaults apply. |
| `POST /api/diff` body | The server | `Content-Type: application/json` required (415), `Content-Length` capped at 2 MB (413), JSON decoded once by `json.loads`, `left`/`right` must be strings (400), `downcase` counts only when literally `true`. Nothing is evaluated. |
| URL path | Static file serving | Only `/` and `/index.html` are served, from a fixed path inside the project. The request path never becomes a file path, so there is no directory listing and no `../` traversal. |
| Block notes | Notes band, export file, import | Free text, capped at 40,000 characters, assigned only to a textarea's `value` and never parsed as markup; exported per block; clamped on import and counted when it had to be shortened. |
| Imported JSON file | The page's state | Read as text and `JSON.parse`d, never evaluated. Rejected at 5 MB, 500 blocks or a block larger than 1 MB; `app` and `version` are checked; every block needs a string `text`; names go through `normalizeName()`; an `id` is kept only if it is 1–64 letters, digits, `-` or `_` and unique, otherwise it is regenerated; settings are taken only as booleans for known keys; unusable blocks are skipped and counted. |

Stalled connections are dropped after 10 seconds so a slow reader cannot pin a
worker thread indefinitely.

### Names

A name is the one field that is pure user text and ends up outside the rows: in
the menu bar, in the delete confirmation, and in any export. `normalizeName()`
is the single gate, used by the rename field, by `localStorage` on load, and by
import when it exists:

- **Unicode NFC first**, so a composed and a decomposed accent compare equal and
  cannot become two identical-looking names in an export.
- **Control characters and line breaks become spaces.** A `maxLength` attribute
  cannot enforce a cap on a contenteditable, and a newline would break both the
  chip and any line-based export.
- **Zero-width and bidi-override characters are removed** (`U+200B`–`U+200F`,
  `U+202A`–`U+202E`, `U+2066`–`U+2069`, `U+FEFF`). These can make a stored name
  display as something else — the "trojan source" trick — and would travel
  silently into an export.
- **Whitespace collapsed, ends trimmed, then capped at 40 code points**
  (`Array.from` rather than `.length`, so an emoji counts as one), and defaulted
  to `Block` when nothing is left.

The cap is enforced three ways, because any single one can be bypassed: a
`beforeinput` check on typed text, a `paste` handler that inserts plain text
through a `Range` within the remaining budget, and the commit-time sanitiser
that everything actually relies on. `drop` is blocked so dragged text cannot
skip the paste path, an `input` pass collapses anything the browser inserted as
markup, and `plaintext-only` is used where supported (with the sanitiser still
covering the browsers that lack it). Enter during IME composition is left to the
IME, so a rename is never committed mid-word.

### What the browser is allowed to load

Responses carry `Content-Security-Policy: default-src 'none'` with only inline
script and style permitted, `connect-src 'self'`, `img-src 'self'`,
`base-uri`/`form-action` set to `'none'` and `frame-ancestors 'none'`, plus
`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
`Referrer-Policy: no-referrer` and `Cache-Control: no-store`. The page therefore
cannot fetch a remote script, cannot be framed, cannot post a form elsewhere and
cannot load an external image.

Inline script *is* allowed because the whole UI is one self-contained file. The
defence that matters is that the page never builds HTML from data: there is no
`innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write`, `eval` or
`new Function` anywhere in it, and header text, names and error messages are all
assigned with `textContent`. Keep it that way — one `innerHTML` on a header
value would undo the rest. The `Server` header reports the app name only, not
the Python version.

### Not covered

- No authentication or transport encryption; loopback by default.
- Anyone with access to the browser profile can read the blocks out of
  `localStorage`. "Clear stored data" removes them from storage, not from the
  clipboard, the page history or an export you already saved.
- Duplicate headers are displayed, not merged or flagged. Duplicate
  `Content-Length` or `Transfer-Encoding` is worth a look but is not warned
  about — this is a viewer, not a validator.
- Imported data is shown, not interpreted: a name or header value can say
  anything and is always rendered as text. Importing a file you did not export
  yourself is still a way to put arbitrary header text into the page — the same
  as pasting it.

## Notes and limits

- Local tool, no accounts, no authentication, single user.
- Two halves at a time; any number of blocks can be stored and compared in
  pairs.
- The browser does the layout and the settings; the server only parses and
  aligns, so a page reload never changes the data.
- Values are compared exactly as parsed, so whitespace inside a value counts.
- There is no "differences only" filter. Hiding rows would break the row
  numbering the two halves share, and "Copy presented" would stop matching what
  is on screen.
- Import replaces rather than merges. There is one file format, version 1, and
  an unknown version is refused instead of half-read.

## Layout

```
header-diff-web/
├── README.md
├── server.py          # serves the page and POST /api/diff
└── static/index.html  # the whole UI: menus, rows, notes band, settings
```
