"""AllAnime scraping service — replicates ani-cli's approach in Python.

Searches allmanga.to / allanime.day for anime and extracts HLS/MP4 stream URLs.
"""

import concurrent.futures
import re
import time
import urllib.parse

import httpx

ALLANIME_API = "https://api.allanime.day/api"
ALLANIME_REFERER = "https://allmanga.to"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0"

_client = httpx.Client(timeout=15, headers={
    "User-Agent": USER_AGENT,
    "Referer": ALLANIME_REFERER,
    "Accept": "application/json",
})

# ani-cli's custom substitution cipher
HEX_DECODE_MAP = {
    "79": "A", "7a": "B", "7b": "C", "7c": "D", "7d": "E", "7e": "F",
    "7f": "G", "70": "H", "71": "I", "72": "J", "73": "K", "74": "L",
    "75": "M", "76": "N", "77": "O", "68": "P", "69": "Q", "6a": "R",
    "6b": "S", "6c": "T", "6d": "U", "6e": "V", "6f": "W", "60": "X",
    "61": "Y", "62": "Z",
    "59": "a", "5a": "b", "5b": "c", "5c": "d", "5d": "e", "5e": "f",
    "5f": "g", "50": "h", "51": "i", "52": "j", "53": "k", "54": "l",
    "55": "m", "56": "n", "57": "o", "48": "p", "49": "q", "4a": "r",
    "4b": "s", "4c": "t", "4d": "u", "4e": "v", "4f": "w", "40": "x",
    "41": "y", "42": "z",
    "08": "0", "09": "1", "0a": "2", "0b": "3", "0c": "4", "0d": "5",
    "0e": "6", "0f": "7", "00": "8", "01": "9",
    "15": "-", "16": ".", "67": "_", "46": "~", "02": ":", "17": "/",
    "07": "?", "1b": "#", "63": "[", "65": "]", "78": "@", "19": "!",
    "1c": "$", "1e": "&", "10": "(", "11": ")", "12": "*", "13": "+",
    "14": ",", "03": ";", "05": "=", "1d": "%",
}

# GraphQL queries (from ani-cli source)
SEARCH_GQL = """query( $search: SearchInput $limit: Int $page: Int $translationType: VaildTranslationTypeEnumType $countryOrigin: VaildCountryOriginEnumType ) { shows( search: $search limit: $limit page: $page translationType: $translationType countryOrigin: $countryOrigin ) { edges { _id name availableEpisodes __typename } } }"""

EPISODES_GQL = """query ($showId: String!) { show( _id: $showId ) { _id availableEpisodesDetail } }"""

EPISODE_EMBED_GQL = """query ($showId: String!, $translationType: VaildTranslationTypeEnumType!, $episodeString: String!) { episode( showId: $showId translationType: $translationType episodeString: $episodeString ) { episodeString sourceUrls } }"""

# Cache
_cache: dict = {}
_CACHE_TTL = 3600
_STREAM_CACHE_TTL = 900


def _gql(query: str, variables: dict) -> dict:
    """Execute a GraphQL query against the AllAnime API."""
    try:
        import json
        resp = _client.get(ALLANIME_API, params={
            "query": query,
            "variables": json.dumps(variables),
        })
        data = resp.json()
        return data.get("data", {})
    except Exception as e:
        print(f"[AllAnime] GraphQL error: {e}")
        return {}


def _decode_url(encoded: str) -> str:
    """Decode an AllAnime provider URL using the substitution cipher."""
    # Strip leading "--" prefix
    if encoded.startswith("--"):
        encoded = encoded[2:]
    # Split into pairs and decode
    chars = []
    for i in range(0, len(encoded), 2):
        pair = encoded[i:i + 2].lower()
        chars.append(HEX_DECODE_MAP.get(pair, ""))
    decoded = "".join(chars)
    # Replace /clock with /clock.json
    decoded = decoded.replace("/clock", "/clock.json")
    # Relative paths need the base domain
    if decoded.startswith("/"):
        decoded = f"https://allanime.day{decoded}"
    return decoded


def search(query: str, mode: str = "sub") -> list:
    """Search for anime titles. Returns list of {id, name, episodes_sub, episodes_dub}."""
    cache_key = f"search:{query.lower()}:{mode}"
    now = time.time()
    if cache_key in _cache and (now - _cache[cache_key]["ts"]) < _CACHE_TTL:
        return _cache[cache_key]["data"]

    variables = {
        "search": {"allowAdult": False, "allowUnknown": False, "query": query},
        "limit": 40,
        "page": 1,
        "translationType": mode,
        "countryOrigin": "ALL",
    }
    data = _gql(SEARCH_GQL, variables)
    edges = data.get("shows", {}).get("edges", [])

    results = []
    for edge in edges:
        eps = edge.get("availableEpisodes", {})
        if isinstance(eps, str):
            eps = {}
        results.append({
            "id": edge.get("_id", ""),
            "name": edge.get("name", ""),
            "episodes_sub": eps.get("sub", 0) if isinstance(eps, dict) else 0,
            "episodes_dub": eps.get("dub", 0) if isinstance(eps, dict) else 0,
        })

    _cache[cache_key] = {"data": results, "ts": now}
    return results


def get_episodes(show_id: str, mode: str = "sub") -> list:
    """Get episode list for a show. Returns sorted list of episode strings."""
    cache_key = f"episodes:{show_id}:{mode}"
    now = time.time()
    if cache_key in _cache and (now - _cache[cache_key]["ts"]) < _CACHE_TTL:
        return _cache[cache_key]["data"]

    data = _gql(EPISODES_GQL, {"showId": show_id})
    detail = data.get("show", {}).get("availableEpisodesDetail", {})
    if isinstance(detail, str):
        detail = {}

    episodes = detail.get(mode, [])
    if isinstance(episodes, list):
        # Sort numerically where possible
        def sort_key(ep):
            try:
                return float(ep)
            except (ValueError, TypeError):
                return float("inf")
        episodes = sorted(episodes, key=sort_key)
    else:
        episodes = []

    _cache[cache_key] = {"data": episodes, "ts": now}
    return episodes


def get_episode_sources(show_id: str, episode: str, mode: str = "sub") -> dict:
    """Get stream sources for an episode. Returns {sources: [...], subtitles: [...]}.

    Each source: {url, quality, type, provider}
    """
    cache_key = f"sources:{show_id}:{episode}:{mode}"
    now = time.time()
    if cache_key in _cache and (now - _cache[cache_key]["ts"]) < _STREAM_CACHE_TTL:
        return _cache[cache_key]["data"]

    data = _gql(EPISODE_EMBED_GQL, {
        "showId": show_id,
        "translationType": mode,
        "episodeString": episode,
    })

    source_urls = data.get("episode", {}).get("sourceUrls", [])
    if not source_urls:
        return {"sources": [], "subtitles": []}

    # Decode all provider URLs and fetch stream links in parallel
    providers = []
    for src in source_urls:
        raw_url = src.get("sourceUrl", "")
        source_name = src.get("sourceName", "")
        if not raw_url or not raw_url.startswith("--"):
            continue
        decoded = _decode_url(raw_url)
        if decoded:
            providers.append({"url": decoded, "name": source_name})

    # Fetch all provider links in parallel
    all_sources = []
    all_subtitles = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(_fetch_provider_links, p["url"], p["name"]): p for p in providers}
        for future in concurrent.futures.as_completed(futures):
            try:
                sources, subs = future.result()
                all_sources.extend(sources)
                all_subtitles.extend(subs)
            except Exception:
                pass

    # Deduplicate subtitles
    seen_subs = set()
    unique_subs = []
    for sub in all_subtitles:
        if sub["url"] not in seen_subs:
            seen_subs.add(sub["url"])
            unique_subs.append(sub)

    # Sort sources: prefer higher quality
    def quality_sort(s):
        q = s.get("quality", "")
        m = re.search(r"(\d+)", q)
        return int(m.group(1)) if m else 0
    all_sources.sort(key=quality_sort, reverse=True)

    result = {"sources": all_sources, "subtitles": unique_subs}
    _cache[cache_key] = {"data": result, "ts": now}
    return result


def _fetch_provider_links(provider_url: str, provider_name: str) -> tuple:
    """Fetch and parse stream links from a decoded provider URL."""
    sources = []
    subtitles = []

    try:
        resp = _client.get(provider_url, headers={
            "User-Agent": USER_AGENT,
            "Referer": ALLANIME_REFERER,
        })
        text = resp.text
        # Clean up escape sequences
        text = text.replace("\\u002F", "/").replace("\\", "")

        # Try to parse as JSON
        try:
            data = resp.json()
        except Exception:
            data = {}

        # Extract subtitles
        if isinstance(data, dict):
            for sub in data.get("subtitles", []):
                if sub.get("src"):
                    subtitles.append({
                        "url": sub["src"],
                        "lang": sub.get("label", sub.get("lang", "Unknown")),
                    })

        # Extract links based on provider type
        links = data.get("links", []) if isinstance(data, dict) else []

        for link in links:
            url = link.get("link", "")
            if not url:
                continue

            resolutions = link.get("resolutionStr", "") or link.get("resolution", "")
            hls_raw = link.get("hls", False)
            mp4_raw = link.get("mp4", False)
            referrer = link.get("Referer", "") or link.get("referrer", "")

            # Determine stream type
            if hls_raw or "m3u8" in url or "master.m3u8" in url:
                stream_type = "hls"
            else:
                stream_type = "mp4"

            if resolutions and "," in str(resolutions):
                # Multiple resolutions embedded
                for res in str(resolutions).split(","):
                    sources.append({
                        "url": url,
                        "quality": res.strip(),
                        "type": stream_type,
                        "provider": provider_name,
                        "referrer": referrer,
                    })
            else:
                sources.append({
                    "url": url,
                    "quality": str(resolutions) if resolutions else "default",
                    "type": stream_type,
                    "provider": provider_name,
                    "referrer": referrer,
                })

    except Exception as e:
        print(f"[AllAnime] Provider fetch error ({provider_name}): {e}")

    return sources, subtitles


def check_availability(title: str) -> dict | None:
    """Check if a title is available on AllAnime. Returns best match or None."""
    results = search(title, "sub")
    if not results:
        results = search(title, "dub")
    if not results:
        return None

    title_lower = title.lower().strip()
    title_words = set(re.sub(r"[^\w\s]", "", title_lower).split())

    best = None
    best_score = -1

    for r in results:
        name_lower = r["name"].lower().strip()
        name_clean = re.sub(r"[^\w\s]", "", name_lower)
        name_words = set(name_clean.split())

        # Exact match
        if name_lower == title_lower or name_clean == re.sub(r"[^\w\s]", "", title_lower):
            return r

        score = 0
        # Full containment
        if title_lower in name_lower or name_lower in title_lower:
            score += 50
        # Word overlap ratio
        if title_words:
            overlap = len(title_words & name_words)
            score += (overlap / len(title_words)) * 40
        # Prefer entries with more episodes (likely the main series, not specials)
        total_eps = r["episodes_sub"] + r["episodes_dub"]
        if total_eps > 100:
            score += 15
        elif total_eps > 10:
            score += 8

        if score > best_score:
            best_score = score
            best = r

    # Also consider the entry with most episodes (often the main series has
    # a short/alternate name like "1P" for One Piece)
    if results:
        by_eps = max(results, key=lambda r: r["episodes_sub"] + r["episodes_dub"])
        top_eps = by_eps["episodes_sub"] + by_eps["episodes_dub"]
        best_eps = (best["episodes_sub"] + best["episodes_dub"]) if best else 0
        # If the top-episode entry has 5x+ more episodes, prefer it
        if top_eps > 0 and (not best or top_eps > best_eps * 5):
            return by_eps

    if best and best_score >= 30:
        return best

    return None
