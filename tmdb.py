from __future__ import annotations

import os
import streamlit as st
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

load_dotenv()

_BASE = "https://api.themoviedb.org/3"
_API_KEY = os.getenv("TMDB_API_KEY", "")


def _get(path: str, params: dict | None = None) -> dict:
    """Send a TMDB request and raise if the API returns an error."""
    p = {"api_key": _API_KEY, **(params or {})}
    r = requests.get(_BASE + path, params=p, timeout=10)
    r.raise_for_status()
    return r.json()


@st.cache_data(show_spinner=False)
def search_movies(query: str, pages: int = 2) -> list[dict]:
    """Search TMDB, fetching up to the requested number of pages."""
    results = []
    for page in range(1, pages + 1):
        data = _get("/search/movie", {"query": query, "page": page, "include_adult": "false"})
        results.extend(data.get("results", []))
        if page >= data.get("total_pages", 1):
            break
    return results


@st.cache_data(show_spinner=False)
def get_movie_details(movie_id: int) -> dict:
    """Fetch a movie's details and keywords."""
    return _get(f"/movie/{movie_id}", {"append_to_response": "keywords"})


def fetch_all_details(movies: list[dict]) -> list[dict]:
    """Fetch details concurrently; fall back to search data if a request fails.

    Results stay in the same order as `movies`, even when requests finish
    in a different order.
    """
    results = [None] * len(movies)
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(get_movie_details, m["id"]): i
                   for i, m in enumerate(movies)}
        for future in as_completed(futures):
            idx = futures[future]
            try:
                results[idx] = future.result()
            except Exception:
                results[idx] = movies[idx]
    return results


def build_dataframe(details: list[dict]) -> "pd.DataFrame":
    """Extract the movie fields used by the app and scoring functions.

    TMDB may return keywords under either `keywords` or `results`, depending
    on the response shape.
    """
    import pandas as pd

    rows = []
    for d in details:
        if d is None:
            continue
        rd = d.get("release_date") or ""
        try:
            year = int(rd[:4]) if len(rd) >= 4 else None
        except ValueError:
            year = None

        genres = [g["name"] for g in d.get("genres", [])]

        kw_data = d.get("keywords", {})
        kw_list = kw_data.get("keywords") or kw_data.get("results") or []
        keywords = [k["name"] for k in kw_list]

        rows.append({
            "id": d.get("id"),
            "title": d.get("title", "Unknown"),
            "year": year,
            "vote_average": d.get("vote_average"),
            "vote_count": d.get("vote_count", 0),
            "runtime": d.get("runtime"),
            "genres": genres,
            "keywords": keywords,
            "poster_path": d.get("poster_path"),
            "overview": d.get("overview", ""),
        })

    return pd.DataFrame(rows)
