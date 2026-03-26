# Jarvis Dashboard — Comprehensive Audit Report

**Date:** March 25, 2026
**Scope:** Full-stack audit — UI/UX, architecture, performance, security, movie buff experience
**Codebase:** ~3,500 lines backend (8 routers, 11 services) + ~4,000 lines frontend (10 pages, 6 components)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Scorecard](#2-scorecard)
3. [Movie Buff Perspective](#3-movie-buff-perspective)
4. [UI/UX Judge Review](#4-uiux-judge-review)
5. [Performance & Optimization](#5-performance--optimization)
6. [Network & API Efficiency](#6-network--api-efficiency)
7. [Backend Architecture](#7-backend-architecture)
8. [Caching & Data Strategy](#8-caching--data-strategy)
9. [Security Posture](#9-security-posture)
10. [Code Quality & DX](#10-code-quality--dx)
11. [Prioritized Improvement Roadmap](#11-prioritized-improvement-roadmap)

---

## 1. Executive Summary

Jarvis Dashboard is a remarkably ambitious self-hosted homelab dashboard that combines **infrastructure monitoring**, **container management**, **media discovery**, **torrent automation**, and a **kanban task board** into a single unified interface. For a personal project, the breadth is impressive — it rivals commercial tools like Organizr or Heimdall while adding unique media intelligence features.

**What it does exceptionally well:**
- Beautiful glassmorphic UI with polished dark/light themes
- Smart movie discovery with 4 distinct recommendation engines (mood, similar, library-based, trending)
- Seamless torrent → Jellyfin pipeline (search → download → watch)
- Clean FastAPI backend with proper router/service separation
- Responsive design that works on mobile

**Where it falls short:**
- No persistent data layer — everything lives in memory caches that vanish on restart
- API call explosion — a single discover page load can trigger 90+ TMDB calls
- Missing social/personal features a movie buff craves (watchlist, personal ratings, watched tracking)
- No authentication — anyone on the network has full access
- Zero test coverage

---

## 2. Scorecard

| Domain | Score | Grade | Summary |
|--------|-------|-------|---------|
| **Visual Design** | 8.5/10 | A | Gorgeous glassmorphic UI, consistent theming, polished feel |
| **UX Flow** | 7/10 | B | Good discovery flow but friction points in series handling, no watchlist |
| **Movie Buff Features** | 5.5/10 | C+ | Great discovery, but missing personal tracking features |
| **Performance** | 6/10 | C | Fast once cached, but cold starts are brutal (90+ API calls) |
| **Network Efficiency** | 5/10 | C- | Redundant TMDB calls, no request batching, risks TMDB rate limits |
| **Backend Architecture** | 7.5/10 | B+ | Clean separation, good patterns, but unbounded caches |
| **Caching Strategy** | 5.5/10 | C+ | Aggressive TTLs but no eviction, no persistence, no invalidation |
| **Security** | 4/10 | D | No auth, no rate limiting, credentials in plaintext |
| **Code Quality** | 7/10 | B | Well-organized, but some duplication and weak typing |
| **DevOps/Infra** | 4.5/10 | D+ | No Docker, no CI/CD, no systemd, manual deploys |
| **Overall** | **6.5/10** | **B-** | Strong foundation, impressive scope — needs hardening |

---

## 3. Movie Buff Perspective

### What a Movie Buff Loves

**The Discovery Engine is Genuinely Good**
The 4-tab recommendation system (Mood / Similar / Library / Trending) is the standout feature. The mood-based picker with 12 curated moods is delightful — it feels like browsing a human-curated film guide, not an algorithm dump. The Reddit Wiki knowledge base adds a layer of taste that pure TMDB recommendations lack.

**Torrent Integration is Seamless**
Click a movie → Find Torrent → pick quality → it's downloading in qBittorrent with correct category tagging. For a piracy-friendly homelab, this is *chef's kiss*. The series season picker that shows which episodes are already in Jellyfin is brilliant.

**New IMDB + Letterboxd Badges**
The clickable rating badges on detail pages let you quickly cross-reference ratings across platforms. IMDB for crowd consensus, Letterboxd for cinephile taste — exactly what a movie buff checks.

### What a Movie Buff is Missing

| Missing Feature | Impact | Difficulty | Notes |
|----------------|--------|------------|-------|
| **Watchlist / "Save for Later"** | HIGH | Medium | The #1 missing feature. You discover amazing movies but have no way to bookmark them without downloading immediately. |
| **"Watched" Tracking** | HIGH | Medium | Jellyfin tracks what you played, but there's no explicit "I've seen this" toggle for movies not in your library. |
| **Personal Rating** | MEDIUM | Low | After watching, you want to rate it. Even a simple 1-5 star or thumbs up/down would add huge value. |
| **Watch History Timeline** | MEDIUM | Medium | "What did I watch last month?" — a chronological view of your viewing history from Jellyfin. |
| **Trailer Playback** | MEDIUM | Low | TMDB has trailer video keys. Embed a YouTube trailer player on the detail page — every movie site does this. |
| **"Because You Watched X"** | LOW | Low | Recommendation explanations. Instead of just showing results, say "Because you liked Inception" next to similar titles. |
| **Cast Filmography Links** | LOW | Low | Clicking a cast member should show their other movies (TMDB has this data). |
| **Custom Lists** | LOW | Medium | "Best Sci-Fi of 2025", "Weekend Comfort Movies" — personal curated lists. |
| **Collection Awareness** | LOW | Medium | Know that "The Dark Knight" is part of the Nolan Batman trilogy. TMDB provides collection data. |
| **Sharing** | LOW | Medium | Share a movie recommendation with friends (link or message). |

### The Dream Flow (What the Dashboard Should Feel Like)

```
1. Open Discover → see personalized "For You" based on watch history
2. Browse by mood → find interesting movie
3. Save to watchlist (not download yet)
4. Later, decide to watch → one-click download
5. After watching → rate it, mark as watched
6. Dashboard learns your taste → better recommendations next time
```

Currently the flow breaks at step 3 — you either download immediately or lose the recommendation.

---

## 4. UI/UX Judge Review

### Strengths

**Visual Design — 8.5/10**
- The glassmorphic card design with `backdrop-filter: blur()` is genuinely beautiful
- Dark theme is the primary design and it *shows* — the color palette (deep blacks, accent blues, subtle borders) feels premium
- Light theme works but is clearly secondary — still good though
- Typography is well-considered: `-apple-system` stack, clear hierarchy from `$text-xs` (0.69rem) to `$text-4xl` (2.5rem)
- Design tokens in `_variables.scss` are comprehensive (108 lines of colors, spacing, radii, easings, breakpoints)

**Layout & Navigation — 7.5/10**
- Top navigation bar is clean and uncluttered
- Mobile bottom nav is a smart choice
- Page structure is consistent: header → body → content sections
- Breadcrumbs on the detail page aid orientation

**Micro-interactions — 7/10**
- Cards lift on hover (`translateY(-2px)`)
- Stagger animations on grid items (`stagger-children` class)
- Smooth theme transitions
- Toast notifications for feedback

### Issues

**Loading States — 6/10**
- Main discover page shows spinners, but there's no skeleton/shimmer loading
- Detail page shows "Loading details..." text — a skeleton layout would feel faster
- External ratings load lazily (good!) but pop in with no transition — feels jarring
- Library tab loads silently in the background on mount (good) but shows nothing until done

**Error Recovery — 5/10**
- Errors show toast messages but no retry buttons
- Failed secondary checks (library status, streaming, ratings) fail completely silently
- No offline/degraded state handling — if backend is down, the whole UI breaks with no helpful message

**Information Density — 7/10**
- Recommendation cards are well-balanced (poster + title + year + type + rating + description + action)
- Detail page hero section packs a lot of info without feeling cramped
- BUT: the discover page mood grid takes up a lot of vertical space before showing results — consider making moods more compact or showing default results on load

**Accessibility — 4/10**
- No keyboard navigation for autocomplete dropdowns (except tasks page)
- Color-only status indicators on Docker page (no text fallback)
- Missing form labels on search inputs
- No focus ring styling beyond browser defaults
- No ARIA attributes on interactive elements (modals, dropdowns)
- No skip-to-content link

**Mobile UX — 6.5/10**
- Responsive grids adapt well
- Bottom nav works
- BUT: Detail page hero poster is still 160px wide on mobile — takes up too much space
- Search results dropdown can overflow viewport on small screens
- Torrent result rows are too cramped on mobile (seeders/leechers/size all inline)

---

## 5. Performance & Optimization

### Frontend Performance

| Issue | Severity | Location | Fix |
|-------|----------|----------|-----|
| **No `<Image>` component** | HIGH | All pages use raw `<img>` | Switch to `next/image` for automatic WebP, srcSet, lazy loading, and caching |
| **No skeleton loading** | MEDIUM | Discover, Detail pages | Add CSS skeleton shimmers for perceived performance |
| **Polling when tab hidden** | MEDIUM | `DataContext.tsx` | Add `document.visibilitychange` listener — pause polling when tab is inactive |
| **Polls ALL endpoints regardless of page** | MEDIUM | `DataContext.tsx` | If user is on `/files`, no need to poll Docker stats. Add per-page selective polling |
| **Stagger animation limit** | LOW | `globals.scss:748` | Hardcoded for 20 children max — fails gracefully but limits large lists |
| **TorrentSearchModal duplicated** | LOW | `discover/page.tsx` + `[type]/[id]/page.tsx` | Extract to shared component |
| **Discover page is 782 lines** | LOW | `discover/page.tsx` | Split into sub-components (MoodPicker, SimilarSearch, etc.) |

### Backend Performance

| Issue | Severity | Location | Fix |
|-------|----------|----------|-----|
| **`/library` triggers ~90 TMDB calls** | HIGH | `recommendations.py:252-427` | 40 library item enrichments + 6 rec batches + genre discover. Needs pagination + lazy enrichment |
| **`/mood` movie path triggers ~25 TMDB calls** | HIGH | `recommendations.py:83-197` | Wiki KB load + discover + enrich 20 items. Consider pre-enriching wiki KB |
| **`/overview` makes 11 sequential Jellyfin calls** | MEDIUM | `media.py:138-280` | Parallelize with ThreadPoolExecutor |
| **`get_processes()` runs `ps aux` twice** | LOW | `system.py:76-100` | Once for all processes, once for top 15 — combine into single call |
| **Apibay search creates new httpx client each call** | LOW | `qbittorrent.py:82` | Use module-level client |

### Cold Start Timing

First load of discover page (nothing cached):
```
/api/recommendations/trending    → 2 TMDB calls      ~400ms
/api/recommendations/library     → 90 TMDB calls      ~8-12s (!!!)
/api/recommendations/mood        → 25 TMDB calls      ~3-5s
/api/recommendations/detail      → 4 TMDB calls       ~800ms
/api/recommendations/ext-ratings → 2 external calls    ~400ms
```

After caching (24h TTL): All endpoints respond in <50ms.

**TMDB Rate Limit Risk:** Free tier allows 40 requests per 10 seconds. The `/library` endpoint alone can hit 90 calls — this WILL trigger rate limiting and cause 429 errors on cold start.

---

## 6. Network & API Efficiency

### API Call Map Per User Action

```
Dashboard Load (every 5s poll):
├─ GET /api/system              → reads /proc (local, instant)
├─ GET /api/docker/containers   → docker ps (local, ~200ms)
├─ GET /api/docker/stats        → docker stats (local, ~500ms-2s)
├─ GET /api/qbit/transfer/info  → 1 qBit call
├─ GET /api/qbit/torrents/info  → 1 qBit call
├─ GET /api/jellyfin/counts     → 1 Jellyfin call
├─ GET /api/jellyfin/latest     → 1 Jellyfin call
├─ GET /api/jellyfin/sessions   → 1 Jellyfin call
├─ GET /api/processes           → 2x ps aux (local)
└─ GET /api/bandwidth/history   → in-memory (instant)
Total: 5 external API calls per 5s cycle

Discover Page Mount:
├─ GET /api/recommendations/trending  → 2 TMDB calls
└─ GET /api/recommendations/library   → 2 Jellyfin + 90 TMDB calls (!!!)
Total: 94 external calls on mount

Movie Detail Page:
├─ GET /api/recommendations/detail         → 4 TMDB calls (parallel)
├─ GET /api/jellyfin-media/library-check   → 1 Jellyfin call
├─ GET /api/streaming/check                → 1 AllAnime call
├─ GET /api/recommendations/ext-ratings    → 1 OMDb + 1 Letterboxd scrape
└─ GET /api/streaming/youtube (Indian)     → 1 yt-dlp search
Total: 5-9 external calls (reasonable)
```

### Optimization Opportunities

| Opportunity | Savings | Effort |
|------------|---------|--------|
| **Paginate `/library` enrichment** — enrich first 10 items, lazy-load rest | 75% fewer TMDB calls | Medium |
| **Cache TMDB `fetch()` at service level** — many endpoints re-fetch same TMDB IDs | 30-50% fewer calls | Low |
| **Pre-build wiki KB with TMDB data** — enrich wiki KB once daily instead of per-request | Eliminates 20 calls per mood request | Medium |
| **Skip enrichment for items with posters** — `enrich_with_posters()` re-fetches even if poster exists | 10-20% fewer calls | Low |
| **Batch Jellyfin overview calls** — combine 8 Jellyfin requests into 3-4 | 50% fewer Jellyfin calls | Low |
| **Add `fetch()` level caching in tmdb.py** — LRU cache on raw TMDB responses | Prevents duplicate calls across endpoints | Low |

---

## 7. Backend Architecture

### What's Done Well

- **Router/Service separation** — clean, consistent, easy to navigate
- **Pydantic settings** — typed config with `.env` loading
- **ThreadPoolExecutor** — parallel API calls where it matters (detail, trending, enrichment)
- **Atomic file writes** — tasks.py uses `tempfile + os.replace()` for crash safety
- **Input validation** — Docker actions whitelist, container name regex, file path traversal protection
- **Image proxy** — TMDB images proxied with 7-day cache headers, avoiding CORS issues

### Architecture Concerns

| Concern | Details |
|---------|---------|
| **No database** | All state is in-memory dicts or JSON files. Caches lost on restart. Tasks stored as JSON. No query capability. |
| **No async** | FastAPI supports async but all endpoints are synchronous. ThreadPoolExecutor compensates but doesn't scale. |
| **Monolith scaling** | Single uvicorn process handles everything — system stats, Docker calls, TMDB calls, Letterboxd scraping. A slow Letterboxd scrape blocks a worker thread. |
| **No health check endpoint** | No `/health` or `/ready` endpoint for monitoring. |
| **No request logging middleware** | No audit trail of who accessed what. |
| **Hardcoded IPs** | Jellyfin play link uses `192.168.0.2` (fixed in recent commit with `window.location.hostname`, but backend still has hardcoded references). |

### Recommended Architecture Improvements

```
Current:
  Browser → Next.js (:3000) → rewrite → FastAPI (:8002) → external APIs

Better:
  Browser → Next.js (:3000) → rewrite → FastAPI (:8002) → external APIs
                                              ↓
                                         SQLite/Redis
                                      (cache + user data)
```

Adding a lightweight SQLite database would solve:
- Watchlist persistence
- Personal ratings storage
- Cache persistence across restarts
- Watch history independent of Jellyfin
- Task data with proper querying

---

## 8. Caching & Data Strategy

### Current Cache Inventory

| Cache | Location | TTL | Max Size | Eviction | Persistence |
|-------|----------|-----|----------|----------|-------------|
| Mood/Similar/Library results | `recommendations.py:_cache` | 24h | **Unbounded** | None | None (lost on restart) |
| Search results | `recommendations.py:_search_cache` | 1h | **Unbounded** | None | None |
| Detail/Ratings results | `recommendations.py:_detail_cache` | 24h | **Unbounded** | None | None |
| IMDB/Letterboxd ratings | `ratings.py:_cache` | 3 days | **Unbounded** | None | None |
| Storage sizes | `system.py:_storage_cache` | 5min | 1 entry | Overwrite | None |
| Weather | `system.py:_weather_cache` | 15min | 1 entry | Overwrite | None |
| AllAnime search | `allanime.py:_cache` | 1h | **Unbounded** | None | None |
| YouTube search | `youtube.py:_cache` | 1h | **Unbounded** | None | None |
| Wiki KB | `wiki.py` (internal) | 24h | 1 copy | Overwrite | None |
| TMDB image proxy | `main.py` (HTTP headers) | 7 days | N/A | Browser/CDN | None |

### Problems

1. **Memory growth** — 5 unbounded caches that only grow. After weeks of usage:
   - 1,000 unique searches × ~30KB = 30MB in `_search_cache`
   - 500 detail pages × ~100KB = 50MB in `_detail_cache`
   - Total potential: 100-200MB of stale cache data

2. **No eviction** — Old entries never removed until app restart

3. **No persistence** — All caches lost on restart, causing a "cold start storm" where the first user triggers 100+ API calls

4. **No invalidation** — If a movie's rating changes, stale data served for 24h-3d

### Recommended Strategy

```python
# Replace dict caches with bounded LRU
from cachetools import TTLCache

_cache = TTLCache(maxsize=500, ttl=86400)      # 500 entries, 24h
_search_cache = TTLCache(maxsize=200, ttl=3600) # 200 entries, 1h
_detail_cache = TTLCache(maxsize=300, ttl=86400) # 300 entries, 24h
```

For persistence across restarts, add a simple SQLite cache layer:
```python
# Cache table: key TEXT PRIMARY KEY, value JSON, expires_at REAL
# On startup: load hot entries from SQLite
# On write: write-through to both memory and SQLite
```

---

## 9. Security Posture

### Risk Assessment

| Risk | Severity | Current State | Mitigation |
|------|----------|--------------|------------|
| **No authentication** | HIGH | Anyone on LAN/Tailscale can access all endpoints including Docker actions, file deletion, torrent adds | Add API key auth or basic auth middleware |
| **No rate limiting** | HIGH | Single user could hammer TMDB (429 ban) or trigger thousands of Letterboxd scrapes | Add `slowapi` rate limiting per IP |
| **Credentials in .env** | MEDIUM | API keys, qBit password in plaintext. In `.gitignore` but `.env` exists in repo | Already gitignored; acceptable for homelab |
| **No CORS middleware** | MEDIUM | Relies on Next.js rewrite proxy. If backend exposed directly, any origin can call it | Add `CORSMiddleware` with explicit origins |
| **File operations unauthed** | HIGH | `/api/files/delete`, `/api/files/move` accessible without auth | Path traversal is protected, but still risky |
| **Docker actions unauthed** | HIGH | `/api/docker/action` can restart/stop any container | Add auth middleware |
| **qBit SID race condition** | LOW | Two simultaneous requests could corrupt login state | Add threading lock |
| **No HTTPS** | MEDIUM | All traffic in plaintext on LAN | Tailscale provides encryption in transit; local LAN is trusted |

### Recommendations

For a homelab, full OAuth2 is overkill. A simple approach:

```python
# middleware: check X-API-Key header
API_KEY = settings.dashboard_api_key  # set in .env

@app.middleware("http")
async def auth_middleware(request, call_next):
    if request.url.path.startswith("/api/") and request.url.path != "/api/health":
        if request.headers.get("X-API-Key") != API_KEY:
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    return await call_next(request)
```

---

## 10. Code Quality & DX

### Strengths
- **Consistent file naming** — `page.tsx`, `page.module.scss` per route
- **No unnecessary abstractions** — direct, readable code
- **Proper git hygiene** — 39 meaningful commits with descriptive messages
- **Good documentation** — README.md, CLAUDE.md both comprehensive

### Concerns

| Issue | Location | Impact |
|-------|----------|--------|
| **`any` types in DataContext** | `DataContext.tsx:7-18` | No type safety for most-used data |
| **TorrentSearchModal duplicated** | `discover/page.tsx` + `[type]/[id]/page.tsx` | Bug fixes need to be applied twice |
| **Discover page is 782 lines** | `discover/page.tsx` | Hard to navigate; split into sub-components |
| **No tests** | Entire project | No pytest, no jest, no e2e tests |
| **No linting** | Entire project | No ESLint, no pylint, no formatting enforcement |
| **No CI/CD** | Project root | No GitHub Actions, no pre-commit hooks |
| **No Dockerfile** | Project root | Manual deployment only |
| **No systemd service** | Server | Backend/frontend must be manually started |

### Quick Wins for DX

1. **Add a `Makefile`** or `justfile` for common operations:
   ```makefile
   dev-backend:
       cd backend && source venv/bin/activate && uvicorn app.main:app --reload --port 8002

   dev-frontend:
       cd frontend && npm run dev

   build:
       cd frontend && npm run build

   restart:
       pkill -f uvicorn; pkill -f "next start"
       make dev-backend & make prod-frontend
   ```

2. **Add systemd services** for auto-start on boot:
   ```ini
   # /etc/systemd/system/jarvis-backend.service
   [Service]
   ExecStart=/home/animesh/projects/jarvis-dashboard/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8002
   WorkingDirectory=/home/animesh/projects/jarvis-dashboard/backend
   Restart=always
   ```

3. **Add `docker-compose.yml`** for portable deployment

---

## 11. Prioritized Improvement Roadmap

### Phase 1: Quick Wins (1-2 sessions)

| # | Task | Impact | Effort |
|---|------|--------|--------|
| 1 | **Add watchlist** — SQLite table + API endpoints + "Save" button on detail page | HIGH | Medium |
| 2 | **Add `cachetools.TTLCache`** — replace unbounded dicts, add `maxsize` | HIGH | Low |
| 3 | **Paginate library enrichment** — enrich 10 items at a time, load more on scroll | HIGH | Medium |
| 4 | **Add trailers** — fetch TMDB video key, embed YouTube iframe on detail page | MEDIUM | Low |
| 5 | **Pause polling when tab hidden** — `visibilitychange` listener in DataContext | MEDIUM | Low |
| 6 | **Add TMDB fetch-level caching** — LRU cache on `tmdb.fetch()` to deduplicate | MEDIUM | Low |

### Phase 2: Polish (2-3 sessions)

| # | Task | Impact | Effort |
|---|------|--------|--------|
| 7 | **Personal ratings** — 1-5 star rating stored in SQLite, shown on cards | MEDIUM | Medium |
| 8 | **Watched tracking** — sync with Jellyfin played status + manual toggle | MEDIUM | Medium |
| 9 | **Skeleton loading** — shimmer placeholders for discover/detail pages | MEDIUM | Low |
| 10 | **Extract shared components** — TorrentSearchModal, RecommendationCard | LOW | Low |
| 11 | **Cast filmography links** — click cast member → show their TMDB movies | LOW | Low |
| 12 | **Use `next/image`** — automatic WebP, srcSet, lazy loading for all posters | MEDIUM | Medium |

### Phase 3: Hardening (ongoing)

| # | Task | Impact | Effort |
|---|------|--------|--------|
| 13 | **Add API key auth** — simple middleware for all `/api/*` endpoints | HIGH | Low |
| 14 | **Add rate limiting** — `slowapi` to prevent TMDB ban | HIGH | Low |
| 15 | **Add systemd services** — auto-start on boot | MEDIUM | Low |
| 16 | **Add Docker Compose** — portable single-command deployment | MEDIUM | Medium |
| 17 | **Add health endpoint** — `/api/health` with dependency checks | LOW | Low |
| 18 | **Parallelize Jellyfin overview** — ThreadPoolExecutor for 11 calls | LOW | Low |

### Phase 4: Ambitious (future)

| # | Task | Impact | Effort |
|---|------|--------|--------|
| 19 | **"For You" personalized feed** — based on watch history + ratings | HIGH | High |
| 20 | **Custom lists** — create and curate movie collections | MEDIUM | Medium |
| 21 | **Collection awareness** — show trilogy/franchise grouping from TMDB | LOW | Medium |
| 22 | **Social sharing** — generate shareable movie recommendation cards | LOW | Medium |
| 23 | **Full accessibility pass** — ARIA, keyboard nav, screen reader support | MEDIUM | High |

---

## Appendix: File Reference

### Frontend
| File | Lines | Purpose |
|------|-------|---------|
| `app/page.tsx` | 146 | Dashboard overview |
| `app/discover/page.tsx` | 782 | Movie discovery (4 tabs) |
| `app/discover/[type]/[id]/page.tsx` | 536 | Movie/series detail |
| `app/system/page.tsx` | 161 | System monitoring |
| `app/docker/page.tsx` | 112 | Container management |
| `app/torrents/page.tsx` | 305 | qBittorrent UI |
| `app/media/page.tsx` | 405 | Jellyfin library |
| `app/tasks/page.tsx` | 605 | Kanban task board |
| `app/files/page.tsx` | 199 | File manager |
| `lib/DataContext.tsx` | 88 | Global polling state |
| `lib/api.ts` | 56 | Fetch wrapper |
| `styles/_variables.scss` | 108 | Design tokens |
| `styles/globals.scss` | 765 | Global styles + themes |

### Backend
| File | Lines | Purpose |
|------|-------|---------|
| `app/main.py` | 61 | FastAPI entry |
| `app/config.py` | 26 | Pydantic settings |
| `app/routers/recommendations.py` | 734 | Discovery endpoints |
| `app/routers/media.py` | 280 | Jellyfin proxy |
| `app/services/tmdb.py` | 330 | TMDB API client |
| `app/services/ratings.py` | 144 | IMDB + Letterboxd |
| `app/services/qbittorrent.py` | 168 | qBit client |
| `app/services/system.py` | 193 | System stats + bandwidth |
| `app/services/wiki.py` | 188 | Reddit wiki KB |
| `app/services/youtube.py` | 152 | YouTube full movie search |

---

*Generated by Claude Code audit — March 25, 2026*
