import concurrent.futures
import random
import re
import time
import urllib.parse

import httpx

from fastapi import APIRouter

from app.services import tmdb as tmdb_svc
from app.services import wiki as wiki_svc
from app.services import jellyfin as jellyfin_svc

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])

_cache: dict = {}
_CACHE_TTL = 86400
_search_cache: dict = {}
_SEARCH_TTL = 3600
_detail_cache: dict = {}
_DETAIL_TTL = 86400

MOOD_CATEGORY_MAP = {
    "feel-good": ["Comedy", "Romance", "Animation", "Adventure", "Family", "Musical"],
    "thriller": ["Thriller", "Crime", "Suspense", "Psychological Thriller", "Crime Thriller"],
    "mind-bending": ["Mystery", "Sci-Fi", "Psychological", "Puzzle", "Science Fiction", "Surreal"],
    "comfort": ["Comedy", "Romance", "Animation", "Family", "Adventure", "Feel-Good"],
    "dark": ["Crime", "Thriller", "Drama", "Noir", "Psychological", "Dark Comedy"],
    "funny": ["Comedy", "Dark Comedy", "Parody", "Satire", "Slapstick"],
    "romantic": ["Romance", "Romantic Comedy", "Rom-Com", "Drama", "Love"],
    "action-packed": ["Action", "Military", "Martial Arts", "Heist", "Spy", "War"],
    "sci-fi": ["Sci-Fi", "Science Fiction", "Cyberpunk", "Space", "Dystopia", "Time Travel"],
    "horror": ["Horror", "Slasher", "Supernatural", "Zombie", "Gothic", "Psychological Horror"],
    "documentary": ["Documentary", "True Crime", "History", "Biography"],
    "animated": ["Animation", "Animated", "Anime", "Pixar", "Disney"],
}

_TMDB_GENRE_MAP = {
    "action": 28, "adventure": 12, "animation": 16, "comedy": 35, "crime": 80,
    "documentary": 99, "drama": 18, "family": 10751, "fantasy": 14, "history": 36,
    "horror": 27, "music": 10402, "mystery": 9648, "romance": 10749,
    "science fiction": 878, "sci-fi": 878, "thriller": 53, "war": 10752, "western": 37,
}


def _match_categories(keywords: list, categories_dict: dict) -> list:
    matched = []
    for kw in keywords:
        kw_lower = kw.lower()
        for cat_name in categories_dict:
            if cat_name in matched:
                continue
            if kw_lower in cat_name.lower() or cat_name.lower() in kw_lower:
                matched.append(cat_name)
    return matched


def _google_search_titles(query: str, num: int = 10) -> list:
    results = []
    seen = set()
    try:
        url = f"https://www.google.com/search?q={urllib.parse.quote(query + ' site:reddit.com')}&num={num}"
        resp = httpx.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml",
        }, timeout=15)
        html_text = resp.text
        title_year_re = re.findall(r'([A-Z][A-Za-z0-9\s\':&,!.\-]{2,40})\s*\((\d{4})\)', html_text)
        for name, year in title_year_re:
            name = name.strip().rstrip(" -\u2013,.")
            if len(name) < 2 or name.lower() in seen:
                continue
            if any(skip in name.lower() for skip in ["reddit", "imdb", "http", "edit", "update", "thread", "spoiler", "anyone", "looking for", "suggest", "recommend", "google", "search"]):
                continue
            seen.add(name.lower())
            results.append({"title": name, "year": year, "type": "movie", "category": "", "tmdb_id": "", "tmdb_url": "", "torrent_query": f"{name} {year}".strip()})
    except Exception:
        pass
    return results


@router.get("/mood")
def get_mood(mood: str = ""):
    if not mood:
        return {"error": "Missing mood parameter"}
    cache_key = f"mood:{mood}"
    now = time.time()
    if cache_key in _cache and (now - _cache[cache_key]["ts"]) < _CACHE_TTL:
        return _cache[cache_key]["data"]

    categories, _ = wiki_svc.get_kb()
    mood_lower = mood.lower().strip()
    cat_keywords = MOOD_CATEGORY_MAP.get(mood_lower, [mood_lower])
    matched_cats = _match_categories(cat_keywords, categories)

    if not matched_cats:
        mood_words = mood_lower.replace("-", " ").split()
        for word in mood_words:
            if len(word) < 3:
                continue
            for cat_name in categories:
                if word in cat_name.lower() and cat_name not in matched_cats:
                    matched_cats.append(cat_name)

    all_movies = []
    seen = set()
    for cat_name in matched_cats:
        for movie in categories.get(cat_name, []):
            key = movie["title"].lower()
            if key not in seen:
                seen.add(key)
                all_movies.append(movie)

    random.shuffle(all_movies)
    results = all_movies[:20]

    if not results:
        results = _google_search_titles(f"{mood} movies recommendations reddit")[:20]

    results = tmdb_svc.enrich_with_posters(results, max_items=20)

    result = {"mood": mood, "matched_categories": matched_cats, "results": results}
    _cache[cache_key] = {"data": result, "ts": now}
    return result


@router.get("/similar")
def get_similar(title: str = ""):
    if not title:
        return {"error": "Missing title parameter"}
    cache_key = f"similar:{title.lower().strip()}"
    now = time.time()
    if cache_key in _cache and (now - _cache[cache_key]["ts"]) < _CACHE_TTL:
        return _cache[cache_key]["data"]

    tmdb_results, seen_tmdb = tmdb_svc.search_similar(title)
    categories, top100 = wiki_svc.get_kb()
    title_lower = title.lower().strip()

    found_categories = []
    for cat_name, movies in categories.items():
        for movie in movies:
            if movie["title"].lower() == title_lower or title_lower in movie["title"].lower():
                if cat_name not in found_categories:
                    found_categories.append(cat_name)
    for movie in top100:
        if movie["title"].lower() == title_lower or title_lower in movie["title"].lower():
            if "Trending" not in found_categories:
                found_categories.append("Trending")

    wiki_movies = []
    seen = {title_lower} | seen_tmdb
    for cat_name in found_categories:
        for movie in categories.get(cat_name, []):
            key = movie["title"].lower()
            if key not in seen:
                seen.add(key)
                wiki_movies.append(movie)

    random.shuffle(wiki_movies)
    results = tmdb_results + wiki_movies

    if not results:
        results = _google_search_titles(f"movies similar to {title} recommendations reddit")[:20]

    results = results[:30]
    result = {"query": title, "matched_categories": found_categories, "results": results}
    _cache[cache_key] = {"data": result, "ts": now}
    return result


@router.get("/library")
def get_library():
    cache_key = "library"
    now = time.time()
    if cache_key in _cache and (now - _cache[cache_key]["ts"]) < _CACHE_TTL:
        return _cache[cache_key]["data"]

    genres = []
    library_titles = set()
    library_items_raw = []
    try:
        users_data = jellyfin_svc.request("/Users")
        user_id = ""
        if isinstance(users_data, list) and users_data:
            user_id = users_data[0].get("Id", "")
        if user_id:
            movies = jellyfin_svc.request(f"/Users/{user_id}/Items?IncludeItemTypes=Movie&Limit=50&SortBy=DatePlayed&SortOrder=Descending&Recursive=true")
            if isinstance(movies, dict) and "Items" in movies:
                for item in movies["Items"]:
                    name = item.get("Name", "")
                    library_titles.add(name.lower())
                    item_genres = item.get("Genres", [])
                    for g in item_genres:
                        genres.append(g)
                    library_items_raw.append({"title": name, "type": "movie", "genres": item_genres})
            series = jellyfin_svc.request(f"/Users/{user_id}/Items?IncludeItemTypes=Series&Limit=30&SortBy=DatePlayed&SortOrder=Descending&Recursive=true")
            if isinstance(series, dict) and "Items" in series:
                for item in series["Items"]:
                    name = item.get("Name", "")
                    library_titles.add(name.lower())
                    item_genres = item.get("Genres", [])
                    for g in item_genres:
                        genres.append(g)
                    library_items_raw.append({"title": name, "type": "series", "genres": item_genres})
    except Exception:
        pass

    if not genres:
        genres = ["Action", "Drama", "Thriller", "Comedy", "Sci-Fi"]

    genre_count = {}
    for g in genres:
        genre_count[g] = genre_count.get(g, 0) + 1
    top_genres = sorted(genre_count.keys(), key=lambda g: genre_count[g], reverse=True)[:5]

    def _enrich_library_item(item):
        import urllib.parse as up
        kind = "tv" if item["type"] == "series" else "movie"
        search = tmdb_svc.fetch(f"/search/{kind}?query={up.quote(item['title'])}")
        if search.get("results"):
            first = search["results"][0]
            poster = f"https://image.tmdb.org/t/p/w300{first['poster_path']}" if first.get("poster_path") else ""
            year = (first.get("release_date") or first.get("first_air_date") or "")[:4]
            return {
                "title": item["title"], "year": year, "type": item["type"],
                "poster": poster, "tmdb_id": str(first.get("id", "")),
                "rating": str(round(first.get("vote_average", 0), 1)),
                "description": (first.get("overview") or "")[:150],
                "genres": item["genres"],
                "torrent_query": f"{item['title']} {year}".strip(),
            }
        return {
            "title": item["title"], "year": "", "type": item["type"],
            "poster": "", "tmdb_id": "", "rating": "", "description": "",
            "genres": item["genres"], "torrent_query": item["title"],
        }

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        library_items = list(pool.map(_enrich_library_item, library_items_raw[:40]))

    sample_items = random.sample(library_items_raw, min(6, len(library_items_raw)))
    suggestions = []
    seen = set(library_titles)

    def _get_recs(item):
        return tmdb_svc.get_recommendations_for_item(item["title"], item["type"])

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        all_recs = list(pool.map(_get_recs, sample_items))

    for recs in all_recs:
        for rec in recs:
            key = rec["title"].lower()
            if key not in seen:
                seen.add(key)
                suggestions.append(rec)

    tmdb_genre_ids = []
    for g in top_genres[:3]:
        g_lower = g.lower()
        if g_lower in _TMDB_GENRE_MAP:
            tmdb_genre_ids.append(_TMDB_GENRE_MAP[g_lower])

    if tmdb_genre_ids:
        discover_results = tmdb_svc.discover_by_genres(tmdb_genre_ids, "movie")
        for rec in discover_results:
            key = rec["title"].lower()
            if key not in seen:
                seen.add(key)
                suggestions.append(rec)

    random.shuffle(suggestions)
    suggestions = suggestions[:30]

    result = {
        "genres": top_genres,
        "library_count": len(library_titles),
        "library_items": library_items,
        "suggestions": suggestions,
    }
    _cache[cache_key] = {"data": result, "ts": now}
    return result


@router.get("/trending")
def get_trending(time_window: str = "week"):
    if time_window not in ("day", "week"):
        time_window = "week"
    cache_key = f"trending:{time_window}"
    now = time.time()
    if cache_key in _cache and (now - _cache[cache_key]["ts"]) < _CACHE_TTL:
        return _cache[cache_key]["data"]

    results = tmdb_svc.get_trending(time_window)
    result = {"results": results, "time_window": time_window}
    _cache[cache_key] = {"data": result, "ts": now}
    return result


@router.get("/categories")
def get_categories():
    cache_key = "categories_list"
    now = time.time()
    if cache_key in _cache and (now - _cache[cache_key]["ts"]) < _CACHE_TTL:
        return _cache[cache_key]["data"]

    categories, _ = wiki_svc.get_kb()
    cat_list = [{"name": name, "count": len(movies)} for name, movies in sorted(categories.items())]
    result = {"categories": cat_list, "total_movies": sum(c["count"] for c in cat_list)}
    _cache[cache_key] = {"data": result, "ts": now}
    return result


@router.get("/autocomplete")
def autocomplete(q: str = ""):
    if not q or len(q) < 2:
        return {"results": []}
    categories, top100 = wiki_svc.get_kb()
    query_lower = q.lower().strip()
    results = []
    seen = set()
    for cat_name, movies in categories.items():
        for movie in movies:
            key = movie["title"].lower()
            if query_lower in key and key not in seen:
                seen.add(key)
                results.append({
                    "title": movie["title"],
                    "year": movie.get("year", ""),
                    "tmdb_id": movie.get("tmdb_id", ""),
                    "type": movie.get("type", "movie"),
                })
            if len(results) >= 10:
                break
        if len(results) >= 10:
            break
    if len(results) < 10:
        for movie in top100:
            key = movie["title"].lower()
            if query_lower in key and key not in seen:
                seen.add(key)
                results.append({
                    "title": movie["title"],
                    "year": movie.get("year", ""),
                    "tmdb_id": movie.get("tmdb_id", ""),
                    "type": movie.get("type", "movie"),
                })
            if len(results) >= 10:
                break
    return {"results": results[:10]}


@router.get("/search")
def search(q: str = ""):
    if not q or len(q) < 2:
        return {"results": []}
    cache_key = f"search:{q.lower().strip()}"
    now = time.time()
    if cache_key in _search_cache and (now - _search_cache[cache_key]["ts"]) < _SEARCH_TTL:
        return _search_cache[cache_key]["data"]
    results = tmdb_svc.multi_search(q)
    result = {"results": results}
    _search_cache[cache_key] = {"data": result, "ts": now}
    return result


@router.get("/detail")
def get_detail(tmdb_id: str = "", type: str = "movie"):
    if not tmdb_id:
        return {"error": "Missing tmdb_id parameter"}
    cache_key = f"detail:{type}:{tmdb_id}"
    now = time.time()
    if cache_key in _detail_cache and (now - _detail_cache[cache_key]["ts"]) < _DETAIL_TTL:
        return _detail_cache[cache_key]["data"]

    result = tmdb_svc.get_detail(tmdb_id, type)

    # Add similar from wiki KB
    if "error" not in result:
        categories, _ = wiki_svc.get_kb()
        title_lower = result["title"].lower()
        found_cats = []
        for cat_name, movies in categories.items():
            for movie in movies:
                if movie["title"].lower() == title_lower:
                    found_cats.append(cat_name)
                    break

        seen_kb = {title_lower}
        for s in result.get("similar_tmdb", []):
            seen_kb.add(s["title"].lower())

        similar_kb_raw = []
        for cat_name in found_cats:
            for movie in categories.get(cat_name, []):
                key = movie["title"].lower()
                if key not in seen_kb:
                    seen_kb.add(key)
                    similar_kb_raw.append(movie)
                if len(similar_kb_raw) >= 10:
                    break
            if len(similar_kb_raw) >= 10:
                break

        def _fetch_kb_poster(movie):
            m = dict(movie)
            if m.get("tmdb_id"):
                try:
                    t = "tv" if m.get("type") == "series" else "movie"
                    data = tmdb_svc.fetch(f"/{t}/{m['tmdb_id']}")
                    if data and data.get("poster_path"):
                        m["poster"] = f"https://image.tmdb.org/t/p/w500{data['poster_path']}"
                    if data and data.get("vote_average"):
                        m["rating"] = round(data["vote_average"], 1)
                except Exception:
                    pass
            return m

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
            result["similar_kb"] = list(pool.map(_fetch_kb_poster, similar_kb_raw))

    _detail_cache[cache_key] = {"data": result, "ts": now}
    return result
