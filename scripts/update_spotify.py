import base64
import html
import json
import os
import urllib.parse
import urllib.request
from urllib.error import HTTPError

CLIENT_ID = os.environ["SPOTIFY_CLIENT_ID"]
CLIENT_SECRET = os.environ["SPOTIFY_CLIENT_SECRET"]
REFRESH_TOKEN = os.environ["SPOTIFY_REFRESH_TOKEN"]

def request(url, *, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            if r.status == 204:
                return None
            return json.loads(r.read().decode())
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(body)
            detail = payload.get("error", payload)
            message = detail.get("message", json.dumps(detail)) if isinstance(detail, dict) else str(detail)
        except (json.JSONDecodeError, AttributeError):
            message = body[:500] or e.reason
        raise RuntimeError(f"Spotify API HTTP {e.code}: {message}") from None

def esc(value):
    return html.escape(str(value), quote=True)

def embed_image(url):
    """Download artwork and return a self-contained data URI for the SVG."""
    if not url:
        return ""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = r.read()
            content_type = (r.headers.get_content_type() or "image/jpeg").lower()
            if not content_type.startswith("image/"):
                content_type = "image/jpeg"
            return f"data:{content_type};base64,{base64.b64encode(data).decode('ascii')}"
    except Exception as e:
        print(f"Warning: could not embed Spotify artwork: {e}")
        return ""

def shorten(value, limit):
    value = str(value or "")
    return value if len(value) <= limit else value[:limit - 1].rstrip() + "…"

def clock(ms):
    seconds = max(0, int(ms or 0) // 1000)
    return f"{seconds // 60}:{seconds % 60:02d}"

basic = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
token = request(
    "https://accounts.spotify.com/api/token",
    data=urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": REFRESH_TOKEN,
    }).encode(),
    headers={
        "Authorization": f"Basic {basic}",
        "Content-Type": "application/x-www-form-urlencoded",
    },
)["access_token"]

track = request(
    "https://api.spotify.com/v1/me/player/currently-playing",
    headers={"Authorization": f"Bearer {token}"},
)

if track and track.get("item"):
    item = track["item"]
    title = item.get("name") or "Unknown track"
    artists = ", ".join(a.get("name", "") for a in item.get("artists", []) if a.get("name")) or "Spotify"
    album = item.get("album", {}).get("name") or ""
    images = item.get("album", {}).get("images", [])
    artwork = images[0].get("url", "") if images else ""
    playing = bool(track.get("is_playing"))
    status = "NOW PLAYING" if playing else "PAUSED"
    url = item.get("external_urls", {}).get("spotify", "https://open.spotify.com/")
    progress = max(0, int(track.get("progress_ms") or 0))
    duration = max(1, int(item.get("duration_ms") or 1))
else:
    title, artists, album = "Nothing playing right now", "Spotify", "Check back later"
    artwork = ""
    playing = False
    status = "OFFLINE"
    url = "https://open.spotify.com/"
    progress, duration = 0, 1

ratio = min(1.0, progress / duration)
bar_x, bar_y, bar_w = 226, 172, 514
progress_w = round(bar_w * ratio, 1)
remaining = max(0.1, (duration - progress) / 1000)
album_line = shorten(album, 58)
title_line = shorten(title, 48)
artists_line = shorten(artists, 58)

embedded_artwork = embed_image(artwork)

art = (
    f'<image href="{embedded_artwork}" x="34" y="34" width="152" height="152" '
    f'preserveAspectRatio="xMidYMid slice" clip-path="url(#coverClip)"/>'
    if embedded_artwork else
    '<rect x="34" y="34" width="152" height="152" rx="16" class="coverFallback"/>'
    '<text x="110" y="128" text-anchor="middle" class="musicNote">♫</text>'
)

equalizer = ""
for i, (x, h, dur) in enumerate([(690, 18, 0.72), (700, 28, 0.91), (710, 22, 0.63), (720, 32, 0.84), (730, 16, 0.76)]):
    y = 61 - h / 2
    if playing:
        equalizer += (
            f'<rect x="{x}" y="{y}" width="5" height="{h}" rx="2.5" class="eq">'
            f'<animate attributeName="height" values="{h};6;{h * .7:.1f};{h}" dur="{dur}s" repeatCount="indefinite"/>'
            f'<animate attributeName="y" values="{y};58;{61 - h * .35:.1f};{y}" dur="{dur}s" repeatCount="indefinite"/>'
            '</rect>'
        )
    else:
        equalizer += f'<rect x="{x}" y="57" width="5" height="8" rx="2.5" class="eq muted"/>'

progress_animation = ""
elapsed_time = f'<text class="time" x="{bar_x}" y="198">{clock(progress)}</text>'
if playing and progress < duration:
    progress_animation = (
        f'<animate attributeName="width" from="{progress_w}" to="{bar_w}" '
        f'dur="{remaining:.1f}s" fill="freeze"/>'
    )

    # SVG cannot numerically increment formatted MM:SS text, so build one
    # discrete SMIL animation containing the remaining second labels.
    start_second = max(0, progress // 1000)
    end_second = max(start_second, duration // 1000)
    labels = ";".join(clock(second * 1000) for second in range(start_second, end_second + 1))
    elapsed_time = (
        f'<text class="time" x="{bar_x}" y="198">'
        f'<animate attributeName="textContent" values="{labels}" '
        f'dur="{remaining:.1f}s" calcMode="discrete" fill="freeze"/>'
        f'{clock(progress)}</text>'
    )

svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="800" height="220" viewBox="0 0 800 220"
 role="img" aria-label="Spotify: {esc(title)} by {esc(artists)}">
  <defs>
    <clipPath id="coverClip"><rect x="34" y="34" width="152" height="152" rx="16"/></clipPath>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" class="bgA"/><stop offset="100%" class="bgB"/>
    </linearGradient>
  </defs>
  <style>
    .bgA {{ stop-color:#0d1117; }} .bgB {{ stop-color:#111820; }}
    .card {{ fill:url(#bg); stroke:#30363d; stroke-width:1; }}
    .title {{ fill:#f0f6fc; font:600 23px -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif; }}
    .artist {{ fill:#c9d1d9; font:500 16px -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif; }}
    .album {{ fill:#8b949e; font:14px -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif; }}
    .status {{ fill:#1ed760; font:700 12px -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif; letter-spacing:1.5px; }}
    .time {{ fill:#8b949e; font:12px -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif; }}
    .eq {{ fill:#1ed760; }} .muted {{ opacity:.55; }}
    .track {{ fill:#30363d; }} .played {{ fill:#1ed760; }}
    .coverFallback {{ fill:#161b22; stroke:#30363d; }}
    .musicNote {{ fill:#1ed760; font:700 48px sans-serif; }}
    @media (prefers-color-scheme: light) {{
      .bgA {{ stop-color:#ffffff; }} .bgB {{ stop-color:#f6f8fa; }}
      .card {{ stroke:#d0d7de; }} .title {{ fill:#1f2328; }}
      .artist {{ fill:#424a53; }} .album,.time {{ fill:#656d76; }}
      .track {{ fill:#d8dee4; }} .coverFallback {{ fill:#f6f8fa; stroke:#d0d7de; }}
    }}
  </style>

  <rect class="card" x="0.5" y="0.5" width="799" height="219" rx="18"/>
  {art}

  <circle cx="226" cy="51" r="5" fill="#1ed760"/>
  <text class="status" x="240" y="55">{esc(status)} ON SPOTIFY</text>
  {equalizer}

  <text class="title" x="226" y="94">{esc(title_line)}</text>
  <text class="artist" x="226" y="121">{esc(artists_line)}</text>
  <text class="album" x="226" y="145">{esc(album_line)}</text>

  <rect class="track" x="{bar_x}" y="{bar_y}" width="{bar_w}" height="5" rx="2.5"/>
  <rect class="played" x="{bar_x}" y="{bar_y}" width="{progress_w}" height="5" rx="2.5">
    {progress_animation}
  </rect>
  {elapsed_time}
  <text class="time" x="{bar_x + bar_w}" y="198" text-anchor="end">{clock(duration)}</text>

  <a href="{esc(url)}" target="_blank">
    <rect x="0" y="0" width="800" height="220" rx="18" fill="transparent"/>
  </a>
</svg>
"""

os.makedirs("assets", exist_ok=True)
with open("assets/spotify.svg", "w", encoding="utf-8") as f:
    f.write(svg)
