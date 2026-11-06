#!/usr/bin/env python3
"""Check the local static site, its links, retained caveats, and generated freshness.

This is a site check, not a repository-wide publication/privacy approval.
"""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

if __package__:
    from .build_site import SiteError, expected_files, load_results, read_bytes, safe_path
else:
    from build_site import SiteError, expected_files, load_results, read_bytes, safe_path


class Page(HTMLParser):
    def __init__(self, source: str):
        super().__init__(convert_charrefs=True)
        self.ids: set[str] = set()
        self.references: list[tuple[str, bool]] = []
        self.h1_count = 0
        self.in_main = False
        self.main_text: list[str] = []
        self.stylesheets: list[str] = []
        self.feed(source)
        self.close()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if len(attributes) != len(attrs):
            raise SiteError("Duplicate HTML attributes are not allowed")
        if tag in {"script", "iframe", "object", "embed", "form", "base", "style"}:
            raise SiteError(f"Active or inline site content is not allowed: {tag}")
        if any(name.startswith("on") for name in attributes):
            raise SiteError("Inline event handler is not allowed")
        if "srcset" in attributes or "style" in attributes:
            raise SiteError("Use only the single local stylesheet and simple asset links")
        if tag == "meta" and "http-equiv" in attributes:
            raise SiteError("HTTP-equivalent metadata is not allowed")
        identifier = attributes.get("id")
        if identifier is not None:
            if not identifier or identifier in self.ids:
                raise SiteError(f"Empty or duplicate fragment ID: {identifier!r}")
            self.ids.add(identifier)
        if tag == "h1":
            self.h1_count += 1
        if tag == "main":
            self.in_main = True
        for key in ("href", "src", "poster", "data", "action"):
            if key in attributes:
                value = attributes[key]
                if value is None:
                    raise SiteError(f"Empty {key} attribute")
                self.references.append((value, tag == "a" and key == "href"))
        if tag == "link" and attributes.get("rel") == "stylesheet":
            href = attributes.get("href")
            if not href:
                raise SiteError("Stylesheet link is missing its href")
            self.stylesheets.append(href)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag == "main":
            self.in_main = False

    def handle_data(self, data: str) -> None:
        if self.in_main:
            self.main_text.append(data)


def check_reference(root: Path, current: str, reference: str, is_link: bool) -> None:
    try:
        target = urlsplit(reference)
    except ValueError as exc:
        raise SiteError(f"Invalid URL: {reference!r}") from exc
    if target.scheme:
        if is_link and target.scheme in {"https", "http", "mailto"}:
            return  # References are not fetched; no network is used by this checker.
        raise SiteError(f"External/unsafe asset or URL scheme: {reference!r}")
    if target.netloc:
        raise SiteError(f"Protocol-relative URL is not allowed: {reference!r}")
    try:
        path = unquote(target.path, errors="strict")
        fragment = unquote(target.fragment, errors="strict")
    except UnicodeError as exc:
        raise SiteError(f"Invalid URL encoding: {reference!r}") from exc
    if path:
        # Check the URL path separately before joining it to the document directory.
        safe_path(root, path)
        relative = str(Path(current).parent / path)
    else:
        relative = current
    destination = safe_path(root, relative)
    if not destination.is_file():
        raise SiteError(f"Unresolved local link: {reference!r} from {current}")
    if fragment:
        if destination.suffix != ".html":
            raise SiteError(f"Fragment on a non-HTML asset: {reference!r}")
        page = Page(destination.read_text(encoding="utf-8"))
        if fragment not in page.ids:
            raise SiteError(f"Unresolved fragment: {reference!r} from {current}")


def check_site(root: Path) -> None:
    root = root.resolve()
    generated = expected_files(root)
    allowed = set(generated) | {"docs/style.css"}
    docs = safe_path(root, "docs")
    for path in docs.rglob("*"):
        relative = path.relative_to(root).as_posix()
        safe_path(root, relative)
        if relative not in allowed and relative != "docs/data":
            raise SiteError(f"Unexpected site artifact: {relative}")
    texts = {}
    for relative in sorted(allowed):
        raw = read_bytes(root, relative)
        try:
            text = raw.decode("utf-8")
        except UnicodeError as exc:
            raise SiteError(f"Site asset must be UTF-8: {relative}") from exc
        if re.search(r"/(?:home|Users)/|[A-Za-z]:[\\/]Users[\\/]|file://", text, re.I):
            raise SiteError(f"Private home path in {relative}")
        if str(root.resolve()) in text:
            raise SiteError(f"Local build path in {relative}")
        if re.search(r"(?:private\.local|\.venv|\.local)(?:[/\\]|[\s\"'<>]|$)", text):
            raise SiteError(f"Private local artifact reference in {relative}")
        if re.search(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{20,})", text):
            raise SiteError(f"Possible credential in {relative}")
        texts[relative] = text
    page = Page(texts["docs/index.html"])
    if page.h1_count != 1:
        raise SiteError(f"Expected exactly one h1, found {page.h1_count}")
    if page.stylesheets != ["style.css"]:
        raise SiteError("Expected exactly one relative stylesheet: style.css")
    for reference, is_link in page.references:
        check_reference(root, "docs/index.html", reference, is_link)
    css = texts["docs/style.css"]
    # This deliberately small stylesheet needs no CSS escapes. Refusing them
    # prevents escaped @import/url tokens without introducing a CSS dependency.
    if "\\" in css or re.search(r"@import\b|url\s*\(", css, re.I):
        raise SiteError("Stylesheet must not import fonts or other network/assets, or use CSS escapes")
    body = " ".join(page.main_text).lower()
    if not re.search(r"\bfail(?:ed|ure|ures)?\b", body):
        raise SiteError("Rendered report must retain negative failure evidence")
    if not re.search(r"limitations|threats to validity", body):
        raise SiteError("Rendered report must retain limitations")
    if not re.search(r"\b(?:not|neither|no)\b", body):
        raise SiteError("Rendered report must retain negative qualifications")
    load_results(read_bytes(root, "docs/data/results.json"))
    for relative, content in generated.items():
        if read_bytes(root, relative) != content:
            raise SiteError(f"Stale generated site: {relative}; run tools/build_site.py")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        check_site(args.root.resolve())
    except (SiteError, OSError, UnicodeError) as exc:
        print(f"Site check failed: {exc}", file=sys.stderr)
        return 1
    print("Site checks passed: current, linked, UTF-8, aggregate-only local assets; nothing published.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
