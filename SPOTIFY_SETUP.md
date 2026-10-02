# 🎵 Spotify Now Playing on My GitHub Profile

I built a small GitHub Actions setup that shows what I'm currently listening to on Spotify directly on my GitHub profile.

## How I set it up

1. I created an app in the Spotify Developer Dashboard with `http://127.0.0.1:8888/callback` as the redirect URI.
2. I authorized the `user-read-currently-playing` and `user-read-playback-state` scopes.
3. Spotify redirected me to `http://127.0.0.1:8888/callback?code=...`. Since I wasn't running a local server, `ERR_CONNECTION_REFUSED` was expected; I only needed the authorization code from the URL.
4. I exchanged the code for a refresh token and stored `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, and `SPOTIFY_REFRESH_TOKEN` as GitHub Actions secrets.
5. My Python script refreshes the access token and calls Spotify's `/v1/me/player/currently-playing` endpoint.
6. It generates an 800×220 SVG with the track, artist, album artwork, playback progress, and an animated equalizer.
7. GitHub Actions periodically regenerates and commits the SVG, which is displayed in my profile README.

## Architecture

```text
Spotify
   ↓
OAuth Refresh Token
   ↓
Currently Playing API
   ↓
Python SVG Generator
   ↓
assets/spotify.svg
   ↓
GitHub Actions
   ↓
My GitHub Profile 🎧
```

## Things I learned

- Spotify's playback API required the Developer app owner's account to have an active Premium subscription for this setup.
- A newly activated Premium subscription can take some time before Spotify's API recognizes it.
- GitHub aggressively caches README images, so I change a `?v=...` value in the SVG URL whenever the card changes.
- I log Spotify's API error messages for debugging while ensuring credentials are never printed.

The result is a small, automatically updating Spotify card on my GitHub profile without committing Spotify credentials to the repository.
