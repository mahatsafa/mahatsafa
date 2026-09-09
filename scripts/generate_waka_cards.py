#!/usr/bin/env python3
"""
Generates two SVG cards from WakaTime stats, both narrow single-column
layout (Languages / Editors / OS / Categories stacked vertically) sized
to sit side-by-side with the GitHub Stats column in a 2-col README table.

  profile/wakatime-top-3.svg  -> top 3 items each section
  profile/wakatime-all.svg    -> top N items each section (default 6)

Env vars:
  WAKATIME_API_KEY   (required)
  WAKA_RANGE         (optional) last_7_days | last_30_days | last_6_months
                       | last_year | all_time   (default: all_time)
  WAKA_ALL_TOP_N     (optional) items per section on the "all" card
                       (default: 6)
  WAKA_OUT_DIR       (optional) output directory (default: profile)
  WAKA_CARD_WIDTH    (optional) card width in px (default: 440)
"""

import base64
import json
import os
import sys
import urllib.request
import urllib.error

API_KEY = os.environ.get("WAKATIME_API_KEY")
RANGE = os.environ.get("WAKA_RANGE", "all_time")
ALL_TOP_N = int(os.environ.get("WAKA_ALL_TOP_N", "6"))
OUT_DIR = os.environ.get("WAKA_OUT_DIR", "profile")
CARD_WIDTH = int(os.environ.get("WAKA_CARD_WIDTH", "440"))

API_URL = f"https://wakatime.com/api/v1/users/current/stats/{RANGE}"

# ---- Theme (unchanged from before) --------------------------------------
BG = "#0d1117"
BORDER = "#30363d"
TITLE_COLOR = "#58a6ff"
TEXT_COLOR = "#c9d1d9"
MUTED_COLOR = "#8b949e"
BAR_BG = "#21262d"
BAR_FILL = "#58a6ff"
FONT = "Segoe UI, Ubuntu, sans-serif"

SECTIONS = [
    ("languages", "💻 LANGUAGES"),
    ("editors", "🖥️ EDITORS"),
    ("operating_systems", "⚙️ OS"),
    ("categories", "📊 CATEGORIES"),
]


def fetch_stats():
    if not API_KEY:
        sys.exit("ERROR: WAKATIME_API_KEY env var is not set.")
    token = base64.b64encode(API_KEY.encode()).decode()
    req = urllib.request.Request(API_URL, headers={"Authorization": f"Basic {token}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        sys.exit(f"ERROR: WakaTime API returned {e.code}: {e.read().decode()}")
    except urllib.error.URLError as e:
        sys.exit(f"ERROR: could not reach WakaTime API: {e.reason}")

    data = payload.get("data")
    if not data:
        sys.exit(f"ERROR: unexpected API response: {payload}")
    return data


def top_items(data, key, n):
    items = data.get(key) or []
    items = sorted(items, key=lambda i: i.get("percent", 0), reverse=True)
    return items[:n]


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_section(y_top, width, title, items):
    """One boxed section, stacked vertically. Returns (svg_snippet, new_y)."""
    pad = 14
    row_h = 34
    bar_w = width - pad * 2

    parts = [
        f'<text x="{pad + 6}" y="{y_top + 24}" font-family="{FONT}" font-size="13" '
        f'font-weight="700" fill="{TITLE_COLOR}">{esc(title)}</text>'
    ]

    y = y_top + 44
    if not items:
        parts.append(
            f'<text x="{pad + 6}" y="{y}" font-family="{FONT}" font-size="11" '
            f'fill="{MUTED_COLOR}">No data</text>'
        )
        y += row_h
    else:
        for item in items:
            name = item.get("name", "Unknown")
            percent = float(item.get("percent", 0))
            text = item.get("text", "")
            bar_y = y + 6
            filled_w = max(2, bar_w * percent / 100)

            parts.append(
                f'<text x="{pad + 6}" y="{y}" font-family="{FONT}" font-size="11" '
                f'fill="{TEXT_COLOR}">{esc(name)}</text>'
            )
            parts.append(
                f'<text x="{width - pad - 6}" y="{y}" text-anchor="end" '
                f'font-family="{FONT}" font-size="11" fill="{MUTED_COLOR}">{percent:.2f}%</text>'
            )
            parts.append(
                f'<rect x="{pad + 6}" y="{bar_y}" width="{bar_w - 12}" height="6" rx="3" fill="{BAR_BG}"/>'
            )
            parts.append(
                f'<rect x="{pad + 6}" y="{bar_y}" width="{max(2, filled_w - 12):.1f}" height="6" '
                f'rx="3" fill="{BAR_FILL}"/>'
            )
            parts.append(
                f'<text x="{pad + 6}" y="{bar_y + 18}" font-family="{FONT}" font-size="9" '
                f'fill="{MUTED_COLOR}">{esc(text)}</text>'
            )
            y += row_h + 10

    box_bottom = y + 6
    box = (
        f'<rect x="0" y="{y_top}" width="{width}" height="{box_bottom - y_top}" '
        f'rx="8" fill="none" stroke="{BORDER}" stroke-width="1"/>'
    )
    return box + "\n" + "\n".join(parts), box_bottom


def build_card(data, top_n, footer_text=None):
    width = CARD_WIDTH
    gap = 14
    outer_pad = 10

    y = outer_pad
    section_svgs = []
    for key, title in SECTIONS:
        items = top_items(data, key, top_n)
        svg, y = render_section(y, width - outer_pad * 2, title, items)
        # shift each section's local x=0 origin to sit inside outer padding
        section_svgs.append(f'<g transform="translate({outer_pad},0)">{svg}</g>')
        y += gap

    footer_h = 24 if footer_text else 0
    height = y - gap + outer_pad + footer_h

    footer_svg = ""
    if footer_text:
        footer_svg = (
            f'<text x="{width / 2}" y="{height - 8}" text-anchor="middle" '
            f'font-family="{FONT}" font-size="9" fill="{MUTED_COLOR}">{esc(footer_text)}</text>'
        )

    return f'''<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
  <rect x="0" y="0" width="{width}" height="{height}" rx="10" fill="{BG}"/>
  {"".join(section_svgs)}
  {footer_svg}
</svg>'''


def main():
    data = fetch_stats()
    os.makedirs(OUT_DIR, exist_ok=True)

    range_field = data.get("range", RANGE)
    range_label = range_field.get("text", RANGE) if isinstance(range_field, dict) else (range_field or RANGE)

    top3_svg = build_card(data, top_n=3, footer_text=f"Top 3 · {range_label}")
    with open(os.path.join(OUT_DIR, "wakatime-top-3.svg"), "w", encoding="utf-8") as f:
        f.write(top3_svg)
    print("Wrote", os.path.join(OUT_DIR, "wakatime-top-3.svg"))

    all_svg = build_card(data, top_n=ALL_TOP_N, footer_text=f"Full breakdown · {range_label}")
    with open(os.path.join(OUT_DIR, "wakatime-all.svg"), "w", encoding="utf-8") as f:
        f.write(all_svg)
    print("Wrote", os.path.join(OUT_DIR, "wakatime-all.svg"))


if __name__ == "__main__":
    main()
