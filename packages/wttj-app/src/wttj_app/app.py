import os
from pathlib import Path

import pandas as pd
import streamlit as st

HF_DATASET_REPO = os.getenv("HF_DATASET_REPO")
HF_TOKEN = os.getenv("HF_TOKEN")
DATA_PATH = os.getenv("DATA_PATH")

DISPLAY_COLS = [
    "job_title",
    "company_name",
    "city",
    "contract_type",
    "remote_level",
    "date_posted_label",
    "job_url",
]


def check_credentials(username: str, password: str) -> bool:
    expected_user = os.getenv("APP_USERNAME")
    expected_password = os.getenv("APP_PASSWORD")
    return bool(
        expected_user
        and expected_password
        and username == expected_user
        and password == expected_password
    )


def auth_configured() -> bool:
    return bool(os.getenv("APP_USERNAME") and os.getenv("APP_PASSWORD"))


def default_local_fallback() -> Path:
    current = Path(__file__).resolve()
    for parent in (current.parent, *current.parents):
        candidate = parent / "data" / "jobs.parquet"
        if candidate.exists():
            return candidate
    return Path("data/jobs.parquet")


@st.cache_data(ttl=300)
def load_data() -> pd.DataFrame:
    if HF_DATASET_REPO:
        from huggingface_hub import hf_hub_download

        path = hf_hub_download(
            repo_id=HF_DATASET_REPO,
            filename="jobs.parquet",
            repo_type="dataset",
            token=HF_TOKEN,
        )
    elif DATA_PATH:
        path = DATA_PATH
    else:
        path = default_local_fallback()

    return pd.read_parquet(path)


def ensure_auth() -> None:
    if not auth_configured():
        st.error("Missing app auth configuration. Set APP_USERNAME and APP_PASSWORD.")
        st.stop()

    if st.session_state.get("authenticated"):
        return

    st.title("🔐 WTTJ Jobs Login")
    with st.form("login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in")

    if submitted:
        if check_credentials(username, password):
            st.session_state["authenticated"] = True
            st.rerun()
        st.error("Invalid credentials.")
    st.stop()


def main() -> None:
    st.set_page_config(page_title="WTTJ Jobs", page_icon="💼", layout="wide")
    ensure_auth()

    st.title("💼 Welcome to the Jungle — Job Offers")

    try:
        df = load_data()
    except FileNotFoundError:
        st.error("No data found. Run the scraper first or set HF_DATASET_REPO.")
        st.stop()

    query = st.text_input("Search", placeholder="Python, Data, Paris…")
    if query:
        mask = (
            df.get("job_title", df.get("title", pd.Series(dtype=str))).fillna("").str.contains(query, case=False)
            | df.get("company_name", pd.Series(dtype=str)).fillna("").str.contains(query, case=False)
            | df.get("city", pd.Series(dtype=str)).fillna("").str.contains(query, case=False)
        )
        df = df[mask]

    col1, col2, col3 = st.columns(3)
    col1.metric("Total offers", len(df))
    col2.metric(
        "Last scraped",
        pd.to_datetime(df["scraped_at"]).max().strftime("%Y-%m-%d %H:%M UTC") if not df.empty else "—",
    )
    col3.metric("Companies", df["company_name"].nunique() if "company_name" in df.columns else "—")

    st.divider()
    st.caption(f"{len(df)} offer(s) shown")

    visible_cols = [col for col in DISPLAY_COLS if col in df.columns]
    st.dataframe(
        df[visible_cols],
        column_config={
            "job_url": st.column_config.LinkColumn("URL"),
            "job_title": st.column_config.TextColumn("Title", width="medium"),
            "company_name": st.column_config.TextColumn("Company", width="medium"),
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

if __name__ == "__main__":
    main()
