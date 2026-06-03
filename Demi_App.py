[16:59, 03/06/2026] +44 7450 337871: import streamlit as st
from database import run_sql
from ai_sql_generator import generate_sql
from validator import validate_sql
import time
from datetime import datetime
[16:59, 03/06/2026] +44 7450 337871: def explain_sql(sql):
    # Mock breakdown — replace with real AI explanation when backend is ready
    return {
        "SELECT": "Choosing the REGION column and calculating the total SALES for each region.",
        "FROM": "Pulling data from the AMAZON_SALES table.",
        "GROUP BY": "Grouping the results by REGION so each region gets its own total.",
    }
[17:01, 03/06/2026] +44 7450 337871: # ── Session state ────────────────────────────────────────────────
if "history" not in st.session_state:
    st.session_state.history = []
if "prefill" not in st.session_state:
    st.session_state.prefill = ""

# ── Page config ──────────────────────────────────────────────────
st.set_page_config(page_title="QueryLens · AI Data Assistant", page_icon="🔍", layout="wide")

# ── Styling ──────────────────────────────────────────────────────
st.markdown("""
<style>
html, body, [class*="css"] {
    background-color: #0d0f14 !important;
    color: #e2e8f0 !important;
}
[data-testid="stTextInput"] input {
    background-color: #313b57 !important;
    color: #e2e8f0 !important;
    border: 1px solid #252b3b !important;
    border-radius: 8px !important;
}
[data-testid="stButton"] > button {
    background-color: #f0a500 !important;
    color: #0d0f14 !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
}
</style>
""", unsafe_allow_html=True)

# ── Header ───────────────────────────────────────────────────────
st.markdown("""
<div style="display:flex; align-items:center; gap:12px; padding-bottom:1rem;
            border-bottom:1px solid #252b3b; margin-bottom:1.5rem;">
    <div style="width:38px; height:38px; background:#f0a500; border-radius:8px;
                display:flex; align-items:center; justify-content:center; font-size:20px;">
        🔍
    </div>
    <div>
        <div style="font-size:1.2rem; font-weight:600; letter-spacing:-0.02em;">QueryLens</div>
        <div style="font-size:0.75rem; color:#64748b; margin-top:2px;">AI-Powered Data Assistant</div>
    </div>
    <div style="margin-left:auto; background:rgba(240,165,0,0.12); border:1px solid rgba(240,165,0,0.25);
                color:#f0a500; font-size:0.65rem; padding:3px 10px; border-radius:99px;
                letter-spacing:0.05em; text-transform:uppercase;">
        AI Agent
    </div>
</div>
""", unsafe_allow_html=True)

st.divider()
[17:02, 03/06/2026] +44 7450 337871: # ── Search bar ───────────────────────────────────────────────────
user_question = st.text_input(
    label="Question",
    placeholder="e.g. What were the total sales in the last quarter broken down by region?",
    value=st.session_state.prefill
)

run_button = st.button("Run Query")
[17:02, 03/06/2026] +44 7450 337871: # ── Suggested questions ──────────────────────────────────────────
SUGGESTIONS = [
    "Total sales by region?",
    "Top 5 products by profit?",
    "Monthly sales trend?",
    "Sales by category?",
]

st.markdown("<div style='font-size:0.75rem; color:#64748b; margin-bottom:6px;'>Suggested questions</div>",
            unsafe_allow_html=True)

cols = st.columns(len(SUGGESTIONS))
for col, suggestion in zip(cols, SUGGESTIONS):
    with col:
        if st.button(suggestion, use_container_width=True):
            st.session_state.prefill = suggestion
            st.rerun()
[17:05, 03/06/2026] +44 7450 337871: if run_button and user_question:

    STEPS = [
        "🧠  Parsing natural language intent",
        "🗺️  Mapping terms to schema",
        "✍️  Generating SQL query",
        "⚡  Executing on database",
        "📊  Analysing result set",
        "💬  Composing summary",
    ]

    with st.status("Agent working...", expanded=True) as status:
        placeholders = [st.empty() for _ in STEPS]

        for i, label in enumerate(STEPS):
            placeholders[i].markdown(f"⬜ {label}")
            time.sleep(0.5)
            placeholders[i].markdown(f"✅ {label}")

        try:
            sql = generate_sql(user_question, SCHEMA_TEXT)
            validate_sql(sql)
            result_df = run_sql(sql)
            error = None
        except Exception as e:
            [17:05, 03/06/2026] +44 7450 337871: sql = None
            result_df = None
            error = str(e)

        status.update(label="✅ Query complete", state="complete")

    if error:
        st.error(f"Something went wrong: {error}")
    else:
        st.session_state.history.append({
            "question": user_question,
            "sql": sql,
            "summary": f"Returned {len(result_df)} rows.",
            "time": datetime.now().strftime("%H:%M:%S"),
        })

        df = result_df

        # ── Three tabs ───────────────────────────────────────────
        tab_results, tab_insights, tab_sql = st.tabs(["📋 Results", "💡 Insights", "⌨️ SQL"])

        with tab_results:
            st.dataframe(df, use_container_width=True)
            csv = df.to_csv(index=False)
            st.download_button(
                label="⬇️ Download results as CSV",
                data=csv,
                file_name="query_results.csv",
                mime="text/csv"
            )

        with tab_insights:
            st.subheader("Summary")
            st.write(f"Your query returned {len(df)} rows across {len(df.columns)} columns.")

            st.divider()

            num_cols = df.select_dtypes(include="number").columns.tolist()
            str_cols = df.select_dtypes(exclude="number").columns.tolist()

            if num_cols and len(df) > 1:
                st.subheader("Chart")
                chart_index = str_cols[0] if str_cols else df.columns[0]
                chart_col   = num_cols[0]
                chart_df    = df.set_index(chart_index)[[chart_col]]
                st.bar_chart(chart_df)
            else:
                st.caption("Chart not available for single-row results.")

            st.divider()

            if num_cols:
                st.subheader("Descriptive Statistics")
                st.dataframe(df[num_cols].describe().round(2), use_container_width=True)
            else:
                st.caption("No numeric columns to summarise.")

        # with tab_sql:
        #     st.subheader("Generated SQL")
        #     st.code(sql.strip(), language="sql")
        with tab_sql:
            st.subheader("Generated SQL")
            st.code(sql.strip(), language="sql")

            st.divider()

            st.subheader("SQL Breakdown")
            st.info(explain_sql(sql))
[17:05, 03/06/2026] +44 7450 337871: # ── Sidebar history ──────────────────────────────────────────────
# This appears as a collapsible panel on the left and shows every question the user has asked this session.
with st.sidebar:
    st.header("Query History")
    st.metric("Queries Run", len(st.session_state.history))

    if not st.session_state.history:
        st.caption("Your previous questions will appear here.")
    else:
        # Loop through history in reverse so newest is at the top
        for i, item in enumerate(reversed(st.session_state.history)):
            # with st.expander(f"Q: {item['question'][:40]}..."):
            # with st.expander(f"{item['time']} -> {item['question'][:40]}..."):
            with st.expander(item["question"][:50]):
                st.caption(item["time"])
                st.caption("Generated SQL:")
                st.code(item["sql"], language="sql")
                st.caption("Summary:")
                st.write(item["summary"])
                if st.button("Run Again", key=f"rerun_{i}"):
                    st.session_state.prefill = item["question"]
                    st.rerun()

        # Button to wipe the history
        if st.button("Clear history"):
            st.session_state.history = []   
            st.rerun()