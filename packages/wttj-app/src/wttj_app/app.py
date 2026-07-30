import os
from pathlib import Path

import pandas as pd
import streamlit as st

HF_DATASET_REPO = os.getenv("HF_DATASET_REPO")
HF_TOKEN = os.getenv("HF_TOKEN")
DATA_PATH = os.getenv("DATA_PATH")

DISPLAY_COLS = [
    "role_family",
    "matched_role_query",
    "job_title",
    "company_name",
    "city",
    "contract_type",
    "remote_level",
    "salary_label",
    "experience_label",
    "date_posted_label",
    "date_posted_estimated",
    "job_url",
]

RECENT_WINDOW_DAYS = 15
RECENT_SCRAPE_FALLBACK_DAYS = 5
NON_PRECISE_LABEL = "Non précisé"
JUNIOR_DEFAULT_LABELS = {NON_PRECISE_LABEL, "< 6 mois", "> 6 mois"}


def get_default_visible_columns(columns: list[str]) -> list[str]:
    preferred = [column for column in DISPLAY_COLS if column in columns]
    remaining = [column for column in columns if column not in preferred]
    return [*preferred, *remaining]


def experience_display_labels(series: pd.Series) -> pd.Series:
    return series.fillna(NON_PRECISE_LABEL)


def filter_by_experience(df: pd.DataFrame, selected_experience: list[str]) -> pd.DataFrame:
    return df[experience_display_labels(df["experience_label"]).isin(selected_experience)]


def recent_offers_mask(df: pd.DataFrame, now: pd.Timestamp) -> pd.Series:
    if df.empty:
        return pd.Series(dtype=bool)
    empty_utc_dates = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns, UTC]")
    posted = (
        pd.to_datetime(df["date_posted_estimated"], utc=True, errors="coerce")
        if "date_posted_estimated" in df.columns
        else empty_utc_dates
    )
    scraped = (
        pd.to_datetime(df["scraped_at"], utc=True, errors="coerce")
        if "scraped_at" in df.columns
        else empty_utc_dates
    )
    posted_recent = posted.notna() & ((now - posted) <= pd.Timedelta(days=RECENT_WINDOW_DAYS))
    fallback_recent = posted.isna() & scraped.notna() & (
        (now - scraped) <= pd.Timedelta(days=RECENT_SCRAPE_FALLBACK_DAYS)
    )
    return posted_recent | fallback_recent


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

    filter_columns = st.columns(4)
    if "role_family" in df.columns:
        selected_families = filter_columns[0].multiselect(
            "Role families",
            sorted(df["role_family"].dropna().unique()),
        )
        if selected_families:
            df = df[df["role_family"].isin(selected_families)]
    if "contract_type" in df.columns:
        selected_contracts = filter_columns[1].multiselect(
            "Contracts",
            sorted(df["contract_type"].dropna().unique()),
        )
        if selected_contracts:
            df = df[df["contract_type"].isin(selected_contracts)]
    if "remote_level" in df.columns:
        selected_remote = filter_columns[2].multiselect(
            "Remote",
            sorted(df["remote_level"].dropna().unique()),
        )
        if selected_remote:
            df = df[df["remote_level"].isin(selected_remote)]
    if "city" in df.columns:
        selected_cities = filter_columns[3].multiselect(
            "Cities",
            sorted(df["city"].dropna().unique()),
        )
        if selected_cities:
            df = df[df["city"].isin(selected_cities)]

    toggle_columns = st.columns(2)
    recent_only = toggle_columns[0].checkbox(
        "🕒 Offres récentes uniquement (≤15 j publication, repli ≤5 j scraping)"
    )
    if recent_only:
        df = df[recent_offers_mask(df, pd.Timestamp.now(tz="UTC"))]

    junior_only = toggle_columns[1].checkbox("🎯 Profils junior uniquement")
    if junior_only and "experience_label" in df.columns:
        options = sorted(experience_display_labels(df["experience_label"]).unique())
        selected_experience = st.multiselect(
            "Niveaux d'expérience retenus",
            options,
            default=[option for option in options if option in JUNIOR_DEFAULT_LABELS],
        )
        df = filter_by_experience(df, selected_experience)

    col1, col2, col3 = st.columns(3)
    col1.metric("Total offers", len(df))
    col2.metric(
        "Last scraped",
        pd.to_datetime(df["scraped_at"]).max().strftime("%Y-%m-%d %H:%M UTC") if not df.empty else "—",
    )
    col3.metric("Companies", df["company_name"].nunique() if "company_name" in df.columns else "—")

    st.divider()
    st.caption(f"{len(df)} offer(s) shown")

    default_cols = get_default_visible_columns(list(df.columns))
    selected_cols = st.multiselect("Visible columns", list(df.columns), default=default_cols)
    visible_cols = selected_cols or default_cols
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
