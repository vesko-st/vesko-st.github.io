#!/usr/bin/env python3
"""Render a markdown post to HTML with the same page template as build_post.py.

    python3 md_to_post.py classifier-builders-rules-not-examples.md

Writes the .html next to the .md. No dependencies; supports the subset the posts use:

    ---                    front matter: title, subtitle, byline, og_desc, twitter_desc,
    key: value             and optionally footer, image (absolute URL for link previews)
    ---
    # Heading / ## Subheading
    - bullet list items
    | pipe | tables |     (second row is the separator; **bold** cells allowed)
    *A paragraph in italics right after a table becomes its note.*
    Inline: **bold**, *italic* or _italic_, [links](https://url).
"""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

from build_post import TEMPLATE, footer, social_image

LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")


def inline(text: str) -> str:
    links: list[str] = []

    def stash(m: re.Match[str]) -> str:
        links.append(f'<a href="{html.escape(m.group(2))}">{inline(m.group(1))}</a>')
        return f"\x00{len(links) - 1}\x00"

    text = LINK.sub(stash, text)
    text = html.escape(text, quote=False)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", text)
    text = re.sub(r"(?<!\w)_(?!\s)(.+?)(?<!\s)_(?!\w)", r"<em>\1</em>", text)
    return re.sub(r"\x00(\d+)\x00", lambda m: links[int(m.group(1))], text)


def split_row(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def render_table(lines: list[str]) -> str:
    head = "".join(f"<th>{inline(c)}</th>" for c in split_row(lines[0]))
    rows = "\n".join(
        "              <tr>" + "".join(f"<td>{inline(c)}</td>" for c in split_row(line)) + "</tr>"
        for line in lines[2:]
    )
    return (
        '        <div class="table-scroll">\n'
        '          <table class="results">\n'
        f"            <thead>\n              <tr>{head}</tr>\n            </thead>\n"
        f"            <tbody>\n{rows}\n            </tbody>\n"
        "          </table>\n"
        "        </div>"
    )


def is_note(para: str) -> bool:
    return bool(re.fullmatch(r"\*(?!\*)[^*].*[^*]\*", para)) and "\n" not in para


def render_body(text: str) -> str:
    parts: list[str] = []
    previous = ""
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = [line.rstrip() for line in block.strip().splitlines()]
        if not lines:
            continue
        first = lines[0]
        if first.startswith("## "):
            parts.append(f"        <h3>{inline(first[3:].strip())}</h3>")
            kind = "h3"
        elif first.startswith("# "):
            parts.append(f"        <h2>{inline(first[2:].strip())}</h2>")
            kind = "h2"
        elif first.startswith("|"):
            parts.append(render_table(lines))
            kind = "table"
        elif first.startswith("- "):
            items = "\n".join(f"          <li>{inline(line[2:].strip())}</li>" for line in lines)
            parts.append(f"        <ul>\n{items}\n        </ul>")
            kind = "ul"
        else:
            para = " ".join(line.strip() for line in lines)
            if previous == "table" and is_note(para):
                parts.append(f'        <p class="table-note">{inline(para[1:-1])}</p>')
            else:
                parts.append(f"        <p>{inline(para)}</p>")
            kind = "p"
        previous = kind
    return "\n\n".join(parts)


def read_front_matter(text: str) -> tuple[dict[str, str], str]:
    m = re.match(r"---\n(.*?)\n---\n", text, flags=re.DOTALL)
    if not m:
        raise SystemExit("missing front matter (--- ... ---) at the top of the file")
    meta = {}
    for line in m.group(1).splitlines():
        key, _, val = line.partition(":")
        if key.strip():
            meta[key.strip()] = val.strip()
    return meta, text[m.end():]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("markdown", type=Path)
    args = parser.parse_args()

    src = args.markdown.resolve()
    meta, body = read_front_matter(src.read_text())
    out = src.with_suffix(".html")
    page = TEMPLATE.format(
        title=html.escape(meta["title"]),
        subtitle=inline(meta["subtitle"]),
        byline=inline(meta["byline"]),
        og_desc=html.escape(meta["og_desc"]),
        twitter_desc=html.escape(meta["twitter_desc"]),
        footer=footer(inline(meta.get("footer", ""))),
        page=out.name,
        social_image=social_image(meta.get("image")),
        body=render_body(body),
    )
    out.write_text(page)
    print(f"Wrote {out.name}")


if __name__ == "__main__":
    main()
