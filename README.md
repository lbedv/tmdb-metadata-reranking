# TMDB Metadata Reranking

[![CI](https://github.com/lbedv/tmdb-metadata-reranking/actions/workflows/ci.yml/badge.svg)](https://github.com/lbedv/tmdb-metadata-reranking/actions/workflows/ci.yml)
[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://tmdb-metadata-reranking.streamlit.app)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Pandas](https://img.shields.io/badge/Pandas-150458?logo=pandas&logoColor=white)](https://pandas.pydata.org/)

A Streamlit app that searches TMDB and reranks movie results using configurable rating, recency, runtime, genre, and keyword factors.

**Live Demo:** [tmdb-metadata-reranking.streamlit.app](https://tmdb-metadata-reranking.streamlit.app)

## Functionality

- Search movies through the TMDB API.
- Adjust rating, recency, runtime, genre, and keyword weights.
- Filter results by genre, keywords, runtime, and minimum vote count.
- View reranked results, factor contributions, and per-movie score breakdowns.

## Project structure

```text
.
├── app.py           # Streamlit interface
├── benchmark.py     # API and reranking benchmarks
├── rerank.py        # Scoring and reranking logic
├── tmdb.py          # TMDB API client and DataFrame builder
├── test_rerank.py   # Unit tests
├── requirements.txt # Python dependencies
├── .env.example     # TMDB API key template
└── .gitignore
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Add your TMDB API key to `.env`:

```env
TMDB_API_KEY=your_tmdb_api_key_here
```

## Run

```bash
streamlit run app.py
```

## Test

```bash
pytest -q
```

## License

[MIT](LICENSE)