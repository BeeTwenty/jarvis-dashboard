# Jarvis Dashboard — Architecture

A self-hosted homelab dashboard combining infrastructure monitoring, container management, media discovery, and automated torrent downloads.

---

## System Overview

```mermaid
graph TB
    subgraph Client["Browser (Chrome / any device)"]
        UI["Next.js Frontend :3000"]
    end

    subgraph Server["Ubuntu Server (jackal)"]
        FE["Next.js (App Router)"]
        BE["FastAPI Backend :8002"]
        DB[(SQLite — jarvis.db)]
        JSON[(tasks.json)]
        DOCK["/var/run/docker.sock"]
    end

    subgraph External["External APIs"]
        TMDB["TMDB API"]
        OMDB["OMDb API"]
        WTTR["wttr.in"]
        WIKI["Reddit Wiki"]
        ANIME["AllAnime GraphQL"]
        APIBAY["Apibay (torrents)"]
        YT["YouTube"]
    end

    subgraph Local["Local Services"]
        JF["Jellyfin :8096"]
        QB["qBittorrent :8080"]
        DOCKER["Docker Engine"]
    end

    UI -->|"/api/* rewrite"| FE
    FE -->|"proxy"| BE
    BE --> JF
    BE --> QB
    BE --> DOCK --> DOCKER
    BE --> TMDB
    BE --> OMDB
    BE --> WTTR
    BE --> WIKI
    BE --> ANIME
    BE --> APIBAY
    BE --> YT
    BE --> DB
    BE --> JSON
```

---

## Request Flow

Every user request follows the same path: browser to Next.js, proxied to FastAPI, routed to the right service.

```mermaid
sequenceDiagram
    participant B as Browser
    participant N as Next.js :3000
    participant F as FastAPI :8002
    participant S as Service Layer
    participant C as Cache (in-memory)
    participant E as External API

    B->>N: GET /api/system
    N->>F: Proxy rewrite (next.config.ts)
    F->>S: Router calls Service
    S->>C: Check TTL cache
    alt Cache hit
        C-->>S: Return cached data
    else Cache miss
        S->>E: HTTP call (httpx)
        E-->>S: Response
        S->>C: Store with TTL
    end
    S-->>F: Processed result
    F-->>N: JSON response
    N-->>B: Render UI
```

---

## Frontend Architecture

```mermaid
graph TB
    subgraph Layout["App Shell"]
        TH["ThemeProvider (dark/light)"]
        DP["DataProvider (polling hub)"]
        NAV["Sidebar + MobileNav"]
        TOAST["Toast Container"]
    end

    subgraph Pages["Pages (App Router)"]
        HOME["/ — Overview"]
        SYS["/system — Stats"]
        DOCK["/docker — Containers"]
        TOR["/torrents — Downloads"]
        MED["/media — Jellyfin"]
        DISC["/discover — Movies & TV"]
        DET["/discover/[type]/[id] — Detail"]
        FILES["/files — File Browser"]
        TASKS["/tasks — Kanban Board"]
    end

    subgraph Lib["lib/"]
        API["api.ts — fetch wrapper"]
        DC["DataContext.tsx — polling"]
        TC["ThemeContext.tsx"]
        TOASTL["toast.ts"]
    end

    TH --> TC
    DP --> DC
    DC -->|"fast: 5s"| API
    DC -->|"slow: 5min"| API
    Layout --> Pages
    Pages --> Lib
```

### Polling Cycles

```mermaid
graph LR
    subgraph Fast["Fast Poll (every 5s)"]
        F1["System stats"]
        F2["Docker containers"]
        F3["Torrent transfers"]
        F4["Jellyfin sessions"]
        F5["Process list"]
        F6["Bandwidth history"]
    end

    subgraph Slow["Slow Poll (every 5min)"]
        S1["Storage sizes (du)"]
        S2["Weather (wttr.in)"]
    end

    VIS{"Tab visible?"}
    VIS -->|Yes| Fast
    VIS -->|Yes| Slow
    VIS -->|No| PAUSE["Polling paused"]
```

- Uses `Promise.allSettled()` so one failed endpoint doesn't break the dashboard
- Tab visibility API pauses polling when the browser tab is hidden

---

## Backend Architecture

```mermaid
graph TB
    subgraph Routers["Routers (HTTP layer)"]
        R1["system.py"]
        R2["docker.py"]
        R3["torrents.py"]
        R4["media.py"]
        R5["recommendations.py"]
        R6["actions.py"]
        R7["files.py"]
        R8["streaming.py"]
        R9["tasks.py"]
        R10["watchlist.py"]
    end

    subgraph Services["Services (business logic)"]
        SV1["system.py"]
        SV2["docker.py"]
        SV3["qbittorrent.py"]
        SV4["jellyfin.py"]
        SV5["tmdb.py"]
        SV6["wiki.py"]
        SV7["ratings.py"]
        SV8["allanime.py"]
        SV9["youtube.py"]
        SV10["files.py"]
        SV11["tasks.py"]
        SV12["database.py"]
    end

    R1 --> SV1
    R2 --> SV2
    R3 --> SV3
    R4 --> SV4
    R5 --> SV5
    R5 --> SV6
    R5 --> SV7
    R5 --> SV8
    R8 --> SV8
    R8 --> SV9
    R7 --> SV10
    R9 --> SV11
    R10 --> SV12
    R6 --> SV4
    R6 --> SV3
    R6 --> SV2
```

### Router to External Service Mapping

```mermaid
graph LR
    subgraph Services
        SYS["system"]
        DOCK["docker"]
        QBIT["qbittorrent"]
        JELLY["jellyfin"]
        TMDB["tmdb"]
        WIKI["wiki"]
        RATE["ratings"]
        ANIME["allanime"]
    end

    subgraph External
        PS["psutil / subprocess"]
        DS["/var/run/docker.sock"]
        QB["qBit :8080"]
        JF["Jellyfin :8096"]
        TA["api.themoviedb.org"]
        RW["reddit.com wiki"]
        OM["omdbapi.com"]
        AA["api.allanime.day"]
        WT["wttr.in"]
        AB["apibay.org"]
    end

    SYS --> PS
    SYS --> WT
    DOCK --> DS
    QBIT --> QB
    QBIT --> AB
    JELLY --> JF
    TMDB --> TA
    WIKI --> RW
    RATE --> OM
    ANIME --> AA
```

---

## Data Storage

```mermaid
graph TB
    subgraph InMemory["In-Memory Caches (TTL)"]
        C1["TMDB fetch — 1h, 500 entries"]
        C2["Recommendations — 24h, 200 entries"]
        C3["Detail pages — 24h, 300 entries"]
        C4["Search results — 1h, 200 entries"]
        C5["Storage sizes — 5min"]
        C6["Weather — 15min"]
        C7["AllAnime — 1h"]
        C8["Ratings (OMDb) — 3 days"]
        C9["Bandwidth — 30min rolling, 360 pts"]
    end

    subgraph Persistent["Persistent Storage"]
        DB["jarvis.db (SQLite WAL)\n- watchlist table"]
        TK["tasks.json\n- Kanban board data\n- Atomic writes"]
    end

    subgraph ClientSide["Browser (localStorage)"]
        LS1["jarvis-theme — dark/light"]
    end
```

---

## Media Discovery Flow

The most complex subsystem — aggregates multiple sources for movie/TV recommendations.

```mermaid
graph TB
    USER["User picks a mood"] --> MOOD["GET /api/recommendations/mood"]

    MOOD --> GENRES["Map mood to TMDB genre IDs"]
    MOOD --> WIKISEARCH["Search Reddit wiki KB"]

    GENRES --> TMDBD["TMDB discover by genres"]
    WIKISEARCH --> WIKIRESULTS["Wiki matches"]

    TMDBD --> MERGE["Merge + deduplicate"]
    WIKIRESULTS --> MERGE

    MERGE --> ENRICH["ThreadPoolExecutor (8 workers)\nenrich with posters & ratings"]

    ENRICH --> LIBCHECK["Check Jellyfin library\n(in_library flag)"]

    LIBCHECK --> RESPONSE["Return enriched results"]
```

```mermaid
graph TB
    DET["Detail Page /discover/movie/12345"] --> API["GET /api/recommendations/detail"]

    API --> PARALLEL["Parallel fetch (ThreadPool)"]

    PARALLEL --> P1["TMDB details + credits"]
    PARALLEL --> P2["TMDB similar titles"]
    PARALLEL --> P3["TMDB recommendations"]
    PARALLEL --> P4["External ratings"]
    PARALLEL --> P5["Jellyfin library check"]

    P4 --> OMDB["OMDb (IMDB rating)"]
    P4 --> LB["Letterboxd (scrape)"]

    P1 --> RESULT["Aggregated detail response"]
    P2 --> RESULT
    P3 --> RESULT
    P4 --> RESULT
    P5 --> RESULT
```

---

## Image Proxying

TMDB and Jellyfin images are proxied through the backend so Tailscale clients can resolve them.

```mermaid
sequenceDiagram
    participant B as Browser
    participant BE as Backend :8002
    participant TMDB as image.tmdb.org
    participant JF as Jellyfin :8096

    B->>BE: GET /api/tmdb-image/w500/abc.jpg
    BE->>TMDB: GET /t/p/w500/abc.jpg
    TMDB-->>BE: Image bytes
    BE-->>B: Image (Cache-Control: 7d)

    B->>BE: GET /api/jellyfin-media/poster/item-id
    BE->>JF: GET /Items/item-id/Images/Primary
    JF-->>BE: Image bytes
    BE-->>B: Image (Cache-Control: 1d)
```

---

## Torrent Workflow

```mermaid
sequenceDiagram
    participant U as User
    participant FE as Frontend
    participant BE as Backend
    participant AB as Apibay
    participant QB as qBittorrent

    U->>FE: Search "movie name"
    FE->>BE: GET /api/torrent-search?q=...
    BE->>AB: Search torrents
    AB-->>BE: Results (name, size, seeds)
    BE-->>FE: Sorted results
    FE-->>U: Display results

    U->>FE: Click "Add"
    FE->>BE: POST /api/torrent-add (magnet, category)
    BE->>QB: Add magnet link
    Note over BE,QB: Auto-detect category (movie/series)<br/>Override save path per category
    QB-->>BE: OK
    BE-->>FE: Success
```

---

## Task Kanban Flow

```mermaid
graph LR
    subgraph Columns
        TODO["To Do"]
        IP["In Progress"]
        DONE["Done"]
    end

    TODO -->|"drag & drop"| IP
    IP -->|"drag & drop"| DONE
    TODO -->|"drag & drop"| DONE

    subgraph Storage
        JSON["tasks.json\n(atomic writes)"]
    end

    subgraph Features
        F1["Date-based views"]
        F2["Auto-migrate incomplete tasks"]
        F3["Entity linking (TMDB)"]
        F4["Export as bullet list"]
        F5["Inline edit"]
    end

    Columns --> JSON
```

---

## Deployment Topology

```mermaid
graph TB
    subgraph Network["Home Network"]
        subgraph Server["Ubuntu Server — jackal (192.168.0.2)"]
            NEXT["Next.js :3000"]
            FAST["FastAPI :8002"]
            JF["Jellyfin :8096"]
            QB["qBit :8080"]
            DOCK["Docker Engine"]
            TS["Tailscale"]
        end

        subgraph Client["Windows PC / Laptop"]
            CHROME["Chrome Browser"]
        end
    end

    CHROME -->|"HTTP :3000"| NEXT
    NEXT -->|"rewrite"| FAST
    FAST --> JF
    FAST --> QB
    FAST --> DOCK

    subgraph Internet["Internet"]
        TMDB["TMDB"]
        OMDB["OMDb"]
        WTTR["wttr.in"]
        REDDIT["Reddit"]
    end

    FAST --> Internet
```

---

## Tech Stack Summary

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16, React 19, TypeScript, SCSS Modules |
| Backend | FastAPI, Python 3.12, Pydantic, httpx |
| Database | SQLite (WAL mode) for watchlist |
| File storage | JSON (tasks), in-memory TTL caches |
| Icons | Lucide React |
| Media | Jellyfin, TMDB, OMDb, Reddit Wiki |
| Torrents | qBittorrent, Apibay |
| Containers | Docker (CLI via socket) |
| Weather | wttr.in |
| Networking | Tailscale (remote access) |

---

## Key Design Decisions

- **No database for most data** — system stats, docker, torrents are all real-time. Only watchlist (SQLite) and tasks (JSON) need persistence.
- **In-memory TTL caching** — avoids redundant external API calls. Each service manages its own cache.
- **Image proxying** — required for Tailscale clients that can't resolve CDN domains directly.
- **Promise.allSettled()** — frontend resilience. One broken API doesn't crash the dashboard.
- **ThreadPoolExecutor** — parallel TMDB enrichment (posters, ratings) keeps discovery pages fast.
- **Atomic file writes** — tasks.json uses tempfile + rename to prevent corruption.
- **No auth** — homelab-only, not exposed to the internet.
