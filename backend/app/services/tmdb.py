import concurrent.futures
import urllib.parse

import httpx

from app.config import settings

_client = httpx.Client(timeout=10, headers={
    "User-Agent": "JarvisDashboard/1.0",
    "Accept": "application/json",
})


def fetch(endpoint: str) -> dict:
    sep = "&" if "?" in endpoint else "?"
    url = f"{settings.tmdb_base}{endpoint}{sep}api_key={settings.tmdb_api_key}"
    try:
        resp = _client.get(url)
        return resp.json()
    except Exception as e:
        print(f"[TMDB] Error fetching {endpoint}: {e}")
        return {}


def search_similar(title: str) -> tuple[list, set]:
    tmdb_results = []
    seen_tmdb = set()

    movie_search = fetch(f"/search/movie?query={urllib.parse.quote(title)}")
    if movie_search.get("results"):
        movie_id = movie_search["results"][0].get("id")
        if movie_id:
            similar = fetch(f"/movie/{movie_id}/similar")
            for s in similar.get("results", [])[:15]:
                s_title = s.get("title", "")
                key = s_title.lower()
                if key and key not in seen_tmdb:
                    seen_tmdb.add(key)
                    year = (s.get("release_date") or "")[:4]
                    poster = f"https://image.tmdb.org/t/p/w500{s['poster_path']}" if s.get("poster_path") else ""
                    tmdb_results.append({
                        "title": s_title, "year": year, "type": "movie",
                        "description": (s.get("overview") or "")[:200],
                        "rating": str(round(s.get("vote_average", 0), 1)),
                        "poster": poster,
                        "tmdb_id": str(s.get("id", "")),
                        "torrent_query": f"{s_title} {year}".strip(),
                    })

    tv_search = fetch(f"/search/tv?query={urllib.parse.quote(title)}")
    if tv_search.get("results"):
        tv_id = tv_search["results"][0].get("id")
        if tv_id:
            similar = fetch(f"/tv/{tv_id}/similar")
            for s in similar.get("results", [])[:15]:
                s_title = s.get("name", "")
                key = s_title.lower()
                if key and key not in seen_tmdb:
                    seen_tmdb.add(key)
                    year = (s.get("first_air_date") or "")[:4]
                    poster = f"https://image.tmdb.org/t/p/w500{s['poster_path']}" if s.get("poster_path") else ""
                    tmdb_results.append({
                        "title": s_title, "year": year, "type": "series",
                        "description": (s.get("overview") or "")[:200],
                        "rating": str(round(s.get("vote_average", 0), 1)),
                        "poster": poster,
                        "tmdb_id": str(s.get("id", "")),
                        "torrent_query": f"{s_title} {year}".strip(),
                    })

    return tmdb_results, seen_tmdb


def enrich_with_posters(results: list, max_items: int = 20) -> list:
    def _fetch_poster(movie):
        m = dict(movie)
        if m.get("tmdb_id") and not m.get("poster"):
            try:
                t = "tv" if m.get("type") == "series" else "movie"
                data = fetch(f"/{t}/{m['tmdb_id']}")
                if data:
                    if data.get("poster_path"):
                        m["poster"] = f"https://image.tmdb.org/t/p/w300{data['poster_path']}"
                    if data.get("vote_average"):
                        m["rating"] = round(data["vote_average"], 1)
                    if data.get("overview") and not m.get("description"):
                        m["description"] = data["overview"][:150]
            except Exception:
                pass
        return m
    items = results[:max_items]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        return list(pool.map(_fetch_poster, items))


def get_recommendations_for_item(title: str, media_type: str = "movie") -> list:
    kind = "tv" if media_type in ("series", "tv") else "movie"
    search = fetch(f"/search/{kind}?query={urllib.parse.quote(title)}")
    if not search.get("results"):
        return []
    tmdb_id = search["results"][0].get("id")
    if not tmdb_id:
        return []
    recs = fetch(f"/{kind}/{tmdb_id}/recommendations")
    results = []
    for s in recs.get("results", [])[:10]:
        s_title = s.get("title") or s.get("name", "")
        year = (s.get("release_date") or s.get("first_air_date") or "")[:4]
        poster = f"https://image.tmdb.org/t/p/w300{s['poster_path']}" if s.get("poster_path") else ""
        s_type = "series" if kind == "tv" else "movie"
        results.append({
            "title": s_title, "year": year, "type": s_type,
            "description": (s.get("overview") or "")[:200],
            "rating": str(round(s.get("vote_average", 0), 1)),
            "poster": poster,
            "tmdb_id": str(s.get("id", "")),
            "torrent_query": f"{s_title} {year}".strip(),
            "genre_ids": s.get("genre_ids", []),
        })
    return results


def discover_by_genres(genre_ids: list, media_type: str = "movie", page: int = 1) -> list:
    kind = "tv" if media_type in ("series", "tv") else "movie"
    genres_str = ",".join(str(g) for g in genre_ids)
    data = fetch(f"/discover/{kind}?with_genres={genres_str}&sort_by=vote_average.desc&vote_count.gte=100&page={page}")
    results = []
    for s in data.get("results", [])[:20]:
        s_title = s.get("title") or s.get("name", "")
        year = (s.get("release_date") or s.get("first_air_date") or "")[:4]
        poster = f"https://image.tmdb.org/t/p/w300{s['poster_path']}" if s.get("poster_path") else ""
        s_type = "series" if kind == "tv" else "movie"
        results.append({
            "title": s_title, "year": year, "type": s_type,
            "description": (s.get("overview") or "")[:200],
            "rating": str(round(s.get("vote_average", 0), 1)),
            "poster": poster,
            "tmdb_id": str(s.get("id", "")),
            "torrent_query": f"{s_title} {year}".strip(),
            "genre_ids": s.get("genre_ids", []),
        })
    return results


def multi_search(query: str) -> list:
    data = fetch(f"/search/multi?query={urllib.parse.quote(query)}&include_adult=false")
    results = []
    for item in data.get("results", []):
        media_type = item.get("media_type", "")
        if media_type not in ("movie", "tv"):
            continue
        if media_type == "movie":
            title = item.get("title", "")
            year = (item.get("release_date") or "")[:4]
            rtype = "movie"
        else:
            title = item.get("name", "")
            year = (item.get("first_air_date") or "")[:4]
            rtype = "series"
        if not title:
            continue
        poster = f"https://image.tmdb.org/t/p/w500{item['poster_path']}" if item.get("poster_path") else ""
        results.append({
            "title": title, "year": year,
            "tmdb_id": str(item.get("id", "")),
            "type": rtype, "poster": poster,
            "rating": round(item.get("vote_average", 0), 1),
            "overview": (item.get("overview") or "")[:150],
        })
        if len(results) >= 20:
            break
    return results


def get_detail(tmdb_id: str, media_type: str = "movie") -> dict:
    kind = "tv" if media_type in ("tv", "series") else "movie"

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        f_details = pool.submit(fetch, f"/{kind}/{tmdb_id}")
        f_credits = pool.submit(fetch, f"/{kind}/{tmdb_id}/credits")
        f_similar = pool.submit(fetch, f"/{kind}/{tmdb_id}/recommendations")

    details = f_details.result()
    credits = f_credits.result()
    similar_data = f_similar.result()

    if not details or "id" not in details:
        return {"error": "Movie/series not found on TMDB"}

    title = details.get("title") or details.get("name") or ""
    release_date = details.get("release_date") or details.get("first_air_date") or ""
    year = release_date[:4] if release_date else ""

    director = ""
    for crew_member in credits.get("crew", []):
        if crew_member.get("job") == "Director":
            director = crew_member.get("name", "")
            break
    if not director and kind == "tv":
        creators = details.get("created_by", [])
        if creators:
            director = creators[0].get("name", "")

    cast = []
    for member in credits.get("cast", [])[:10]:
        photo = ""
        if member.get("profile_path"):
            photo = f"https://image.tmdb.org/t/p/w185{member['profile_path']}"
        cast.append({
            "name": member.get("name", ""),
            "character": member.get("character", ""),
            "photo": photo,
        })

    poster = f"https://image.tmdb.org/t/p/w500{details['poster_path']}" if details.get("poster_path") else ""
    backdrop = f"https://image.tmdb.org/t/p/w1280{details['backdrop_path']}" if details.get("backdrop_path") else ""

    genres = [g.get("name", "") for g in details.get("genres", [])]

    runtime = details.get("runtime") or 0
    if not runtime and kind == "tv":
        ert = details.get("episode_run_time", [])
        runtime = ert[0] if ert else 0

    similar_tmdb = []
    for s in similar_data.get("results", [])[:10]:
        s_title = s.get("title") or s.get("name") or ""
        s_date = s.get("release_date") or s.get("first_air_date") or ""
        s_year = s_date[:4] if s_date else ""
        s_poster = f"https://image.tmdb.org/t/p/w500{s['poster_path']}" if s.get("poster_path") else ""
        s_type = "tv" if s.get("name") and not s.get("title") else "movie"
        similar_tmdb.append({
            "title": s_title, "year": s_year,
            "tmdb_id": str(s.get("id", "")),
            "poster": s_poster,
            "rating": round(s.get("vote_average", 0), 1),
            "type": s_type,
        })

    return {
        "title": title, "year": year,
        "overview": details.get("overview", ""),
        "poster": poster, "backdrop": backdrop,
        "genres": genres, "runtime": runtime,
        "rating": round(details.get("vote_average", 0), 1),
        "vote_count": details.get("vote_count", 0),
        "cast": cast, "director": director,
        "tagline": details.get("tagline", ""),
        "status": details.get("status", ""),
        "tmdb_id": str(tmdb_id), "type": kind,
        "torrent_query": f"{title} {year}".strip(),
        "similar_tmdb": similar_tmdb,
    }


def get_trending(time_window: str = "week") -> list:
    results = []
    seen = set()

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        f_movies = pool.submit(fetch, f"/trending/movie/{time_window}")
        f_tv = pool.submit(fetch, f"/trending/tv/{time_window}")

    for item in f_movies.result().get("results", [])[:20]:
        title = item.get("title", "")
        key = title.lower()
        if key and key not in seen:
            seen.add(key)
            year = (item.get("release_date") or "")[:4]
            poster = f"https://image.tmdb.org/t/p/w300{item['poster_path']}" if item.get("poster_path") else ""
            results.append({
                "title": title, "year": year, "type": "movie",
                "description": (item.get("overview") or "")[:200],
                "rating": str(round(item.get("vote_average", 0), 1)),
                "poster": poster,
                "tmdb_id": str(item.get("id", "")),
                "torrent_query": f"{title} {year}".strip(),
                "genre_ids": item.get("genre_ids", []),
            })

    for item in f_tv.result().get("results", [])[:20]:
        title = item.get("name", "")
        key = title.lower()
        if key and key not in seen:
            seen.add(key)
            year = (item.get("first_air_date") or "")[:4]
            poster = f"https://image.tmdb.org/t/p/w300{item['poster_path']}" if item.get("poster_path") else ""
            results.append({
                "title": title, "year": year, "type": "series",
                "description": (item.get("overview") or "")[:200],
                "rating": str(round(item.get("vote_average", 0), 1)),
                "poster": poster,
                "tmdb_id": str(item.get("id", "")),
                "torrent_query": f"{title} {year}".strip(),
                "genre_ids": item.get("genre_ids", []),
            })

    return results
