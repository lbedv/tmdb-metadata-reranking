from __future__ import annotations

import streamlit as st
import pandas as pd
import altair as alt

from tmdb import search_movies, fetch_all_details, build_dataframe
from rerank import rerank, normalise_weights

st.set_page_config(page_title="TMDB Reranking", page_icon="🎬", layout="wide")

with st.sidebar:
    st.title("🎬 TMDB Reranking")

    query = st.text_input("Search query", placeholder="e.g. Inception")
    search_btn = st.button("🔍 Search", use_container_width=True)

    st.divider()

    st.subheader("⚖️ Factor weights")
    w_rating  = st.slider("Rating",   0, 10, 5)
    w_recency = st.slider("Recency",  0, 10, 3)
    w_runtime = st.slider("Runtime",  0, 10, 2)
    w_genre   = st.slider("Genre",    0, 10, 4)
    w_keyword = st.slider("Keyword",  0, 10, 2)

    raw_weights = {"rating": w_rating, "recency": w_recency,
                   "runtime": w_runtime, "genre": w_genre, "keyword": w_keyword}
    norm_w = normalise_weights(raw_weights)

    st.caption("Effective weights:")
    cols = st.columns(5)
    labels = ["Rat.", "Rec.", "Run.", "Gen.", "Kw."]
    for col, (key, label) in zip(cols, zip(norm_w, labels)):
        col.metric(label, f"{norm_w[key]:.0%}")

    st.divider()

    TMDB_GENRES = [
        "Action", "Adventure", "Animation", "Comedy", "Crime",
        "Documentary", "Drama", "Family", "Fantasy", "History",
        "Horror", "Music", "Mystery", "Romance", "Science Fiction",
        "Thriller", "War", "Western",
    ]
    query_genres = st.multiselect("Query genres", TMDB_GENRES)

    kw_input = st.text_input("Query keywords (comma-separated)", placeholder="alien, space, hero")
    query_keywords = [k.strip() for k in kw_input.split(",") if k.strip()]

    target_runtime = st.slider("Target runtime (min)", 60, 240, 120, step=5)

    min_votes = st.number_input("Min vote count", min_value=0, value=0, step=100)

if "raw_df" not in st.session_state:
    st.session_state["raw_df"] = None
if "orig_order" not in st.session_state:
    st.session_state["orig_order"] = None

if search_btn and query.strip():
    with st.spinner("Fetching from TMDB…"):
        movies = search_movies(query.strip())
        if movies:
            details = fetch_all_details(movies)
            df = build_dataframe(details)
            # Keep TMDB's search position as the baseline for rank changes.
            df["orig_rank"] = range(1, len(df) + 1)
            st.session_state["raw_df"] = df
        else:
            st.warning("No results found.")
            st.session_state["raw_df"] = None

raw_df = st.session_state.get("raw_df")

if raw_df is None:
    st.info("Enter a query in the sidebar and click **Search**.")
    st.stop()

df_filtered = raw_df[raw_df["vote_count"] >= min_votes].copy()

if df_filtered.empty:
    st.warning("No movies match the vote count filter.")
    st.stop()

result_df = rerank(
    df_filtered,
    raw_weights,
    query_genres,
    query_keywords,
    target_runtime,
)
result_df["new_rank"] = range(1, len(result_df) + 1)

st.subheader("📋 Reranked Results")

def rank_change(row):
    """Show how many places a movie moved relative to its TMDB rank."""
    delta = row["orig_rank"] - row["new_rank"]
    if delta > 0:
        return f"↑{delta}"
    elif delta < 0:
        return f"↓{abs(delta)}"
    return "–"

display_df = result_df[["new_rank", "title", "year", "vote_average", "vote_count",
                          "runtime", "FinalScore", "orig_rank"]].copy()
display_df["Δ rank"] = result_df.apply(rank_change, axis=1)
display_df = display_df.rename(columns={
    "new_rank": "#",
    "title": "Title",
    "year": "Year",
    "vote_average": "Rating",
    "vote_count": "Votes",
    "runtime": "Runtime (min)",
    "FinalScore": "Score",
    "orig_rank": "TMDB rank",
})
display_df["Score"] = display_df["Score"].round(3)

st.dataframe(display_df, use_container_width=True, hide_index=True)

st.subheader("📊 Factor contribution (Top 10)")

top10 = result_df.head(10).copy()
factor_cols = {
    "Rating":  "weighted_rating",
    "Recency": "weighted_recency",
    "Runtime": "weighted_runtime",
    "Genre":   "weighted_genre",
    "Keyword": "weighted_keyword",
}

# Altair expects one row per movie and factor for the stacked chart.
records = []
for _, row in top10.iterrows():
    for factor, col in factor_cols.items():
        records.append({"Title": row["title"], "Factor": factor, "Score": row[col]})

chart_df = pd.DataFrame(records)

color_scale = alt.Scale(
    domain=list(factor_cols.keys()),
    range=["#4c78a8", "#f58518", "#e45756", "#72b7b2", "#54a24b"],
)

bar = (
    alt.Chart(chart_df)
    .mark_bar()
    .encode(
        x=alt.X("Title:N", sort="-y", title="Movie", axis=alt.Axis(labelAngle=-30)),
        y=alt.Y("Score:Q", stack="zero", title="Weighted Score"),
        color=alt.Color("Factor:N", scale=color_scale, legend=alt.Legend(title="Factor")),
        tooltip=["Title", "Factor", alt.Tooltip("Score:Q", format=".3f")],
    )
    .properties(height=350)
)

st.altair_chart(bar, use_container_width=True)

st.subheader("🔍 Score breakdown by film")

titles = result_df["title"].tolist()
selected_title = st.selectbox("Select a film", titles)
sel = result_df[result_df["title"] == selected_title].iloc[0]

breakdown = pd.DataFrame({
    "Factor":        list(factor_cols.keys()),
    "Raw score":     [sel["score_rating"], sel["score_recency"], sel["score_runtime"],
                      sel["score_genre"], sel["score_keyword"]],
    "Weight":        [norm_w["rating"], norm_w["recency"], norm_w["runtime"],
                      norm_w["genre"], norm_w["keyword"]],
    "Weighted score": [sel["weighted_rating"], sel["weighted_recency"], sel["weighted_runtime"],
                       sel["weighted_genre"], sel["weighted_keyword"]],
})
breakdown = breakdown.round(4)

col1, col2 = st.columns([1, 1])

with col1:
    st.dataframe(breakdown, use_container_width=True, hide_index=True)

with col2:
    bar2 = (
        alt.Chart(breakdown)
        .mark_bar()
        .encode(
            x=alt.X("Weighted score:Q", title="Weighted contribution"),
            y=alt.Y("Factor:N", sort="-x"),
            color=alt.Color("Factor:N", scale=color_scale, legend=None),
            tooltip=["Factor",
                     alt.Tooltip("Raw score:Q", format=".3f"),
                     alt.Tooltip("Weight:Q", format=".1%"),
                     alt.Tooltip("Weighted score:Q", format=".3f")],
        )
        .properties(height=220)
    )
    st.altair_chart(bar2, use_container_width=True)

st.caption(f"Total FinalScore: **{sel['FinalScore']:.4f}**")
