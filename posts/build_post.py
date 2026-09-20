#!/usr/bin/env python3
"""Assemble the Jev post from editable text files in content/.

Edit the plain-text files in ``content/`` (prose, one section per file) and run:

    python3 build_post.py

This regenerates ``typesafe-jev-vs-claude.html``. Tables are data (kept below) so
the prose files stay clean; drop a token on its own line to place an asset:

    [[FIGURE]]            the summary card image
    [[PROMPT]]            the prompt example (content/prompt.txt)
    [[TABLE:accuracy]]    accuracy table
    [[TABLE:cost]]        cost table
    [[TABLE:coolidge]]    Grace-Coolidge table
    [[PDF]]               the "read the full write-up" button

Inline formatting in the prose files: **bold**, _italic_, and [links](https://url).
"""

from __future__ import annotations

import html
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONTENT = HERE / "content"
OUT = HERE / "typesafe-jev-vs-claude.html"

# ── Table data (plain rendering, PDF/booktabs style) ─────────────────────────
ACCURACY = {
    "caption": "Accuracy by system and dataset (measured, n = 100, seed 42).",
    "headers": ["System", "CommonsenseQA", "MMLU-CF", "RACE-H"],
    "rows": [
        ["Claude Haiku 4.5", "88.0%", "64.0%", "89.0%"],
        ["Claude Haiku 4.5 (low)", "90.0%", "74.0%", "93.0%"],
        ["Claude Haiku 4.5 (medium)", "90.0%", "75.0%", "94.0%"],
        ["Claude Sonnet 5", "90.0%", "73.0%", "94.0%"],
        ["Claude Sonnet 5 (low)", "87.0%", "76.0%", "96.0%"],
        ["Claude Sonnet 5 (medium)", "89.0%", "79.0%", "97.0%"],
        ["Claude Opus 5", "90.0%", "79.0%", "95.0%"],
        ["Claude Opus 5 (low)", "95.0%", "84.0%", "96.0%"],
        ["Claude Opus 5 (medium)", "93.0%", "82.0%", "96.0%"],
        ["TypeSafe Jev", "91.0%", "80.0%", "95.0%"],
    ],
}

COST = {
    "caption": "Cost in USD per 1,000 questions (metered tokens \u00d7 published rates).",
    "headers": ["System", "CommonsenseQA", "MMLU-CF", "RACE-H"],
    "rows": [
        ["Claude Haiku 4.5", "$0.109", "$0.137", "$0.506"],
        ["Claude Haiku 4.5 (low)", "$1.345", "$1.832", "$2.317"],
        ["Claude Haiku 4.5 (medium)", "$1.683", "$2.464", "$2.961"],
        ["Claude Sonnet 5", "$0.263", "$0.339", "$1.334"],
        ["Claude Sonnet 5 (low)", "$0.263", "$0.443", "$1.334"],
        ["Claude Sonnet 5 (medium)", "$0.263", "$0.417", "$1.334"],
        ["Claude Opus 5", "$0.658", "$0.822", "$3.335"],
        ["Claude Opus 5 (low)", "$1.123", "$1.544", "$3.437"],
        ["Claude Opus 5 (medium)", "$1.542", "$2.140", "$3.652"],
        ["TypeSafe Jev", "$0.015", "$0.016", "$0.031"],
    ],
}

COOLIDGE = {
    "caption": "Grace-Coolidge (n = 40): accuracy, latency, and cost (~20k-token article per call).",
    "headers": ["System", "Accuracy", "Avg latency", "Cost / 1k"],
    "rows": [
        ["Claude Haiku 4.5", "70.0%", "962 ms", "$18.52"],
        ["Claude Haiku 4.5 (low)", "90.0%", "3007 ms", "$19.79"],
        ["Claude Haiku 4.5 (medium)", "90.0%", "3431 ms", "$20.00"],
        ["Claude Sonnet 5", "87.5%", "1548 ms", "$51.88"],
        ["Claude Sonnet 5 (low)", "87.5%", "1524 ms", "$51.91"],
        ["Claude Sonnet 5 (medium)", "85.0%", "1472 ms", "$51.90"],
        ["Claude Opus 5", "92.5%", "2252 ms", "$129.69"],
        ["Claude Opus 5 (low)", "90.0%", "1960 ms", "$129.95"],
        ["Claude Opus 5 (medium)", "90.0%", "2181 ms", "$130.21"],
        ["TypeSafe Jev", "90.0%", "429 ms", "$0.84"],
    ],
}

SALES = {
    "caption": "Customer/sales-style tasks (n = 500 test, seed 13). Accuracy against the "
    "majority-class baseline, published SOTA*, and ECE (expected calibration error, "
    "lower is better). *Published SOTA are supervised models trained specifically "
    "for each task \u2014 different inputs, label sets, or evaluation subsets \u2014 so "
    "they are not directly comparable to this zero-shot setup; \u201c\u2014\u201d marks "
    "tasks with no comparable published benchmark.",
    "headers": ["Task", "Majority", "Published SOTA*", "Claude Haiku 4.5", "Claude Sonnet 5", "TypeSafe Jev", "Haiku ECE", "Sonnet ECE", "Jev ECE"],
    "rows": [
        ["Amazon QA \u2014 yes/no (Noul)", "73.0%", "76.8%", "61.1%", "60.4%", "62.8%", "0.201", "0.098", "0.076"],
        ["Persuasion \u2014 did they donate? (Noul)", "54.0%", "\u2014", "71.4%", "70.7%", "71.2%", "0.239", "0.214", "0.219"],
        ["Persuasion \u2014 strategy, 18-way (Choice)", "18.8%", "79.5%", "40.7%", "52.6%", "44.2%", "0.445", "0.196", "0.245"],
        ["Craigslist \u2014 reached a deal? (Noul)", "77.6%", "\u2014", "90.2%", "92.8%", "91.8%", "0.044", "0.034", "0.015"],
    ],
}

TABLES = {"accuracy": ACCURACY, "cost": COST, "coolidge": COOLIDGE, "sales": SALES}


# ── Rendering helpers ────────────────────────────────────────────────────────
def inline(text: str) -> str:
    text = html.escape(text, quote=False)
    text = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"_(.+?)_", r"<em>\1</em>", text)
    return text


def render_table(spec: dict) -> str:
    headers = spec["headers"]
    # Highlight Jev wherever it appears: as a row (MC tables) or a column (sales table).
    jev_col = next((i for i, h in enumerate(headers) if h.strip() == "TypeSafe Jev"), None)
    head = "".join(
        f'<th{" class=\"jev\"" if i == jev_col else ""}>{html.escape(h)}</th>'
        for i, h in enumerate(headers)
    )
    body_rows = []
    for row in spec["rows"]:
        is_jev_row = str(row[0]).strip() == "TypeSafe Jev"
        tr_cls = ' class="jev"' if is_jev_row else ""
        cells = "".join(
            f'<td{" class=\"jev\"" if (not is_jev_row and i == jev_col) else ""}>'
            f"{html.escape(c)}</td>"
            for i, c in enumerate(row)
        )
        body_rows.append(f"              <tr{tr_cls}>{cells}</tr>")
    body = "\n".join(body_rows)
    return (
        '        <div class="table-scroll">\n'
        '          <table class="results">\n'
        f"            <caption>{html.escape(spec['caption'])}</caption>\n"
        f"            <thead>\n              <tr>{head}</tr>\n            </thead>\n"
        f"            <tbody>\n{body}\n            </tbody>\n"
        "          </table>\n"
        "        </div>"
    )


def render_prompt() -> str:
    raw = (CONTENT / "prompt.txt").read_text().rstrip("\n")
    escaped = html.escape(raw, quote=False)
    escaped = re.sub(
        r"^(System:|User:)",
        r'<span class="lbl">\1</span>',
        escaped,
        flags=re.MULTILINE,
    )
    return f'<pre class="prompt">{escaped}</pre>'


def render_figure() -> str:
    return (
        "        <figure>\n"
        '          <img src="results-card.png" alt="Summary of results: TypeSafe Jev vs '
        'Claude Haiku 4.5, Sonnet 5, and Opus 5 across four multiple-choice benchmarks.">\n'
        "          <figcaption>A summary of the results. Cost is in USD per 1,000 "
        "long-context questions.</figcaption>\n"
        "        </figure>"
    )


def render_pdf() -> str:
    return '        <p><a class="cta" href="typesafe-jev-vs-claude.pdf">Read the full write-up (PDF)</a></p>'


ASSETS = {
    "FIGURE": render_figure,
    "PROMPT": render_prompt,
    "PDF": render_pdf,
}


def render_asset(token: str) -> str:
    if token.startswith("TABLE:"):
        return render_table(TABLES[token.split(":", 1)[1]])
    return ASSETS[token]()


def render_section(text: str) -> str:
    parts: list[str] = []
    for block in re.split(r"\n\s*\n", text.strip()):
        block = block.strip()
        if not block:
            continue
        m = re.fullmatch(r"\[\[(.+?)\]\]", block)
        if m:
            parts.append(render_asset(m.group(1)))
        elif block.startswith("# "):
            parts.append(f"        <h2>{inline(block[2:].strip())}</h2>")
        else:
            para = " ".join(line.strip() for line in block.splitlines())
            parts.append(f"        <p>{inline(para)}</p>")
    return "\n\n".join(parts)


def read_meta() -> dict:
    meta: dict[str, str] = {}
    for line in (CONTENT / "meta.txt").read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, val = line.partition(":")
        meta[key.strip()] = val.strip()
    return meta


TEMPLATE = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{title} \u2014 Veselin Stoyanov</title>
    <link rel="icon" type="image/x-icon" href="../favicon-32x32.png">

    <!-- Open Graph / Twitter cards for link previews -->
    <meta property="og:type" content="article">
    <meta property="og:title" content="{title}">
    <meta property="og:description" content="{og_desc}">
    <meta property="og:image" content="https://vesstoyanov.com/posts/results-card.png">
    <meta property="og:url" content="https://vesstoyanov.com/posts/typesafe-jev-vs-claude.html">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{title}">
    <meta name="twitter:description" content="{twitter_desc}">
    <meta name="twitter:image" content="https://vesstoyanov.com/posts/results-card.png">

    <style>
      *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
      :root {{ --accent: #2a7ab5; --accent-dark: #1a5a8a; --ink: #24292f; --muted: #6a737d; --rule: #333a42; --jev: #eaf3fb; }}
      html {{ -webkit-text-size-adjust: 100%; }}
      body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen,
          Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", Arial, sans-serif;
        font-size: 18px; line-height: 1.75; color: var(--ink); background: #fff;
        -webkit-font-smoothing: antialiased;
      }}
      a {{ color: var(--accent); text-decoration: none; }}
      a:hover {{ color: var(--accent-dark); text-decoration: underline; }}

      .wrap {{ max-width: 940px; margin: 0 auto; padding: 24px 28px 80px; }}

      .topbar {{ margin: 6px 0 30px; font-size: 15px; }}
      .topbar a {{ color: var(--accent); font-weight: 500; }}
      .topbar a:hover {{ text-decoration: none; }}

      header.post {{ border-bottom: 3px solid var(--accent); padding-bottom: 22px; margin-bottom: 34px; }}
      h1 {{ font-size: 40px; font-weight: 700; line-height: 1.15; letter-spacing: -0.02em;
        color: var(--ink); margin-bottom: 14px; }}
      .subtitle {{ font-size: 20px; color: var(--muted); font-weight: 400; line-height: 1.5; }}
      .byline {{ font-size: 15px; color: var(--muted); margin-top: 16px; }}

      article p {{ margin: 0 0 22px; }}
      article > p:first-of-type {{ font-size: 19px; }}

      h2 {{ font-size: 26px; font-weight: 650; color: var(--ink); letter-spacing: -0.01em;
        margin: 46px 0 16px; padding-left: 14px; border-left: 4px solid var(--accent); }}

      figure {{ margin: 30px 0; }}
      figure img {{ width: 100%; height: auto; border: 1px solid #e6e9ee; border-radius: 8px; }}
      figcaption {{ font-size: 14px; color: var(--muted); margin-top: 10px; text-align: center; }}

      pre.prompt {{
        background: #f6f8fa; border: 1px solid #e4e8ec; border-radius: 8px;
        padding: 18px 20px; overflow-x: auto; font-size: 14px; line-height: 1.55;
        font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
        color: #2b3138; margin: 8px 0 26px; white-space: pre;
      }}
      pre.prompt .lbl {{ color: var(--accent); font-weight: 600; }}

      /* Plain tables, PDF/booktabs style: horizontal rules only */
      .table-scroll {{ overflow-x: auto; margin: 24px 0 26px; }}
      table.results {{ width: 100%; border-collapse: collapse; font-size: 16px;
        border-top: 2px solid var(--rule); border-bottom: 2px solid var(--rule); }}
      table.results caption {{ caption-side: top; text-align: left; font-size: 15px;
        color: var(--muted); margin-bottom: 12px; }}
      table.results th, table.results td {{ padding: 8px 18px; text-align: right; }}
      table.results th:first-child, table.results td:first-child {{ text-align: left; }}
      table.results thead th {{ font-weight: 600; border-bottom: 1px solid var(--rule); }}
      /* Highlight the TypeSafe Jev row (MC tables) or column (sales table). */
      table.results tr.jev td, table.results tr.jev th,
      table.results td.jev, table.results thead th.jev {{ background: var(--jev); font-weight: 600; }}

      .cta {{ display: inline-block; margin-top: 8px; background: var(--accent); color: #fff;
        padding: 11px 20px; border-radius: 8px; font-weight: 600; font-size: 16px; }}
      .cta:hover {{ background: var(--accent-dark); color: #fff; text-decoration: none; }}

      footer.post {{ margin-top: 46px; padding-top: 22px; border-top: 1px solid #eceff2;
        font-size: 14px; color: var(--muted); }}

      @media (max-width: 640px) {{
        body {{ font-size: 17px; }}
        .wrap {{ padding: 16px 18px 56px; }}
        h1 {{ font-size: 30px; }}
        .subtitle {{ font-size: 18px; }}
        h2 {{ font-size: 22px; }}
      }}
    </style>
    <!-- Analytics: GoatCounter (cookieless). -->
    <script data-goatcounter="https://vesstoyanov.goatcounter.com/count"
            async src="//gc.zgo.at/count.js"></script>
  </head>
  <body>
    <div class="wrap">
      <div class="topbar"><a href="../index.html">\u2190 Veselin Stoyanov</a></div>

      <header class="post">
        <h1>{title}</h1>
        <p class="subtitle">{subtitle}</p>
        <p class="byline">{byline}</p>
      </header>

      <article>

{body}

        <footer class="post">{footer}</footer>

      </article>
    </div>
  </body>
</html>
"""


def main() -> None:
    meta = read_meta()
    section_files = sorted(CONTENT.glob("[0-9][0-9]-*.txt"))
    sections = []
    for f in section_files:
        sections.append(f"<!-- ===== {f.stem} ===== -->\n" + render_section(f.read_text()))
    body = "\n\n".join(sections)

    out = TEMPLATE.format(
        title=meta["title"],
        subtitle=inline(meta["subtitle"]),
        byline=inline(meta["byline"]),
        og_desc=meta["og_desc"],
        twitter_desc=meta["twitter_desc"],
        footer=inline(meta["footer"]),
        body=body,
    )
    OUT.write_text(out)
    print(f"Wrote {OUT.relative_to(HERE)} from {len(section_files)} sections.")


if __name__ == "__main__":
    main()
