#!/usr/bin/env python3
"""
Generate kartu "Coding activity" dari statistik WakaTime, versi dark & light.

Desainnya meniru section "Aktivitas" di https://gustomahatsafa.vercel.app/activity:
kolom kiri berisi LANGUAGES (bar tebal), kolom kanan berisi EDITOR,
OPERATING SYSTEM, dan CATEGORY (bar tipis), dengan palet netral hitam/putih/abu.

Output:
    profile/wakatime-dark.svg
    profile/wakatime-light.svg

Kenapa dua file:
GitHub me-proxy gambar lewat camo, jadi SVG tidak tahu pembaca sedang pakai
light atau dark mode. README memilih salah satu file lewat <picture> +
prefers-color-scheme.

Env var:
    WAKATIME_API_KEY  (wajib)
    WAKA_RANGE        last_7_days | last_30_days | last_6_months | last_year
                      | all_time   (default: all_time)
    WAKA_LANG_TOP_N   jumlah bahasa di kolom kiri (default: 6)
    WAKA_SIDE_TOP_N   jumlah item per section di kolom kanan (default: 3)
    WAKA_OUT_DIR      folder output (default: profile)

Hanya memakai standard library Python, jadi tidak perlu `pip install`.
"""

from __future__ import annotations

import base64
import json
import os
import sys
import urllib.error
import urllib.request

API_KEY = os.environ.get("WAKATIME_API_KEY")
RANGE = os.environ.get("WAKA_RANGE", "all_time")
LANG_TOP_N = int(os.environ.get("WAKA_LANG_TOP_N", "6"))
SIDE_TOP_N = int(os.environ.get("WAKA_SIDE_TOP_N", "3"))
OUT_DIR = os.environ.get("WAKA_OUT_DIR", "profile")

API_URL = f"https://wakatime.com/api/v1/users/current/stats/{RANGE}"

# ---- Tema ---------------------------------------------------------------------
# Palet netral seperti portfolio. "fill" = warna bar, "track" = latar bar.
THEMES: dict[str, dict[str, str]] = {
    "dark": {
        "bg": "#0a0a0a",
        "border": "#262626",
        "text": "#fafafa",
        "muted": "#a3a3a3",
        "faint": "#737373",
        "track": "#262626",
        "fill": "#fafafa",
        "fill_soft": "#d4d4d4",
    },
    "light": {
        "bg": "#ffffff",
        "border": "#e5e5e5",
        "text": "#0a0a0a",
        "muted": "#737373",
        "faint": "#a3a3a3",
        "track": "#f0f0f0",
        "fill": "#0a0a0a",
        "fill_soft": "#404040",
    },
}

# GitHub menampilkan SVG lewat <img>, jadi web font (Google Fonts, dll.) tidak
# bisa dimuat. Karena itu pakai font bawaan sistem dengan beberapa cadangan.
SANS = 'ui-sans-serif, -apple-system, "Segoe UI", Helvetica, Arial, sans-serif'
MONO = 'ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace'

SIDE_SECTIONS = [
    ("editors", "EDITOR"),
    ("operating_systems", "OPERATING SYSTEM"),
    ("categories", "CATEGORY"),
]

# ---- Ukuran layout (px, dalam koordinat viewBox) ------------------------------
WIDTH = 840
PAD = 32
LEFT_X = PAD
LEFT_W = 456
DIVIDER_X = 520
RIGHT_X = 552
RIGHT_W = WIDTH - PAD - RIGHT_X  # 256
BODY_Y = 132  # baseline judul section pertama

LANG_FIRST_OFFSET = 30  # jarak judul LANGUAGES ke baseline nama bahasa pertama
LANG_ROW_CONTENT = 18  # dari baseline nama sampai bawah bar tebal
LANG_PITCH_MIN = 40  # jarak minimum antar baris bahasa
LANG_PITCH_MAX = 64  # batas maksimum supaya baris tidak terlalu renggang

SIDE_FIRST_OFFSET = 28
SIDE_PITCH = 30
SIDE_ROW_CONTENT = 11  # dari baseline nama sampai bawah bar tipis
SIDE_GAP_MIN = 30  # jarak minimum antar section di kolom kanan

NAME_MAX_LEFT = 22  # ~22 huruf tebal masih muat sebelum teks durasi
NAME_MAX_RIGHT = 22


# ---- Data ---------------------------------------------------------------------
def fetch_stats() -> dict:
    """Ambil statistik WakaTime untuk RANGE. Keluar dengan pesan jelas kalau gagal."""
    if not API_KEY:
        sys.exit("ERROR: env var WAKATIME_API_KEY belum diset.")
    # WakaTime memakai HTTP Basic Auth dengan API key sebagai username (base64).
    token = base64.b64encode(API_KEY.encode()).decode()
    request = urllib.request.Request(API_URL, headers={"Authorization": f"Basic {token}"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode())
    except urllib.error.HTTPError as error:
        sys.exit(f"ERROR: WakaTime API membalas {error.code}: {error.read().decode()}")
    except urllib.error.URLError as error:
        sys.exit(f"ERROR: tidak bisa menghubungi WakaTime API: {error.reason}")

    data = payload.get("data")
    if not data:
        sys.exit(f"ERROR: respons API tidak terduga: {payload}")
    return data


def top_items(data: dict, key: str, n: int) -> list[dict]:
    """Ambil n item teratas, buang yang durasinya 0 (contoh: 'AI Coding 0 secs')."""
    items = [item for item in data.get(key) or [] if float(item.get("total_seconds", 0)) > 0]
    items.sort(key=lambda item: float(item.get("percent", 0)), reverse=True)
    return items[:n]


def total_text(data: dict) -> str:
    """Teks total waktu, misalnya '12 hrs 44 mins'."""
    return (
        data.get("human_readable_total_including_other_language")
        or data.get("human_readable_total")
        or "0 secs"
    )


def range_text(range_key: str) -> str:
    """Ubah 'all_time' / 'last_7_days' menjadi 'all time' / 'last 7 days'."""
    return range_key.replace("_", " ")


# ---- Helper teks --------------------------------------------------------------
def esc(value: object) -> str:
    """Escape karakter khusus XML. Nama dari API bisa saja berisi '&', '<', '>'
    atau tanda kutip; tanpa escape, SVG jadi rusak dan tidak tampil sama sekali."""
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def truncate(name: str, limit: int) -> str:
    """Potong nama yang terlalu panjang supaya tidak menabrak teks di kanannya."""
    return name if len(name) <= limit else name[: limit - 1].rstrip() + "…"


def fmt_percent(value: float) -> str:
    return f"{value:.1f}%"


# ---- Layout -------------------------------------------------------------------
def side_section_height(count: int) -> int:
    """Tinggi satu section kanan, dari baseline judul sampai bawah bar terakhir."""
    rows = max(count, 1)  # section kosong tetap memakai satu baris "No data"
    return SIDE_FIRST_OFFSET + (rows - 1) * SIDE_PITCH + SIDE_ROW_CONTENT


def compute_layout(lang_count: int, side_counts: list[int]) -> dict:
    """Hitung jarak baris supaya kolom kiri dan kanan berakhir sejajar.

    Kolom kanan punya tinggi alami (3 section). Jarak antar baris bahasa
    direnggangkan agar kolom kiri setinggi itu, tapi dibatasi LANG_PITCH_MAX
    supaya tidak terlihat kosong. Kalau justru kolom kiri yang lebih tinggi,
    jarak antar section kanan yang direnggangkan.
    """
    rows = max(lang_count, 1)
    section_heights = [side_section_height(count) for count in side_counts]
    right_h = sum(section_heights) + SIDE_GAP_MIN * (len(section_heights) - 1)

    if rows > 1:
        wanted = (right_h - LANG_FIRST_OFFSET - LANG_ROW_CONTENT) / (rows - 1)
        pitch = min(max(wanted, LANG_PITCH_MIN), LANG_PITCH_MAX)
    else:
        pitch = LANG_PITCH_MIN
    left_h = LANG_FIRST_OFFSET + (rows - 1) * pitch + LANG_ROW_CONTENT

    side_gap = float(SIDE_GAP_MIN)
    if left_h > right_h and len(section_heights) > 1:
        side_gap += (left_h - right_h) / (len(section_heights) - 1)
        right_h = left_h

    return {
        "lang_pitch": pitch,
        "side_gap": side_gap,
        "body_h": max(left_h, right_h),
    }


# ---- Render -------------------------------------------------------------------
def render_style(theme: dict[str, str]) -> str:
    """CSS di dalam SVG: warna, font, dan animasi bar 'tumbuh' dari kiri."""
    return f"""<style>
    .sans {{ font-family: {SANS}; }}
    .mono {{ font-family: {MONO}; }}
    .title {{ font-size: 18px; font-weight: 700; fill: {theme["text"]}; }}
    .subtitle {{ font-size: 12px; fill: {theme["muted"]}; }}
    .label {{ font-size: 11px; font-weight: 600; letter-spacing: 1.8px; fill: {theme["faint"]}; }}
    .rank {{ font-size: 12px; fill: {theme["faint"]}; }}
    .lang {{ font-size: 14px; font-weight: 700; fill: {theme["text"]}; }}
    .item {{ font-size: 13px; font-weight: 600; fill: {theme["text"]}; }}
    .dur {{ font-size: 12px; fill: {theme["muted"]}; }}
    .pct {{ font-size: 13px; font-weight: 700; fill: {theme["text"]}; }}
    .pct-sm {{ font-size: 12px; font-weight: 600; fill: {theme["muted"]}; }}
    .empty {{ font-size: 12px; fill: {theme["faint"]}; }}
    /* transform-box: fill-box membuat titik awal skala = sisi kiri bar itu
       sendiri, bukan sisi kiri seluruh SVG. */
    .bar {{
      transform-box: fill-box;
      transform-origin: left center;
      animation: grow 900ms cubic-bezier(.2, .7, .2, 1) both;
    }}
    @keyframes grow {{ from {{ transform: scaleX(0); }} to {{ transform: scaleX(1); }} }}
    /* Hormati pengaturan "kurangi animasi" di sistem operasi pembaca. */
    @media (prefers-reduced-motion: reduce) {{ .bar {{ animation: none; }} }}
  </style>"""


def render_bar(x: float, y: float, width: float, height: float, percent: float,
               fill: str, track: str, delay_ms: int) -> str:
    """Satu bar: track penuh + isi sesuai persen (minimal 2px supaya tetap terlihat)."""
    filled = max(2.0, width * min(percent, 100) / 100)
    radius = height / 2
    return (
        f'<rect x="{x}" y="{y:.1f}" width="{width}" height="{height}" rx="{radius}" fill="{track}"/>'
        f'<rect class="bar" style="animation-delay:{delay_ms}ms" x="{x}" y="{y:.1f}" '
        f'width="{filled:.1f}" height="{height}" rx="{radius}" fill="{fill}"/>'
    )


def render_header(theme: dict[str, str], subtitle: str) -> str:
    """Ikon jam, judul, subjudul monospace, dan lencana panah ↗ di kanan atas."""
    icon_cx, icon_cy = PAD + 9, 42
    badge_cx, badge_cy = WIDTH - PAD - 16, 48
    return f"""
  <g fill="none" stroke="{theme["text"]}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="{icon_cx}" cy="{icon_cy}" r="9"/>
    <path d="M{icon_cx} {icon_cy - 5} V{icon_cy} L{icon_cx + 3.5} {icon_cy + 2.5}"/>
  </g>
  <text class="sans title" x="{PAD + 28}" y="{icon_cy + 6}">Coding activity</text>
  <text class="mono subtitle" x="{PAD}" y="{icon_cy + 32}">{esc(subtitle)}</text>
  <circle cx="{badge_cx}" cy="{badge_cy}" r="16" fill="none" stroke="{theme["border"]}" stroke-width="1"/>
  <path d="M{badge_cx - 4} {badge_cy + 4} L{badge_cx + 4} {badge_cy - 4} M{badge_cx - 2.5} {badge_cy - 4} H{badge_cx + 4} V{badge_cy + 2.5}"
        fill="none" stroke="{theme["text"]}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
  <line x1="{PAD}" y1="96" x2="{WIDTH - PAD}" y2="96" stroke="{theme["border"]}" stroke-width="1"/>"""


def render_languages(theme: dict[str, str], items: list[dict], pitch: float) -> str:
    """Kolom kiri: daftar bahasa bernomor dengan bar tebal."""
    parts = [f'<text class="sans label" x="{LEFT_X}" y="{BODY_Y}">LANGUAGES</text>']
    name_x = LEFT_X + 24
    right_edge = LEFT_X + LEFT_W
    bar_w = right_edge - name_x

    if not items:
        parts.append(
            f'<text class="sans empty" x="{LEFT_X}" y="{BODY_Y + LANG_FIRST_OFFSET}">No data</text>'
        )
        return "\n  ".join(parts)

    for index, item in enumerate(items):
        y = BODY_Y + LANG_FIRST_OFFSET + index * pitch
        percent = float(item.get("percent", 0))
        parts.append(f'<text class="mono rank" x="{LEFT_X}" y="{y:.1f}">{index + 1}</text>')
        parts.append(
            f'<text class="sans lang" x="{name_x}" y="{y:.1f}">'
            f'{esc(truncate(item.get("name", "Unknown"), NAME_MAX_LEFT))}</text>'
        )
        # Persen ditaruh paling kanan; durasi di kirinya dengan jarak tetap,
        # karena lebar teks persen hampir selalu sama ("45.1%").
        parts.append(
            f'<text class="sans pct" x="{right_edge}" y="{y:.1f}" text-anchor="end">'
            f'{fmt_percent(percent)}</text>'
        )
        parts.append(
            f'<text class="mono dur" x="{right_edge - 58}" y="{y:.1f}" text-anchor="end">'
            f'{esc(item.get("text", ""))}</text>'
        )
        parts.append(render_bar(name_x, y + 12, bar_w, 6, percent,
                                theme["fill"], theme["track"], 80 * index))
    return "\n  ".join(parts)


def render_side_section(theme: dict[str, str], top_y: float, title: str,
                        items: list[dict], delay_base: int) -> str:
    """Satu section di kolom kanan (EDITOR / OPERATING SYSTEM / CATEGORY)."""
    parts = [f'<text class="sans label" x="{RIGHT_X}" y="{top_y:.1f}">{esc(title)}</text>']
    right_edge = RIGHT_X + RIGHT_W

    if not items:
        parts.append(
            f'<text class="sans empty" x="{RIGHT_X}" y="{top_y + SIDE_FIRST_OFFSET:.1f}">No data</text>'
        )
        return "\n  ".join(parts)

    for index, item in enumerate(items):
        y = top_y + SIDE_FIRST_OFFSET + index * SIDE_PITCH
        percent = float(item.get("percent", 0))
        parts.append(
            f'<text class="sans item" x="{RIGHT_X}" y="{y:.1f}">'
            f'{esc(truncate(item.get("name", "Unknown"), NAME_MAX_RIGHT))}</text>'
        )
        parts.append(
            f'<text class="mono pct-sm" x="{right_edge}" y="{y:.1f}" text-anchor="end">'
            f'{fmt_percent(percent)}</text>'
        )
        parts.append(render_bar(RIGHT_X, y + 8, RIGHT_W, 3, percent,
                                theme["fill_soft"], theme["track"], delay_base + 80 * index))
    return "\n  ".join(parts)


def build_card(data: dict, theme_name: str, range_key: str = RANGE,
               lang_top_n: int = LANG_TOP_N, side_top_n: int = SIDE_TOP_N) -> str:
    """Rakit satu SVG lengkap untuk tema 'dark' atau 'light'."""
    theme = THEMES[theme_name]
    languages = top_items(data, "languages", lang_top_n)
    sides = [(title, top_items(data, key, side_top_n)) for key, title in SIDE_SECTIONS]
    layout = compute_layout(len(languages), [len(items) for _, items in sides])

    height = round(BODY_Y + layout["body_h"] + PAD)
    subtitle = f"WakaTime · {range_text(range_key)} · {total_text(data)} total"

    side_parts = []
    top_y = float(BODY_Y)
    for section_index, (title, items) in enumerate(sides):
        side_parts.append(render_side_section(theme, top_y, title, items, 200 + 240 * section_index))
        top_y += side_section_height(len(items)) + layout["side_gap"]

    divider_bottom = BODY_Y + layout["body_h"]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}" role="img" aria-labelledby="title">
  <title id="title">Coding activity: {esc(subtitle)}</title>
  {render_style(theme)}
  <rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{height - 1}" rx="12" fill="{theme["bg"]}" stroke="{theme["border"]}"/>
  {render_header(theme, subtitle)}
  <line x1="{DIVIDER_X}" y1="{BODY_Y - 14}" x2="{DIVIDER_X}" y2="{divider_bottom:.1f}" stroke="{theme["border"]}" stroke-width="1"/>
  {render_languages(theme, languages, layout["lang_pitch"])}
  {"".join(side_parts)}
</svg>
"""


def main() -> None:
    data = fetch_stats()
    os.makedirs(OUT_DIR, exist_ok=True)
    for theme_name in THEMES:
        path = os.path.join(OUT_DIR, f"wakatime-{theme_name}.svg")
        with open(path, "w", encoding="utf-8") as file:
            file.write(build_card(data, theme_name))
        print("Tersimpan:", path)


if __name__ == "__main__":
    main()
