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
            if isinstance(detail, dict):
                message = detail.get("message", json.dumps(detail))
            else:
                message = str(detail)
        except (json.JSONDecodeError, AttributeError):
            message = body[:500] or e.reason
        raise RuntimeError(f"Spotify API HTTP {e.code}: {message}") from None

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
    title = item.get("name", "Unknown")
    artists = ", ".join(a["name"] for a in item.get("artists", [])) or "Spotify"
    playing = bool(track.get("is_playing"))
    url = item.get("external_urls", {}).get("spotify", "https://open.spotify.com/")
    status = "NOW PLAYING" if playing else "PAUSED"
else:
    title, artists, status, url = "Nothing playing", "Spotify", "OFFLINE", "https://open.spotify.com/"

def esc(s):
    return html.escape(str(s), quote=True)

svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="560" height="120" role="img" aria-label="Spotify: {esc(title)} by {esc(artists)}">
  <style>
    .bg {{ fill: #0d1117; }}
    .title {{ fill: #f0f6fc; font: 600 18px -apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif; }}
    .artist {{ fill: #8b949e; font: 14px -apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif; }}
    .status {{ fill: #1DB954; font: 700 11px -apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif; letter-spacing: 1px; }}
    .note {{ fill: #1DB954; font: 700 32px sans-serif; }}
  </style>
  <rect class="bg" width="560" height="120" rx="12"/>
  <circle cx="55" cy="60" r="34" fill="#161b22"/>
  <text class="note" x="43" y="71">♫</text>
  <text class="status" x="105" y="37">{esc(status)} ON SPOTIFY</text>
  <text class="title" x="105" y="66">{esc(title[:42])}</text>
  <text class="artist" x="105" y="91">{esc(artists[:55])}</text>
  <a href="{esc(url)}" target="_blank"><rect x="0" y="0" width="560" height="120" fill="transparent"/></a>
</svg>
"""
os.makedirs("assets", exist_ok=True)
with open("assets/spotify.svg", "w", encoding="utf-8") as f:
    f.write(svg)
