"""Web server for the header diff UI.

Install the dependency, then run it from this directory:

    python3 -m pip install -r requirements.txt
    python3 server.py

binds to 0.0.0.0:8000 by default
Open http://127.0.0.1:8000/ locally; pass --host/--port to change either.
"""

from __future__ import annotations

import argparse
import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from header_sorter import InvalidHeaderError, parse_headers

BASE_DIR = Path(__file__).resolve().parent
INDEX = BASE_DIR / "static" / "index.html"
MAX_BODY = 2_000_000


def parse_side(text: str, downcase: bool) -> dict[str, Any]:
    """Read one pasted block into ordered (name, value) items.

    Ordering comes from the package: sorted by lowercased name, stable for equal
    names (pasted order wins the tie). ``items`` is ``None`` when the block
    cannot be parsed, which keeps "no headers" distinct from "unreadable".
    """
    if not text.strip():
        return {"error": None, "count": 0, "altered": "", "items": []}

    try:
        headers = parse_headers(text)
    except InvalidHeaderError as exc:
        return {"error": str(exc), "count": None, "altered": None, "items": None}

    items: list[dict[str, str]] = []
    lines: list[str] = []
    for header in sorted(headers, key=lambda h: h.name.lower()):
        name = header.name.lower() if downcase else header.name
        items.append({"name": name, "lower": header.name.lower(), "value": header.value})
        lines.append(f"{name}: {header.value}")
    return {
        "error": None,
        "count": len(headers),
        "altered": "\n".join(lines),
        "items": items,
    }


def pair_items(
    lefts: list[dict[str, str]], rights: list[dict[str, str]]
) -> list[tuple[dict[str, str] | None, dict[str, str] | None]]:
    """Pair the repeats of one field name: equal values first, then by position.

    Value-first pairing stops an inserted header from shifting every later one,
    and the positional fallback keeps a genuinely changed value on a single row
    instead of splitting it into an ``only`` pair.
    """
    partner: list[int | None] = [None] * len(lefts)
    used = [False] * len(rights)

    for index, left in enumerate(lefts):
        for right_index, right in enumerate(rights):
            if used[right_index] or right["value"] != left["value"]:
                continue
            partner[index] = right_index
            used[right_index] = True
            break

    for index in range(len(lefts)):
        if partner[index] is not None:
            continue
        for right_index in range(len(rights)):
            if used[right_index]:
                continue
            partner[index] = right_index
            used[right_index] = True
            break

    rows: list[tuple[dict[str, str] | None, dict[str, str] | None]] = []
    for index, left in enumerate(lefts):
        right_index = partner[index]
        rows.append((left, None if right_index is None else rights[right_index]))
    for right_index, right in enumerate(rights):
        if not used[right_index]:
            rows.append((None, right))
    return rows


def build_diff(left_text: str, right_text: str, downcase: bool) -> dict[str, Any]:
    """Align two pasted blocks into rows grouped by lowercased field name."""
    left = parse_side(left_text, downcase)
    right = parse_side(right_text, downcase)

    # A block that could not be parsed has nothing to compare against, so the
    # other side's rows stay uncoloured instead of all reading as "only".
    comparable = left["items"] is not None and right["items"] is not None

    groups: dict[str, tuple[list[dict[str, str]], list[dict[str, str]]]] = {}
    for side, items in enumerate((left["items"] or [], right["items"] or [])):
        for item in items:
            groups.setdefault(item["lower"], ([], []))[side].append(item)

    rows = []
    for name in sorted(groups):
        lefts, rights = groups[name]
        for l_item, r_item in pair_items(lefts, rights):
            if l_item is None or r_item is None:
                status = "only"
                case_differs = False
            else:
                same = l_item["value"] == r_item["value"]
                status = "same" if same else "changed"
                case_differs = l_item["name"] != r_item["name"]
            rows.append(
                {
                    "key": name,
                    "status": status if comparable else "none",
                    "nameCaseDiffers": case_differs,
                    "cells": [
                        None if l_item is None else f"{l_item['name']}: {l_item['value']}",
                        None if r_item is None else f"{r_item['name']}: {r_item['value']}",
                    ],
                }
            )

    sides = []
    for index, side in enumerate((left, right)):
        presented = (
            None
            if side["altered"] is None
            else "\n".join(row["cells"][index] or "" for row in rows)
        )
        sides.append(
            {
                "error": side["error"],
                "count": side["count"],
                "altered": side["altered"],
                "presented": presented,
            }
        )
    return {"rows": rows, "sides": sides}


class HeaderDiffHandler(BaseHTTPRequestHandler):
    """Serves the page and a single JSON endpoint backed by header_sorter."""

    server_version = "HeaderDiffUI/0.1"
    # Do not advertise the Python version in the Server header.
    sys_version = ""
    # Drop a stalled connection instead of pinning its thread forever.
    timeout = 10

    def version_string(self) -> str:
        return self.server_version

    def do_GET(self) -> None:  # noqa: N802 - http.server naming
        if self.path in ("/", "/index.html"):
            try:
                body = INDEX.read_bytes()
            except OSError:
                self._json(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    {"error": "missing static/index.html"},
                )
                return
            self._respond(HTTPStatus.OK, body, "text/html; charset=utf-8")
        else:
            self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802 - http.server naming
        if self.path != "/api/diff":
            self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        if not self.headers.get("Content-Type", "").startswith("application/json"):
            self._json(
                HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {"error": "expected application/json"}
            )
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = -1
        if length < 0 or length > MAX_BODY:
            self._json(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "request body too large"}
            )
            return

        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
            left = payload["left"]
            right = payload["right"]
            downcase = payload.get("downcase", False)
            if not isinstance(left, str) or not isinstance(right, str):
                raise TypeError
        except (ValueError, TypeError, KeyError):
            self._json(
                HTTPStatus.BAD_REQUEST,
                {"error": 'expected {"left": "...", "right": "...", "downcase": bool}'},
            )
            return

        self._json(HTTPStatus.OK, build_diff(left, right, downcase is True))

    def _respond(self, status: HTTPStatus, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        # The page is one self-contained file: no external loads, no framing, no
        # form posts, and the only fetch it makes is back to this origin. Inline
        # script and style are allowed because they are the page itself; the real
        # defence is that the UI never builds markup from data.
        self.send_header(
            "Content-Security-Policy",
            "default-src 'none'; script-src 'unsafe-inline'; "
            "style-src 'unsafe-inline'; connect-src 'self'; img-src 'self'; "
            "base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
        )
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: HTTPStatus, data: dict) -> None:
        self._respond(status, json.dumps(data).encode("utf-8"), "application/json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Serve the header diff UI.")
    parser.add_argument(
        "--host",
        default=os.environ.get("HOST", "0.0.0.0"),
        help="bind address (default: 0.0.0.0; HOST is used when set)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT", "8000")),
        help="port (default: 8000; PORT is used when set)",
    )
    args = parser.parse_args(argv)

    server = ThreadingHTTPServer((args.host, args.port), HeaderDiffHandler)
    host, port = server.server_address[:2]
    # 0.0.0.0 is not a browsable address; point the reader at loopback.
    shown = "127.0.0.1" if host in ("0.0.0.0", "::") else host
    print(
        f"Header diff UI on http://{shown}:{port}/  "
        f"(bound to {host}; Ctrl-C to stop)",
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
