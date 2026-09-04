#!/usr/bin/env python3
"""
Generates two SVG cards from WakaTime stats, both in the same dark theme:

  profile/wakatime-top-3.svg  -> Languages / Editors / OS / Categories,
                                  top 3 items each
  profile/wakatime-all.svg    -> same 4 columns, top N items each
                                  (default 6) - the "full" card

Env vars:
  WAKATIME_API_KEY   (required)
  WAKA_RANGE         (optional) last_7_days | last_30_days | last_6_months
                       | last_year | all_time   (default: all_time)
  WAKA_ALL_TOP_N     (optional) items per column on the "all" card
                       (default: 6)
  WAKA_OUT_DIR       (optional) output directory (default: profile)
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

API_URL = f"https://wakatime.com/api/v1/users/current/stats/{RANGE}"

# ---- Theme --------------------------------------------------------------
BG = "#0d1117"
BORDER = "#30363d"
TITLE_COLOR = "#58a6ff"
TEXT_COLOR = "#c9d1d9"
MUTED_COLOR = "#8b949e"
BAR_BG = "#21262d"
BAR_FILL = "#58a6ff"
FONT = "Segoe UI, Ubuntu, sans-serif"

COLUMNS = [
    ("languages", "LANGUAGES"),
    ("editors", "EDITORS"),
    ("operating_systems", "OS"),
    ("categories", "CATEGORIES"),
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


def render_column(x, width, title, items):
    parts = [
        f'<text x="{x + 14}" y="28" font-family="{FONT}" font-size="13" '
        f'font-weight="700" fill="{TITLE_COLOR}">{esc(title)}</text>'
    ]
    row_h = 34
    bar_w = width - 28
    y = 48

    if not items:
        parts.append(
            f'<text x="{x + 14}" y="{y}" font-family="{FONT}" font-size="11" '
            f'fill="{MUTED_COLOR}">No data</text>'
        )
        return "\n".join(parts), y + row_h

    for item in items:
        name = item.get("name", "Unknown")
        percent = float(item.get("percent", 0))
        text = item.get("text", "")
        bar_y = y + 6
        filled_w = max(2, bar_w * percent / 100)

        parts.append(
            f'<text x="{x + 14}" y="{y}" font-family="{FONT}" font-size="11" '
            f'fill="{TEXT_COLOR}">{esc(name)}</text>'
        )
        parts.append(
            f'<text x="{x + width - 14}" y="{y}" text-anchor="end" '
            f'font-family="{FONT}" font-size="11" fill="{MUTED_COLOR}">{percent:.2f}%</text>'
        )
        parts.append(
            f'<rect x="{x + 14}" y="{bar_y}" width="{bar_w}" height="6" rx="3" fill="{BAR_BG}"/>'
        )
        parts.append(
            f'<rect x="{x + 14}" y="{bar_y}" width="{filled_w:.1f}" height="6" rx="3" fill="{BAR_FILL}"/>'
        )
        parts.append(
            f'<text x="{x + 14}" y="{bar_y + 18}" font-family="{FONT}" font-size="9" '
            f'fill="{MUTED_COLOR}">{esc(text)}</text>'
        )
        y += row_h + 10

    return "\n".join(parts), y


def build_card(data, top_n, footer_text=None):
    col_width = 230
    gap = 14
    padding = 14
    n_cols = len(COLUMNS)
    width = padding * 2 + col_width * n_cols + gap * (n_cols - 1)

    col_svgs = []
    max_bottom = 0
    for i, (key, title) in enumerate(COLUMNS):
        x = padding + i * (col_width + gap)
        items = top_items(data, key, top_n)
        svg, bottom = render_column(x, col_width, title, items)
        col_svgs.append(svg)
        max_bottom = max(max_bottom, bottom)

    footer_h = 22 if footer_text else 0
    height = max_bottom + 16 + footer_h

    boxes = []
    for i in range(n_cols):
        x = padding + i * (col_width + gap)
        boxes.append(
            f'<rect x="{x}" y="8" width="{col_width}" height="{height - 16 - footer_h}" '
            f'rx="8" fill="none" stroke="{BORDER}" stroke-width="1"/>'
        )

    footer_svg = ""
    if footer_text:
        footer_svg = (
            f'<text x="{width / 2}" y="{height - 8}" text-anchor="middle" '
            f'font-family="{FONT}" font-size="9" fill="{MUTED_COLOR}">{esc(footer_text)}</text>'
        )

    return f'''<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
  <rect x="0" y="0" width="{width}" height="{height}" rx="10" fill="{BG}"/>
  {"".join(boxes)}
  {"".join(col_svgs)}
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
