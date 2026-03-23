# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Jarvis Dashboard — a self-hosted homelab dashboard combining infrastructure monitoring, container management, media discovery, and automated torrent downloads. Integrates Jellyfin, qBittorrent, Docker, TMDB, Reddit Wiki, and wttr.in.

## Commands

### Frontend (from `frontend/`)
```bash
npm run dev          # Dev server on :3000
npm run build        # Production build
npm start            # Production server on :3000
```

### Backend (from `backend/`)
```bash
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8002   # Dev server on :8002
```

No test or lint tooling is configured.

### After making changes
After any code change, **always** rebuild/restart the affected server(s), verify they respond (e.g. `curl` the health endpoint), and only then report back to the user. Do not report a change as done without restarting and testing.
- **Frontend**: Runs in production mode. Must `npm run build` then `npm start` (not `npm run dev`). Kill any existing `next start` process first.
- **Backend**: Kill existing uvicorn and restart: `source venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8002`

## Architecture

```
Browser → Next.js (:3000) → rewrites /api/* → FastAPI (:8002) → external services
```

**Frontend:** Next.js 16 App Router, React 19, TypeScript, SCSS Modules. No utility CSS framework.

**Backend:** FastAPI with router/service separation. Routers handle HTTP, services encapsulate business logic and external API calls.

### Frontend data flow
- `lib/DataContext.tsx` — global state provider with two polling cycles:
  - Fast (5s): system stats, containers, torrents, jellyfin, processes, bandwidth
  - Slow (5min): storage sizes, weather
- Uses `Promise.allSettled()` so individual API failures don't break the dashboard
- `lib/ThemeContext.tsx` — dark/light mode, persisted to localStorage (`jarvis-theme`)

### Backend patterns
- Routers: `app/routers/` — system, docker, torrents, media, recommendations, files, actions
- Services: `app/services/` — system, docker, tmdb, jellyfin, qbittorrent, files, wiki
- In-memory caching with TTL (module-level dicts) — no database
- `ThreadPoolExecutor` for parallel TMDB/Jellyfin enrichment
- Background thread for bandwidth collection (30-min rolling window)
- Config via Pydantic settings in `app/config.py`, loaded from `.env`

### Frontend routing (App Router)
- `/` — dashboard overview
- `/discover` — media discovery (mood, similar, library, trending)
- `/discover/[type]/[id]` — movie/series detail page
- `/system`, `/docker`, `/torrents`, `/media`, `/files` — dedicated pages

### Styling
- SCSS Modules per component, global styles in `styles/`
- CSS custom properties for theming (switched via `data-theme` attribute)
- Design tokens in `styles/_variables.scss` (colors, spacing, typography, breakpoints)
- Breakpoints: mobile 640px, tablet 768px, desktop 1024px, wide 1280px

## Environment

Copy `.env.example` to `.env` at project root. Required: `JELLYFIN_API_KEY`, `QBIT_USER`, `QBIT_PASS`, `TMDB_API_KEY`. Optional: `MEDIA_PATH`, `FILE_HOME`, `WEATHER_CITY`, `JELLYFIN_BASE`, `QBIT_BASE`.

## Key files

- `frontend/next.config.ts` — API rewrite proxy rules and allowed dev origins
- `frontend/lib/api.ts` — fetch wrapper and formatting utilities
- `frontend/lib/toast.ts` — toast notification system
- `backend/app/main.py` — FastAPI app entry, router registration, CORS, lifespan
- `backend/app/config.py` — all environment variable definitions with defaults
