import time
from scipy.stats import spearmanr
from tmdb import search_movies, fetch_all_details, build_dataframe
from rerank import rerank

# Compare API and scoring time, then measure how much each weight profile
# changes the original search ranking.
for pages in [1, 2]:
    t0 = time.perf_counter()
    movies = search_movies.__wrapped__("Space", pages=pages)
    details = fetch_all_details(movies)
    df = build_dataframe(details)
    t_api = time.perf_counter() - t0

    t1 = time.perf_counter()
    res = rerank(df, {"rating": 5, "recency": 3, "runtime": 2, "genre": 4, "keyword": 2}, ["Science Fiction"], ["space"], 120)
    t_rerank = time.perf_counter() - t1
    print(f"Pages={pages} (N={len(df)}): API={t_api:.3f}s, Rerank={t_rerank*1000:.2f}ms")

df["orig_rank"] = range(1, len(df) + 1)
profiles = {
    "Only Rating": {"rating": 10, "recency": 0, "runtime": 0, "genre": 0, "keyword": 0},
    "Only Recency": {"rating": 0, "recency": 10, "runtime": 0, "genre": 0, "keyword": 0},
    "Balanced": {"rating": 5, "recency": 3, "runtime": 2, "genre": 4, "keyword": 2},
}

for name, w in profiles.items():
    res = rerank(df, w, ["Science Fiction"], [], 120)
    rho, _ = spearmanr(res["orig_rank"], range(1, len(res) + 1))
    top5_changed = sum(1 for i, r in enumerate(res["orig_rank"].head(5), 1) if r != i)
    print(f"{name}: Spearman rho = {rho:.2f}, Top-5 changes = {top5_changed}/5")