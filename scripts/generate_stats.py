#!/usr/bin/env python3
"""Generate hand-styled SVG cards for GitHub & LeetCode stats.

Reads from GitHub's REST API and LeetCode's public GraphQL endpoint,
writes assets/stats.svg, assets/top-langs.svg, assets/leetcode.svg.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

GH_USER = os.environ.get("GH_USER", "bobo100")
LC_USER = os.environ.get("LC_USER", "lione1234")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
ASSETS = Path(__file__).resolve().parent.parent / "assets"

ACCENT_PINK = "#F72585"
ACCENT_PURPLE = "#7209B7"
ACCENT_BLUE = "#3A0CA3"
ACCENT_INDIGO = "#4361EE"
ACCENT_CYAN = "#4CC9F0"
ACCENT_YELLOW = "#FFD60A"
ACCENT_CORAL = "#FB5607"
ACCENT_GREEN = "#06FFA5"
BG_DARK = "#0F0E1A"
BG_DARK_TOP = "#15101F"
INNER_BG = "#1C1530"
BORDER_DIM = "#2A1F3D"
TXT_LIGHT = "#FFFFFE"
TXT_MUTED = "#B8C1D1"
TXT_DIM = "#94A1B2"

FONT = "'SF Mono', ui-monospace, Menlo, Consolas, monospace"

LANG_COLORS = {
    "JavaScript": "#F7DF1E",
    "TypeScript": "#3178C6",
    "HTML": "#E34F26",
    "CSS": "#1572B6",
    "Python": "#3776AB",
    "Java": "#ED8B00",
    "C#": "#239120",
    "C++": "#00599C",
    "Go": "#00ADD8",
    "Vue": "#41B883",
    "SCSS": "#CC6699",
    "Shell": "#89E051",
    "PHP": "#777BB4",
    "Ruby": "#CC342D",
    "Kotlin": "#7F52FF",
    "Swift": "#FA7343",
    "Dart": "#0175C2",
    "Rust": "#DEA584",
}


def gh_get(path: str):
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "bobo100-stats-generator",
            **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}),
        },
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def fetch_user():
    return gh_get(f"/users/{GH_USER}")


def fetch_repos():
    out, page = [], 1
    while True:
        chunk = gh_get(f"/users/{GH_USER}/repos?per_page=100&page={page}&type=owner")
        out.extend(chunk)
        if len(chunk) < 100:
            break
        page += 1
    return out


def fetch_languages(repos):
    totals: dict[str, int] = {}
    for r in repos:
        if r.get("fork"):
            continue
        try:
            data = gh_get(f"/repos/{r['full_name']}/languages")
        except Exception:
            continue
        for lang, bytes_ in data.items():
            totals[lang] = totals.get(lang, 0) + bytes_
    return totals


def fetch_leetcode():
    query = """
    query userStats($username: String!) {
      matchedUser(username: $username) {
        username
        profile { ranking realName }
        submitStats {
          acSubmissionNum { difficulty count submissions }
          totalSubmissionNum { difficulty count submissions }
        }
      }
      allQuestionsCount { difficulty count }
    }
    """
    body = json.dumps({"query": query, "variables": {"username": LC_USER}}).encode()
    req = urllib.request.Request(
        "https://leetcode.com/graphql/",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Origin": "https://leetcode.com",
            "Referer": f"https://leetcode.com/u/{LC_USER}/",
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
        },
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


# ---------- SVG building blocks ----------

def card_frame(width: int, height: int, label: str, title: str) -> str:
    return f"""
  <defs>
    <linearGradient id="border" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{ACCENT_PINK}"/>
      <stop offset="50%" stop-color="{ACCENT_PURPLE}"/>
      <stop offset="100%" stop-color="{ACCENT_CYAN}"/>
    </linearGradient>
    <linearGradient id="card-bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{BG_DARK_TOP}"/>
      <stop offset="100%" stop-color="{BG_DARK}"/>
    </linearGradient>
  </defs>
  <rect width="{width}" height="{height}" rx="20" fill="url(#card-bg)"/>
  <rect width="{width}" height="{height}" rx="20" fill="none" stroke="url(#border)" stroke-width="2"/>
  <text x="32" y="40" font-family="{FONT}" font-size="11" font-weight="600" fill="{TXT_DIM}" letter-spacing="2">{label}</text>
  <text x="32" y="64" font-family="{FONT}" font-size="16" font-weight="700" fill="{TXT_LIGHT}">{title}</text>
  <line x1="32" y1="82" x2="{width - 32}" y2="82" stroke="{BORDER_DIM}" stroke-width="1"/>
"""


def render_stats_card(user: dict, repos: list[dict]) -> str:
    own_repos = [r for r in repos if not r.get("fork")]
    stars = sum(r.get("stargazers_count", 0) for r in own_repos)
    forks_received = sum(r.get("forks_count", 0) for r in own_repos)
    repo_count = len(own_repos)
    followers = user.get("followers", 0)
    following = user.get("following", 0)
    public_gists = user.get("public_gists", 0)

    rows = [
        ("⭐", "Total Stars", stars, ACCENT_YELLOW),
        ("📦", "Public Repos", repo_count, ACCENT_CYAN),
        ("👥", "Followers", followers, ACCENT_PINK),
        ("➡️", "Following", following, ACCENT_CORAL),
        ("🍴", "Forks Received", forks_received, ACCENT_PURPLE),
        ("📝", "Public Gists", public_gists, ACCENT_INDIGO),
    ]

    width, height = 500, 320
    body = []
    for i, (icon, label, value, color) in enumerate(rows):
        y = 108 + i * 34
        body.append(
            f'  <text x="32" y="{y}" font-family="{FONT}" font-size="14">{icon}</text>'
            f'  <text x="60" y="{y}" font-family="{FONT}" font-size="13" font-weight="500" fill="{TXT_MUTED}">{label}</text>'
            f'  <text x="{width - 32}" y="{y}" text-anchor="end" font-family="{FONT}" font-size="20" font-weight="800" fill="{color}">{value}</text>'
        )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="GitHub stats for {GH_USER}">
{card_frame(width, height, "GITHUB  STATS", f"📊  @{GH_USER}")}
{chr(10).join(body)}
</svg>
"""


def render_top_langs(lang_bytes: dict[str, int], top_n: int = 6) -> str:
    items = sorted(lang_bytes.items(), key=lambda kv: kv[1], reverse=True)[:top_n]
    total = sum(v for _, v in items) or 1

    width = 500
    row_h = 34
    height = max(220, 100 + row_h * max(len(items), 1) + 20)

    body = []
    for i, (lang, bytes_) in enumerate(items):
        pct = bytes_ / total * 100
        color = LANG_COLORS.get(lang, ACCENT_CYAN)
        y = 108 + i * row_h
        bar_x = 180
        bar_max = width - bar_x - 90
        bar_w = max(2, int(bar_max * pct / 100))
        body.append(
            f'  <circle cx="40" cy="{y + 4}" r="5" fill="{color}"/>'
            f'  <text x="56" y="{y + 9}" font-family="{FONT}" font-size="13" font-weight="600" fill="{TXT_LIGHT}">{lang}</text>'
            f'  <rect x="{bar_x}" y="{y - 4}" width="{bar_max}" height="14" rx="7" fill="#1A1428"/>'
            f'  <rect x="{bar_x}" y="{y - 4}" width="{bar_w}" height="14" rx="7" fill="{color}"/>'
            f'  <text x="{width - 32}" y="{y + 9}" text-anchor="end" font-family="{FONT}" font-size="12" font-weight="700" fill="{TXT_MUTED}">{pct:.1f}%</text>'
        )

    if not items:
        body.append(
            f'  <text x="{width//2}" y="{height//2 + 20}" text-anchor="middle" font-family="{FONT}" font-size="14" fill="{TXT_DIM}">No language data</text>'
        )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="Top languages for {GH_USER}">
{card_frame(width, height, "MOST  USED  LANGUAGES", "🎨  Top Languages")}
{chr(10).join(body)}
</svg>
"""


def render_leetcode(payload: dict) -> str:
    width, height = 500, 320
    user = (payload.get("data") or {}).get("matchedUser") or {}
    if not user:
        return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">
{card_frame(width, height, "LEETCODE", f"🧩  @{LC_USER}")}
  <text x="{width//2}" y="{height//2}" text-anchor="middle" font-family="{FONT}" font-size="14" fill="{TXT_DIM}">User not found</text>
</svg>
"""

    ranking = (user.get("profile") or {}).get("ranking", "—")
    ac = {x["difficulty"]: x["count"] for x in user["submitStats"]["acSubmissionNum"]}
    totals = {x["difficulty"]: x["count"] for x in (payload["data"]["allQuestionsCount"] or [])}

    easy = ac.get("Easy", 0)
    medium = ac.get("Medium", 0)
    hard = ac.get("Hard", 0)
    solved_all = ac.get("All", easy + medium + hard)
    total_all = totals.get("All", 1) or 1

    rows = [
        ("Easy", easy, totals.get("Easy", 1) or 1, ACCENT_GREEN),
        ("Medium", medium, totals.get("Medium", 1) or 1, ACCENT_YELLOW),
        ("Hard", hard, totals.get("Hard", 1) or 1, "#FF375F"),
    ]

    body = [
        f'  <text x="32" y="118" font-family="{FONT}" font-size="11" font-weight="600" fill="{TXT_DIM}" letter-spacing="2">SOLVED</text>',
        f'  <text x="32" y="158" font-family="{FONT}" font-size="36" font-weight="800" fill="{TXT_LIGHT}">{solved_all}<tspan font-size="18" font-weight="500" fill="{TXT_DIM}"> / {total_all}</tspan></text>',
        f'  <text x="{width - 32}" y="118" text-anchor="end" font-family="{FONT}" font-size="11" font-weight="600" fill="{TXT_DIM}" letter-spacing="2">RANKING</text>',
        f'  <text x="{width - 32}" y="158" text-anchor="end" font-family="{FONT}" font-size="24" font-weight="800" fill="{ACCENT_CYAN}">#{ranking}</text>',
    ]

    for i, (label, val, total, color) in enumerate(rows):
        y = 200 + i * 38
        pct = val / total * 100
        bar_x = 124
        bar_max = width - bar_x - 80
        bar_w = max(2, int(bar_max * pct / 100))
        body.extend([
            f'  <circle cx="40" cy="{y + 4}" r="5" fill="{color}"/>',
            f'  <text x="56" y="{y + 9}" font-family="{FONT}" font-size="13" font-weight="600" fill="{color}">{label}</text>',
            f'  <rect x="{bar_x}" y="{y - 4}" width="{bar_max}" height="14" rx="7" fill="#1A1428"/>',
            f'  <rect x="{bar_x}" y="{y - 4}" width="{bar_w}" height="14" rx="7" fill="{color}"/>',
            f'  <text x="{width - 32}" y="{y + 9}" text-anchor="end" font-family="{FONT}" font-size="12" font-weight="700" fill="{TXT_MUTED}">{val} / {total}</text>',
        ])

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="LeetCode stats for {LC_USER}">
{card_frame(width, height, "LEETCODE", f"🧩  @{LC_USER}")}
{chr(10).join(body)}
</svg>
"""


def render_leetcode_placeholder() -> str:
    width, height = 500, 320
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="LeetCode card for {LC_USER}">
{card_frame(width, height, "LEETCODE", f"🧩  @{LC_USER}")}
  <text x="{width//2}" y="{height//2 + 4}" text-anchor="middle" font-family="{FONT}" font-size="14" fill="{TXT_MUTED}">Stats will appear after the next scheduled run.</text>
  <text x="{width//2}" y="{height//2 + 28}" text-anchor="middle" font-family="{FONT}" font-size="12" fill="{TXT_DIM}">(LeetCode often blocks non-CI clients)</text>
</svg>
"""


# ---------- main ----------

def write(name: str, content: str) -> None:
    path = ASSETS / name
    path.write_text(content, encoding="utf-8")
    print(f"  wrote {path.relative_to(ASSETS.parent)}")


def safe(fn, default, label):
    try:
        return fn()
    except Exception as e:  # noqa: BLE001
        print(f"  ⚠️  {label} failed: {e}", file=sys.stderr)
        return default


def main() -> int:
    ASSETS.mkdir(parents=True, exist_ok=True)
    print(f"==> Fetching GitHub data for {GH_USER}")
    user = safe(fetch_user, {}, "fetch_user")
    repos = safe(fetch_repos, [], "fetch_repos")
    langs = safe(lambda: fetch_languages(repos), {}, "fetch_languages")

    if user:
        write("stats.svg", render_stats_card(user, repos))
    if langs:
        write("top-langs.svg", render_top_langs(langs))

    print(f"==> Fetching LeetCode data for {LC_USER}")
    lc = safe(fetch_leetcode, {}, "fetch_leetcode")
    if lc:
        write("leetcode.svg", render_leetcode(lc))
    elif not (ASSETS / "leetcode.svg").exists():
        write("leetcode.svg", render_leetcode_placeholder())

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
