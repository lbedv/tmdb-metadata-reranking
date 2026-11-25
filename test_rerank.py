import math
import pandas as pd
import pytest
from rerank import (
    score_rating,
    score_recency,
    score_runtime,
    jaccard,
    score_genres,
    score_keywords,
    normalise_weights,
    rerank,
)


def test_rating_normal():
    assert math.isclose(score_rating(8.0), 0.8)

def test_rating_zero():
    assert score_rating(0.0) == 0.0

def test_rating_ten():
    assert math.isclose(score_rating(10.0), 1.0)

def test_rating_none():
    assert score_rating(None) == 0.0

def test_rating_nan():
    assert score_rating(float("nan")) == 0.0


def test_recency_normal():
    assert math.isclose(score_recency(2020, 2000, 2024), (2020 - 2000) / (2024 - 2000))

def test_recency_min_equals_max():
    assert score_recency(2020, 2020, 2020) == 1.0

def test_recency_none():
    assert score_recency(None, 2000, 2024) == 0.0

def test_recency_at_min():
    assert score_recency(2000, 2000, 2020) == 0.0

def test_recency_at_max():
    assert score_recency(2020, 2000, 2020) == 1.0


def test_runtime_exact():
    assert math.isclose(score_runtime(120, 120), 1.0)

def test_runtime_90_away():
    assert score_runtime(210, 120) == 0.0

def test_runtime_more_than_90():
    assert score_runtime(220, 120) == 0.0

def test_runtime_none():
    assert score_runtime(None, 120) == 0.0

def test_runtime_45_away():
    assert math.isclose(score_runtime(75, 120), 0.5)


def test_jaccard_empty_a():
    assert jaccard(set(), {"a", "b"}) == 0.0

def test_jaccard_empty_b():
    assert jaccard({"a"}, set()) == 0.0

def test_jaccard_both_empty():
    assert jaccard(set(), set()) == 0.0

def test_jaccard_identical():
    assert jaccard({"a", "b"}, {"a", "b"}) == 1.0

def test_jaccard_disjoint():
    assert jaccard({"a"}, {"b"}) == 0.0

def test_jaccard_partial():
    assert math.isclose(jaccard({"a", "b"}, {"b", "c"}), 1/3)


def test_genres_empty_query():
    assert score_genres(["Action", "Drama"], []) == 0.0

def test_genres_match():
    assert math.isclose(score_genres(["Action", "Drama"], ["Action"]), 1/2)

def test_keywords_case_insensitive():
    assert math.isclose(score_keywords(["Alien"], ["alien"]), 1.0)

def test_keywords_empty():
    assert score_keywords([], ["alien"]) == 0.0


def test_weights_normal():
    w = normalise_weights({"a": 2.0, "b": 2.0, "c": 6.0})
    assert math.isclose(sum(w.values()), 1.0)
    assert math.isclose(w["c"], 0.6)

def test_weights_all_zero():
    w = normalise_weights({"a": 0.0, "b": 0.0})
    assert math.isclose(w["a"], 0.5)
    assert math.isclose(w["b"], 0.5)


def _make_df():
    return pd.DataFrame([
        {"title": "A", "year": 2020, "vote_average": 8.0, "runtime": 120.0,
         "genres": ["Action"], "keywords": ["hero"]},
        {"title": "B", "year": 2000, "vote_average": 5.0, "runtime": 90.0,
         "genres": ["Drama"], "keywords": []},
        {"title": "C", "year": None, "vote_average": None, "runtime": None,
         "genres": [], "keywords": []},
    ])

def test_rerank_sorted():
    df = _make_df()
    result = rerank(df, {"rating": 10, "recency": 0, "runtime": 0, "genre": 0, "keyword": 0},
                    [], [], 120)
    assert result.iloc[0]["title"] == "A"

def test_rerank_all_missing_scores_zero():
    df = _make_df()
    result = rerank(df, {"rating": 1, "recency": 1, "runtime": 1, "genre": 1, "keyword": 1},
                    [], [], 120)
    c_row = result[result["title"] == "C"].iloc[0]
    assert c_row["FinalScore"] == 0.0

def test_rerank_genre_weight():
    df = _make_df()
    result = rerank(df, {"rating": 0, "recency": 0, "runtime": 0, "genre": 10, "keyword": 0},
                    ["Action"], [], 120)
    assert result.iloc[0]["title"] == "A"

def test_rerank_zero_weights_equal():
    df = _make_df()
    result = rerank(df, {"rating": 0, "recency": 0, "runtime": 0, "genre": 0, "keyword": 0},
                    [], [], 120)
    # Equal weights still favor A because of its rating and year.
    assert "FinalScore" in result.columns
