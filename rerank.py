from __future__ import annotations

import pandas as pd


def score_rating(vote_average: float | None) -> float:
    """Scale TMDB's 0–10 rating to a 0–1 score."""
    if vote_average is None or pd.isna(vote_average):
        return 0.0
    return float(vote_average) / 10.0


def score_recency(year: float | None, min_year: float, max_year: float) -> float:
    """Scale a year against the oldest and newest results; missing years score zero."""
    if year is None or pd.isna(year):
        return 0.0
    if max_year == min_year:
        return 1.0
    return (float(year) - min_year) / (max_year - min_year)


def score_runtime(runtime: float | None, target: float) -> float:
    """Reduce the score linearly with distance from target, reaching zero at 90 minutes."""
    if runtime is None or pd.isna(runtime):
        return 0.0
    return max(0.0, 1.0 - abs(float(runtime) - float(target)) / 90.0)


def jaccard(set_a: set, set_b: set) -> float:
    """Return intersection-over-union, or zero if either set is empty."""
    if not set_a or not set_b:
        return 0.0
    inter = len(set_a & set_b)
    union = len(set_a | set_b)
    return inter / union if union else 0.0


def score_genres(movie_genres: list[str], query_genres: list[str]) -> float:
    """Compare a movie's genres with the requested genres."""
    return jaccard(set(movie_genres), set(query_genres))


def score_keywords(movie_keywords: list[str], query_keywords: list[str]) -> float:
    """Compare keywords without regard to letter case."""
    return jaccard(set(kw.lower() for kw in movie_keywords),
                   set(kw.lower() for kw in query_keywords))


def normalise_weights(weights: dict[str, float]) -> dict[str, float]:
    """Scale weights to sum to one; use equal weights when all are zero."""
    total = sum(weights.values())
    keys = list(weights.keys())
    if total == 0:
        return {k: 1.0 / len(keys) for k in keys}
    return {k: v / total for k, v in weights.items()}


def rerank(
    df: pd.DataFrame,
    weights: dict[str, float],
    query_genres: list[str],
    query_keywords: list[str],
    target_runtime: float,
) -> pd.DataFrame:
    """Add weighted scores for all five factors and sort by their sum.

    Recency is scaled to the year range in this DataFrame; genres and keywords
    use Jaccard similarity against the query values.
    """
    df = df.copy()

    valid_years = df["year"].dropna()
    min_year = float(valid_years.min()) if len(valid_years) else 0.0
    max_year = float(valid_years.max()) if len(valid_years) else 0.0

    df["score_rating"]  = df["vote_average"].apply(score_rating)
    df["score_recency"] = df["year"].apply(lambda y: score_recency(y, min_year, max_year))
    df["score_runtime"] = df["runtime"].apply(lambda r: score_runtime(r, target_runtime))
    df["score_genre"]   = df["genres"].apply(lambda g: score_genres(g, query_genres))
    df["score_keyword"] = df["keywords"].apply(lambda k: score_keywords(k, query_keywords))

    w = normalise_weights(weights)

    df["weighted_rating"]  = w["rating"]  * df["score_rating"]
    df["weighted_recency"] = w["recency"] * df["score_recency"]
    df["weighted_runtime"] = w["runtime"] * df["score_runtime"]
    df["weighted_genre"]   = w["genre"]   * df["score_genre"]
    df["weighted_keyword"] = w["keyword"] * df["score_keyword"]

    df["FinalScore"] = (
        df["weighted_rating"]
        + df["weighted_recency"]
        + df["weighted_runtime"]
        + df["weighted_genre"]
        + df["weighted_keyword"]
    )

    df = df.sort_values("FinalScore", ascending=False).reset_index(drop=True)
    return df
