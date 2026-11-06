#!/usr/bin/env python3
"""Render the authoritative report locally; this tool never publishes anything."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path, PurePosixPath
import sys

import markdown


class SiteError(ValueError):
    """Invalid or unavailable site input."""


def safe_path(root: Path, relative: str) -> Path:
    """Refuse traversal and symlinks, including symlinked parent directories."""
    parts = relative.split("/")
    if not relative or "\\" in relative or "\0" in relative or any(
        part in ("", ".", "..") for part in parts
    ) or PurePosixPath(relative).is_absolute():
        raise SiteError(f"Unsafe relative path: {relative!r}")
    path = root.resolve()
    for part in parts:
        path = path / part
        if path.is_symlink():
            raise SiteError(f"Symlink refused: {relative}")
    return path


def read_bytes(root: Path, relative: str) -> bytes:
    try:
        return safe_path(root, relative).read_bytes()
    except FileNotFoundError as exc:
        raise SiteError(f"Missing required input: {relative}; site build is pending.") from exc


def split_frontmatter(source: str) -> tuple[dict[str, str], str]:
    """Strip a leading YAML block without interpreting YAML or changing body text."""
    lines = source.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return {}, source
    for end in range(1, len(lines)):
        if lines[end].strip() in ("---", "..."):
            metadata = {}
            for line in lines[1:end]:
                key, separator, value = line.partition(":")
                if separator:
                    metadata[key.strip()] = value.strip()
            return metadata, "".join(lines[end + 1 :])
    raise SiteError("Unclosed YAML frontmatter in report.md")


def load_results(raw: bytes) -> object:
    def reject_constant(value: str) -> None:
        raise ValueError(f"Non-JSON numeric constant: {value}")

    try:
        return json.loads(raw.decode("utf-8"), parse_constant=reject_constant)
    except (UnicodeError, ValueError) as exc:
        raise SiteError(f"Invalid UTF-8 JSON in data/results.json: {exc}") from exc


def render_report(source: str) -> str:
    metadata, body = split_frontmatter(source)
    renderer = markdown.Markdown(extensions=["fenced_code", "tables", "toc"], output_format="html5")
    article = renderer.convert(body)
    toc = getattr(renderer, "toc", None)
    if not isinstance(toc, str):
        raise SiteError("The Markdown TOC extension did not provide HTML")
    for alignment in ("left", "right", "center"):
        article = article.replace(
            f'style="text-align: {alignment};"', f'class="align-{alignment}"'
        )
    # The wrappers preserve table content while allowing narrow-screen scrolling.
    article = article.replace(
        "<table>",
        '<div class="table-scroll" role="region" aria-label="Report table" tabindex="0"><table>',
    ).replace("</table>", "</table></div>")
    article = article.replace("<pre>", '<pre tabindex="0">')
    heading, separator, remainder = article.partition("</h1>")
    if not separator:
        raise SiteError("The report must have a main heading")
    title = html.escape(metadata.get("title", "Technical report"), quote=True)
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <a class="skip-link" href="#report">Skip to report</a>
  <main id="report">
{heading}</h1>
    <nav aria-label="Table of contents">
      <details>
        <summary>Contents</summary>
{toc}
      </details>
    </nav>
{remainder}
  </main>
  <footer>Generated from <code>report.md</code>; aggregate-only scope.</footer>
</body>
</html>
'''


def expected_files(root: Path) -> dict[str, bytes]:
    try:
        source = read_bytes(root, "report.md").decode("utf-8")
    except UnicodeError as exc:
        raise SiteError("report.md must be UTF-8") from exc
    results = read_bytes(root, "data/results.json")
    load_results(results)
    # CSS is the one hand-maintained site asset, not a generated second template.
    read_bytes(root, "docs/style.css").decode("utf-8")
    return {
        "docs/index.html": render_report(source).encode("utf-8"),
        "docs/data/results.json": results,
        "docs/.nojekyll": b"",
    }


def build(root: Path) -> None:
    outputs = expected_files(root)
    # Validate every destination before writing any of them.
    destinations = {name: safe_path(root, name) for name in outputs}
    for name, content in outputs.items():
        destination = destinations[name]
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        build(args.root)
    except (SiteError, OSError, UnicodeError) as exc:
        print(f"Site build failed: {exc}", file=sys.stderr)
        return 1
    print("Built docs/index.html and byte-exact aggregate results locally; nothing published.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
