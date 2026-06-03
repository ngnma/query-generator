"""
Natural Language Query Agent — IADS Hackathon
Single-file Streamlit app.  Swap `_mock_backend` for your real OCI/LLM function.
"""

import io, os, re, sqlite3, tempfile, textwrap
import pandas as pd
import streamlit as st

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DataTalk · Natural Language Query",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Minimal custom CSS ────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:wght@400;500;600&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
h1, h2, h3 { font-family: 'DM Serif Display', serif; }

.dt-card {
    background: #f8f7f4;
    border: 1px solid #e8e4de;
    border-radius: 12px;
    padding: 1.1rem 1.4rem;
    margin-bottom: 1rem;
}
.dt-tag {
    display: inline-block;
    background: #1a1a2e;
    color: #e8e4de;
    border-radius: 20px;
    padding: 2px 10px;
    font-size: 0.78rem;
    margin: 2px 3px 2px 0;
}
.dt-summary {
    background: #eaf4ee;
    border-left: 4px solid #2d9e6b;
    border-radius: 0 8px 8px 0;
    padding: 0.8rem 1rem;
    margin-bottom: 0.8rem;
    font-size: 1rem;
}
.dt-error {
    background: #fff0ee;
    border-left: 4px solid #e05a3a;
    border-radius: 0 8px 8px 0;
    padding: 0.8rem 1rem;
    margin-bottom: 0.8rem;
}
.stTextArea textarea { font-size: 1.05rem !important; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# MOCK BACKEND  ← replace with your real OCI / LLM function
# Signature: (question: str, schema_desc: str, db_path: str, table: str)
#            -> dict {sql, results_df, summary}
# ══════════════════════════════════════════════════════════════════════════════
def _mock_backend(question: str, schema_desc: str, db_path: str, table: str) -> dict:
    con = sqlite3.connect(db_path)
    info = pd.read_sql(f"PRAGMA table_info({table})", con)
    cols, types = info["name"].tolist(), info["type"].str.lower().tolist()
    num = [c for c, t in zip(cols, types) if any(k in t for k in ("int","real","num","float"))]
    sql = f"SELECT {cols[0]}, SUM({num[0]}) total FROM {table} GROUP BY {cols[0]} LIMIT 10" \
          if (cols and num) else f"SELECT * FROM {table} LIMIT 10"
    try: df = pd.read_sql(sql, con)
    except Exception: df = pd.read_sql(f"SELECT * FROM {table} LIMIT 10", con)
    con.close()
    return {"sql": sql, "results_df": df,
            "summary": f"Here are the top results based on your question: **{question}**"}

# ══════════════════════════════════════════════════════════════════════════════
# DATA LOADING — all sources → SQLite
# ══════════════════════════════════════════════════════════════════════════════
def _clean_col(name: str) -> str:
    return re.sub(r"[^\w]", "_", str(name)).strip("_") or "col"

def load_to_sqlite(source, db_path: str) -> str:
    """Load DataFrame, CSV, SQL dump, or SQLite file into db_path. Returns table name."""
    table = "dataset"
    if isinstance(source, pd.DataFrame):
        df = source.copy()
        df.columns = [_clean_col(c) for c in df.columns]
        con = sqlite3.connect(db_path)
        df.to_sql(table, con, if_exists="replace", index=False)
        con.close()
        return table

    fname = getattr(source, "name", "")
    ext = os.path.splitext(fname)[-1].lower()
    raw = source.read() if hasattr(source, "read") else open(source, "rb").read()

    if ext in (".csv", ".tsv"):
        sep = "\t" if ext == ".tsv" else ","
        df = pd.read_csv(io.BytesIO(raw), sep=sep, on_bad_lines="skip")
        df.columns = [_clean_col(c) for c in df.columns]
        table = _clean_col(os.path.splitext(fname)[0]) or table
        con = sqlite3.connect(db_path)
        df.to_sql(table, con, if_exists="replace", index=False)
        con.close()

    elif ext in (".sql",):
        sql_text = raw.decode("utf-8", errors="ignore")
        con = sqlite3.connect(db_path)
        try:
            con.executescript(sql_text)
            con.commit()
        except Exception:
            pass
        tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", con)
        table = tables.iloc[0, 0] if len(tables) else table
        con.close()

    elif ext in (".db", ".sqlite", ".sqlite3"):
        import shutil
        shutil.copy2(io.BytesIO(raw) if isinstance(raw, bytes) else source, db_path)
        # write bytes directly
        with open(db_path, "wb") as f:
            f.write(raw)
        con = sqlite3.connect(db_path)
        tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", con)
        table = tables.iloc[0, 0] if len(tables) else table
        con.close()

    return table

# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def get_schema_desc(db_path: str, table: str) -> str:
    con = sqlite3.connect(db_path)
    info = pd.read_sql(f"PRAGMA table_info({table})", con)
    con.close()
    parts = [f"{r['name']} ({r['type']})" for _, r in info.iterrows()]
    return f"Table '{table}' columns: {', '.join(parts)}"

def friendly_col_preview(db_path: str, table: str) -> str:
    con = sqlite3.connect(db_path)
    cols = pd.read_sql(f"PRAGMA table_info({table})", con)["name"].tolist()[:3]
    con.close()
    readable = [c.replace("_", " ").lower() for c in cols]
    if len(readable) == 1:
        return f"This dataset includes {readable[0]}."
    joined = ", ".join(readable[:-1]) + f" and {readable[-1]}"
    return f"This dataset includes {joined}."

def get_row_count(db_path: str, table: str) -> int:
    con = sqlite3.connect(db_path)
    n = pd.read_sql(f"SELECT COUNT(*) n FROM {table}", con).iloc[0, 0]
    con.close()
    return int(n)

def get_col_count(db_path: str, table: str) -> int:
    con = sqlite3.connect(db_path)
    n = len(pd.read_sql(f"PRAGMA table_info({table})", con))
    con.close()
    return n

def suggest_questions(db_path: str, table: str) -> list[str]:
    con = sqlite3.connect(db_path)
    info = pd.read_sql(f"PRAGMA table_info({table})", con)
    con.close()
    cols = info["name"].tolist()
    types = info["type"].str.lower().tolist()
    num = [c for c, t in zip(cols, types) if any(k in t for k in ("int", "real", "num", "float"))]
    txt = [c for c, t in zip(cols, types) if "text" in t or "char" in t or "varchar" in t]
    qs = []
    if txt and num:
        qs.append(f"What is the total {num[0].replace('_',' ')} grouped by {txt[0].replace('_',' ')}?")
        qs.append(f"Show me the top 5 {txt[0].replace('_',' ')} by {num[0].replace('_',' ')}.")
    if num:
        qs.append(f"What is the average {num[0].replace('_',' ')}?")
    if txt:
        qs.append(f"How many unique {txt[0].replace('_',' ')} values are there?")
    while len(qs) < 4:
        qs.append(f"Show me all rows in this dataset.")
    return qs[:4]

def maybe_chart(df: pd.DataFrame):
    if df is None or df.empty or len(df.columns) < 2:
        return
    txt_cols = [c for c in df.columns if df[c].dtype == object]
    num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if txt_cols and num_cols:
        chart_df = df[[txt_cols[0], num_cols[0]]].set_index(txt_cols[0])
        st.bar_chart(chart_df)

# ══════════════════════════════════════════════════════════════════════════════
# SESSION STATE INIT
# ══════════════════════════════════════════════════════════════════════════════
for key, default in [
    ("db_path", None),
    ("table_name", None),
    ("query_history", []),
    ("prefill", ""),
    ("last_result", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 🗄️ Load your data")
    uploaded = st.file_uploader(
        "Drag & drop a file here",
        type=["csv", "tsv", "sql", "db", "sqlite", "sqlite3"],
        help="CSV, TSV, SQL dump, or SQLite database",
    )

    if uploaded:
        tmp = tempfile.mktemp(suffix=".db")
        try:
            tname = load_to_sqlite(uploaded, tmp)
            st.session_state.db_path = tmp
            st.session_state.table_name = tname
            st.session_state.query_history = []
            st.session_state.last_result = None
            st.success("Dataset loaded ✓")
        except Exception as e:
            st.markdown(f'<div class="dt-error">Could not load file. Please check it is a valid CSV or database.</div>', unsafe_allow_html=True)

    # Dataset card
    if st.session_state.db_path:
        db, tbl = st.session_state.db_path, st.session_state.table_name
        rows, ncols = get_row_count(db, tbl), get_col_count(db, tbl)
        preview = friendly_col_preview(db, tbl)
        st.markdown(f"""
<div class="dt-card">
<b>{tbl.replace('_',' ').title()}</b><br>
<span class="dt-tag">{rows:,} rows</span>
<span class="dt-tag">{ncols} columns</span><br>
<small style="color:#666;">{preview}</small>
</div>""", unsafe_allow_html=True)

    # Query history
    if st.session_state.query_history:
        st.markdown("---")
        st.markdown("#### Recent questions")
        for i, q in enumerate(reversed(st.session_state.query_history[-5:])):
            label = textwrap.shorten(q, 38)
            if st.button(f"↩ {label}", key=f"hist_{i}"):
                st.session_state.prefill = q
                st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# MAIN PANEL
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("# DataTalk")
st.markdown("Ask questions about your data in plain English — no SQL required.")

if not st.session_state.db_path:
    st.markdown("""
<div class="dt-card" style="text-align:center; padding:2.5rem;">
<h3 style="margin-bottom:.5rem;">👈  Start by loading a dataset</h3>
<p style="color:#777; margin:0;">Use the sidebar to upload a CSV, SQL dump, or SQLite file.<br>
Then type a question below — we'll handle the rest.</p>
</div>""", unsafe_allow_html=True)
else:
    db, tbl = st.session_state.db_path, st.session_state.table_name
    schema = get_schema_desc(db, tbl)

    # Example question buttons
    suggestions = suggest_questions(db, tbl)
    cols_btns = st.columns(4)
    for i, (col, q) in enumerate(zip(cols_btns, suggestions)):
        if col.button(q, key=f"sug_{i}", use_container_width=True):
            st.session_state.prefill = q
            st.rerun()

    # Main text input
    question = st.text_area(
        "What would you like to know?",
        value=st.session_state.prefill,
        height=90,
        placeholder="e.g. What were the total sales last quarter by product category?",
    )
    st.session_state.prefill = ""

    run_btn = st.button("🔍  Ask", type="primary", use_container_width=False)

    if run_btn and question.strip():
        with st.spinner("Thinking…"):
            try:
                result = _mock_backend(question.strip(), schema, db, tbl)
                st.session_state.last_result = result
                history = st.session_state.query_history
                if question not in history:
                    history.append(question)
                st.session_state.query_history = history[-5:]
            except Exception:
                st.markdown('<div class="dt-error">Something went wrong while processing your question. Please try rephrasing it.</div>', unsafe_allow_html=True)
                st.session_state.last_result = None

    # Display last result
    res = st.session_state.last_result
    if res:
        st.markdown(f'<div class="dt-summary">{res["summary"]}</div>', unsafe_allow_html=True)

        df_res: pd.DataFrame = res["results_df"]
        if df_res is not None and not df_res.empty:
            st.dataframe(df_res, use_container_width=True, hide_index=True)
            maybe_chart(df_res)
            csv_bytes = df_res.to_csv(index=False).encode()
            st.download_button("⬇ Download as CSV", csv_bytes, "results.csv", "text/csv")
        else:
            st.info("Your query ran successfully but returned no rows.")

        with st.expander("View generated query"):
            st.code(res["sql"], language="sql")
