"""
Follow‑Up Question Suggestions Module for QueryLens
==================================================

This module provides functionality to suggest context‑aware follow‑up
questions after a user has executed a query. It analyzes the original
question, the SQL used to retrieve the data, and a preview of the
resulting DataFrame to ask an LLM for additional questions that
encourage deeper data exploration.

The suggestions help non‑technical users continue their analysis by
prompting new queries such as grouping, filtering, or comparing
metrics. Each suggestion can be inserted back into the main query
input via a button click.
"""

import json
from typing import List

import pandas as pd
import streamlit as st

from ai_sql_generator import call_ai_inference_endpoint
from validator import validate_sql
from db import run_sql


def _parse_suggestions(raw_response: str) -> List[str]:
    """
    Attempt to parse a raw LLM response into a list of follow‑up question
    strings. The response may be JSON or a plain text list.

    Parameters
    ----------
    raw_response : str
        Raw output from the LLM.

    Returns
    -------
    List[str]
        A list of follow‑up question suggestions.
    """
    response = raw_response.strip()
    # Try JSON first
    try:
        parsed = json.loads(response)
        # The API may return either a dict with a key or a list directly
        if isinstance(parsed, dict):
            for key in ["follow_up_questions", "follow_up", "followUps", "suggestions", "questions"]:
                if key in parsed and isinstance(parsed[key], list):
                    return [str(x).strip() for x in parsed[key] if str(x).strip()]
        elif isinstance(parsed, list):
            return [str(x).strip() for x in parsed if str(x).strip()]
    except Exception:
        pass
    # Fallback: split lines on common bullet or numbered list markers
    lines = [line.strip("\- ") for line in response.split("\n") if line.strip()]
    # Remove numbering prefixes such as "1." or "-"
    suggestions = []
    for line in lines:
        # Remove numeric prefixes
        cleaned = line
        # Remove leading digits and punctuation
        cleaned = cleaned.lstrip()
        # If the cleaned line contains more than 2 words, consider it a suggestion
        if cleaned:
            suggestions.append(cleaned)
    return suggestions[:4]


def _generate_followup_suggestions(df: pd.DataFrame, question: str, sql: str) -> List[str]:
    """
    Generate a list of follow‑up questions using an LLM based on the
    current query's result and context.

    The function takes a subset of the DataFrame (up to 100 rows) and
    formats it into CSV. It then constructs a prompt instructing the
    LLM to propose follow‑up questions that refine or extend the
    analysis. The response is parsed into a list of suggestions.

    Parameters
    ----------
    df : pandas.DataFrame
        The DataFrame containing query results.
    question : str
        The natural language question originally asked.
    sql : str
        The SQL query executed to produce the DataFrame.

    Returns
    -------
    List[str]
        A list of suggested follow‑up questions.
    """
    # Prepare a preview of the DataFrame
    preview_df = df.copy()
    if len(preview_df) > 100:
        preview_df = preview_df.head(100)
    csv_data = preview_df.to_csv(index=False)
    column_list = ", ".join([str(col) for col in df.columns])

    prompt = f"""
You are an expert data analyst assistant. Your task is to propose the next logical questions
that a user might ask after seeing the results of a SQL query. Consider the original
question, the generated SQL, the column names, and a preview of the result set. Your goal
is to suggest 3 or 4 follow‑up questions that help the user explore the data further. These
questions should refine, drill down, compare, or aggregate the information shown.

Original Question: {question}
Generated SQL: {sql}
Result Columns: {column_list}
Preview of result data (CSV):
{csv_data}

Respond with a JSON object containing a key "follow_up_questions" whose value is an array of
your suggested questions. Each suggested question should be concise and stand alone.

Example response:
{{
  "follow_up_questions": [
    "Group the products by category and show their average ratings.",
    "Filter the results to products with more than 500 reviews.",
    "Compare the average discounted price versus the actual price by category."
  ]
}}
"""

    raw_response = call_ai_inference_endpoint(prompt)
    return _parse_suggestions(raw_response)


def render_followup_suggestions_tab() -> None:
    """
    Render the Follow‑Up Suggestions tab in Streamlit.

    The tab provides a dropdown to select a previous query from the
    session's history. Upon clicking the **Generate Suggestions** button,
    the underlying SQL is re‑executed to obtain the data, and the LLM
    generates follow‑up question prompts. Each suggestion can be
    inserted back into the query input via a button.
    """
    st.header("✨ Follow‑Up Question Suggestions")
    st.caption(
        "Select a previously executed query to generate intelligent follow‑up questions "
        "that will help you dive deeper into your dataset."
    )

    history: List[dict] = st.session_state.get("history", [])  # type: ignore
    if not history:
        st.info("Run at least one query to see follow‑up suggestions.")
        return

    # Build selection options from history, newest first
    options = []
    labels = []
    for item in reversed(history):
        options.append(item)
        labels.append(f"{item['question']} (ran at {item['time']})")

    selected_idx = st.selectbox(
        "Choose a query to analyze", options=list(range(len(options))), format_func=lambda i: labels[i]
    )
    selected_item = options[selected_idx]
    question = selected_item.get("question", "")
    sql = selected_item.get("sql", "")

    with st.expander("Show generated SQL", expanded=False):
        st.code(sql, language="sql")

    if st.button("Generate Follow‑Up Suggestions", key="generate_followups_button"):
        with st.spinner("Running query and generating suggestions…"):
            try:
                validate_sql(sql)
                df = run_sql(sql)
            except Exception as e:
                st.error(f"Error executing query: {e}")
                return

            try:
                suggestions = _generate_followup_suggestions(df, question=question, sql=sql)
            except Exception as e:
                st.error(f"AI failed to generate suggestions: {e}")
                return

            if not suggestions:
                st.warning("The AI could not generate follow‑up questions.")
                return

            st.subheader("Suggested Follow‑Up Questions")
            for idx, suggestion in enumerate(suggestions):
                col = st.columns([8, 2])  # 80/20 split for text and button
                with col[0]:
                    st.markdown(f"{idx + 1}. {suggestion}")
                with col[1]:
                    if st.button("Use this", key=f"use_suggestion_{idx}"):
                        # Insert the suggestion back into the query input area
                        st.session_state.prefill = suggestion
                        st.success("Suggestion added to query input! Scroll back to the query box.")
