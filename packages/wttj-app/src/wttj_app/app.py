import os
from pathlib import Path

import pandas as pd
import streamlit as st

HF_DATASET_REPO = os.getenv("HF_DATASET_REPO")
DATA_PATH = os.getenv("DATA_PATH")

_LOCAL_FALLBACK = Path(__file__).parents[4] / "data" / "jobs.csv"

DISPLAY_COLS = ["title", "snippet", "scraped_at", "url"]


@st.cache_data(ttl=300)
def load_data() -> pd.DataFrame:
    if HF_DATASET_REPO:
        from huggingface_hub import hf_hub_download

        path = hf_hub_download(
            repo_id=HF_DATASET_REPO,
            filename="jobs.csv",
            repo_type="dataset",
        )
    elif DATA_PATH:
        path = DATA_PATH
    else:
        path = _LOCAL_FALLBACK

    return pd.read_csv(path, parse_dates=["scraped_at"])


st.set_page_config(page_title="WTTJ Jobs", page_icon="💼", layout="wide")
st.title("💼 Welcome to the Jungle — Job Offers")

df = pd.DataFrame()
try:
    df = load_data()
except FileNotFoundError:
    st.error("No data found. Run the scraper first or set HF_DATASET_REPO.")
    st.stop()

col1, col2, col3 = st.columns(3)
col1.metric("Total offers", len(df))
col2.metric(
    "Last scraped",
    df["scraped_at"].max().strftime("%Y-%m-%d %H:%M UTC") if not df.empty else "—",
)
col3.metric("Sources", df["source"].nunique() if "source" in df.columns else "—")

st.divider()

query = st.text_input("Search", placeholder="Python, Data, Paris…")
if query:
    mask = df["title"].str.contains(query, case=False, na=False) | df[
        "snippet"
    ].str.contains(query, case=False, na=False)
    df = df[mask]

st.caption(f"{len(df)} offer(s) shown")

st.dataframe(
    df[DISPLAY_COLS],
    column_config={
        "url": st.column_config.LinkColumn("URL"),
        "title": st.column_config.TextColumn("Title", width="medium"),
        "snippet": st.column_config.TextColumn("Snippet", width="large"),
        "scraped_at": st.column_config.DatetimeColumn(
            "Scraped at", format="YYYY-MM-DD HH:mm"
        ),
    },
    use_container_width=True,
    hide_index=True,
)

st.download_button(
    "⬇️ Download CSV",
    data=df.to_csv(index=False).encode("utf-8"),
    file_name="wttj_jobs.csv",
    mime="text/csv",
)
