#!/usr/bin/env python3
"""Genera el radar de lenguajes a partir de los repos publicos de GitHub."""

from __future__ import annotations

import json
import math
import urllib.request
from pathlib import Path
from urllib.error import HTTPError, URLError


USER = "bvnyamin"
PROFILE_REPO = USER.lower()
ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets"
IGNORED_LANGUAGES = {"html", "css", "dockerfile", "makefile", "shell"}
THEMES = {
    "dark": {
        "background": "#171827",
        "grid": "#3d405a",
        "label": "#e9e7f2",
        "muted": "#a4a8c2",
        "accent": "#63dfd0",
        "secondary": "#fa83b8",
    },
    "light": {
        "background": "#fffaf7",
        "grid": "#d8d5e5",
        "label": "#29283d",
        "muted": "#646981",
        "accent": "#188f8a",
        "secondary": "#c33d83",
    },
}


def github_json(url: str) -> dict | list:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "bvnyamin-profile-radar"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def collect_language_bytes() -> list[tuple[str, int]]:
    totals: dict[str, int] = {}
    page = 1
    while True:
        url = f"https://api.github.com/users/{USER}/repos?type=owner&per_page=100&page={page}"
        repos = github_json(url)
        if not repos:
            break
        for repo in repos:
            if repo["name"].lower() == PROFILE_REPO or repo.get("fork") or repo.get("archived"):
                continue
            for language, byte_count in github_json(repo["languages_url"]).items():
                if language.lower() not in IGNORED_LANGUAGES:
                    totals[language] = totals.get(language, 0) + byte_count
        if len(repos) < 100:
            break
        page += 1
    return sorted(totals.items(), key=lambda item: item[1], reverse=True)[:7]


def esc(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def point(angle: float, radius: float, cx: float, cy: float) -> tuple[float, float]:
    return cx + math.cos(angle) * radius, cy + math.sin(angle) * radius


def render(languages: list[tuple[str, int]], theme: dict[str, str], mode: str) -> str:
    width, height = 680, 390
    cx, cy, radius = 340, 211, 116
    peak = max(count for _, count in languages)
    angles = [-math.pi / 2 + i * 2 * math.pi / len(languages) for i in range(len(languages))]
    radii = [radius * math.sqrt(count / peak) for _, count in languages]
    vertices = [point(angle, distance, cx, cy) for angle, distance in zip(angles, radii)]
    polygon = " ".join(f"{x:.1f},{y:.1f}" for x, y in vertices)
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" aria-labelledby="title desc">',
        '<title id="title">Lenguajes en repositorios publicos de bvnyamin</title>',
        '<desc id="desc">Grafico radial de la distribucion relativa de bytes por lenguaje, con escala de raiz cuadrada para hacer visibles los lenguajes menos usados. No expresa nivel de dominio.</desc>',
        f'<rect width="{width}" height="{height}" rx="20" fill="{theme["background"]}"/>',
        f'<text x="340" y="35" text-anchor="middle" fill="{theme["label"]}" font-family="ui-monospace,Consolas,monospace" font-size="16" font-weight="700">LENGUAJES · REPOS PUBLICOS</text>',
    ]
    for ring in (0.25, 0.5, 0.75, 1.0):
        points = " ".join(
            f"{point(angle, radius * ring, cx, cy)[0]:.1f},{point(angle, radius * ring, cx, cy)[1]:.1f}"
            for angle in angles
        )
        svg.append(f'<polygon points="{points}" fill="none" stroke="{theme["grid"]}" stroke-width="1"/>')
    for angle in angles:
        x, y = point(angle, radius, cx, cy)
        svg.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="{theme["grid"]}" stroke-width="1"/>')
    svg.append(f'<polygon points="{polygon}" fill="{theme["accent"]}" fill-opacity=".18" stroke="{theme["accent"]}" stroke-width="3" stroke-linejoin="round"/>')
    for (language, _), (x, y), angle in zip(languages, vertices, angles):
        svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{theme["secondary"]}" stroke="{theme["background"]}" stroke-width="2"/>')
        lx, ly = point(angle, radius + 33, cx, cy)
        anchor = "middle" if abs(math.cos(angle)) < 0.25 else ("start" if math.cos(angle) > 0 else "end")
        svg.append(f'<text x="{lx:.1f}" y="{ly + 5:.1f}" text-anchor="{anchor}" fill="{theme["label"]}" font-family="ui-monospace,Consolas,monospace" font-size="14">{esc(language)}</text>')
    svg.append(f'<text x="340" y="372" text-anchor="middle" fill="{theme["muted"]}" font-family="Segoe UI,Arial,sans-serif" font-size="12">bytes de codigo · escala relativa comprimida · generado desde GitHub</text>')
    svg.append("</svg>")
    return "\n".join(svg)


def main() -> None:
    try:
        languages = collect_language_bytes()
    except (HTTPError, URLError, TimeoutError) as error:
        raise SystemExit(f"No se pudieron consultar los lenguajes publicos de GitHub: {error}")
    if len(languages) < 3:
        raise SystemExit("Se necesitan al menos tres lenguajes con codigo publico para generar el radar.")
    OUTPUT.mkdir(exist_ok=True)
    for name, theme in THEMES.items():
        path = OUTPUT / f"language-radar-{name}.svg"
        path.write_text(render(languages, theme, name), encoding="utf-8")
        print(f"Actualizado: {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
