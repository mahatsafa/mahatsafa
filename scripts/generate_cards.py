#!/usr/bin/env python3
"""
Generate kartu README versi light & dark ke folder profile/.

Kenapa perlu script ini:
GitHub me-proxy semua gambar lewat camo, jadi server kartu (vercel/demolab)
tidak tahu pembacanya lagi pakai light mode atau dark mode. Satu-satunya cara
yang benar-benar jalan adalah menyiapkan DUA file SVG, lalu README memilih
salah satunya lewat <picture> + prefers-color-scheme.

Pakai:
    python scripts/generate_cards.py

Butuh:
    pip install requests
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import requests

USER = "mahatsafa"
OUT_DIR = Path("profile")
TIMEOUT = 45
RETRIES = 3

# ---------------------------------------------------------------------------
# Daftar kartu.
# Tiap entri: nama file dasar -> (url_light, url_dark)
#
# Catatan warna:
#   light -> theme=default / warna GitHub light (bg putih, teks #24292f)
#   dark  -> theme=tokyonight (senada sama profil kamu sekarang)
# ---------------------------------------------------------------------------

STATS = "https://github-readme-stats.vercel.app/api"
STREAK = "https://streak-stats.demolab.com/"
GRAPH = "https://github-readme-activity-graph.vercel.app/graph"

CARDS: dict[str, tuple[str, str]] = {
    "github-stats": (
        f"{STATS}?username={USER}&show_icons=true&hide_border=true&theme=default",
        f"{STATS}?username={USER}&show_icons=true&hide_border=true&theme=tokyonight",
    ),
    "top-langs": (
        f"{STATS}/top-langs/?username={USER}&layout=compact&hide_border=true&theme=default",
        f"{STATS}/top-langs/?username={USER}&layout=compact&hide_border=true&theme=tokyonight",
    ),
    "streak": (
        f"{STREAK}?user={USER}&hide_border=true&theme=default",
        f"{STREAK}?user={USER}&hide_border=true&theme=tokyonight",
    ),
    "activity-graph": (
        # light: latar putih, garis biru GitHub -> terbaca di light mode
        f"{GRAPH}?username={USER}&hide_border=true"
        "&bg_color=ffffff&color=24292f&line=0969da&point=57606a&area=true&area_color=0969da",
        # dark: latar GitHub dark
        f"{GRAPH}?username={USER}&hide_border=true"
        "&bg_color=0d1117&color=c9d1d9&line=58a6ff&point=c9d1d9&area=true&area_color=1f6feb",
    ),
}


def fetch(url: str) -> str:
    """Ambil SVG, dengan retry karena endpoint gratisan kadang rate-limit."""
    last_error: Exception | None = None
    for attempt in range(1, RETRIES + 1):
        try:
            response = requests.get(
                url,
                timeout=TIMEOUT,
                headers={"User-Agent": f"{USER}-readme-cards"},
            )
            response.raise_for_status()
            text = response.text
            if "<svg" not in text:
                raise ValueError("respons bukan SVG")
            return text
        except Exception as error:  # noqa: BLE001
            last_error = error
            print(f"  percobaan {attempt}/{RETRIES} gagal: {error}")
            if attempt < RETRIES:
                time.sleep(5 * attempt)
    raise RuntimeError(f"gagal mengambil {url}") from last_error


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    failures: list[str] = []

    for name, (url_light, url_dark) in CARDS.items():
        for variant, url in (("light", url_light), ("dark", url_dark)):
            target = OUT_DIR / f"{name}-{variant}.svg"
            print(f"[{name}-{variant}] mengambil...")
            try:
                target.write_text(fetch(url), encoding="utf-8")
                print(f"  tersimpan -> {target}")
            except Exception as error:  # noqa: BLE001
                print(f"  DILEWATI: {error}")
                failures.append(target.name)

    if failures:
        print("\nKartu yang gagal:", ", ".join(failures))
        # Sengaja tetap exit 0 supaya workflow tidak merah cuma gara-gara
        # satu endpoint lagi down. File lama tetap dipakai README.
    else:
        print("\nSemua kartu berhasil dibuat.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
