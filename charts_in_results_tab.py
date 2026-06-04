"""
Dynamic Charts for Result Tabs
=============================

This module defines a function to render dynamic visualisations within
the results tab of the QueryLens application. It accepts a
DataFrame and draws various charts using matplotlib based on the
columns present. Charts include bar charts for categorical vs
numeric data, pie charts for distribution of numeric values across
categories, line charts for date/time trends, and scatter plots
when multiple numeric columns exist. If no suitable data is found,
a message is displayed instead of charts.
"""

from typing import List, Optional

import pandas as pd
# Note: matplotlib is unavailable in this environment.  We rely on
# Streamlit's built‑in chart functions (bar_chart and line_chart) instead
# of importing and using matplotlib.  If additional plotting capabilities
# become available in the future, they can be integrated here.
import streamlit as st


def _convert_numeric_columns(df: pd.DataFrame) -> List[str]:
    """
    Convert columns to numeric where possible and return the list of
    numeric columns. String columns that can be coerced to floats
    are converted in place.
    """
    numeric_cols: List[str] = []
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            numeric_cols.append(col)
        else:
            # Try to coerce object columns to numeric
            coerced = pd.to_numeric(df[col], errors="coerce")
            if coerced.notna().sum() > 0:
                df[col] = coerced
                numeric_cols.append(col)
    return numeric_cols


def _detect_date_column(df: pd.DataFrame) -> Optional[str]:
    """
    Detect a date/time column by dtype or heuristics in column names.
    Returns the column name or None if not found.
    """
    for col in df.columns:
        # Check dtype directly
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            return col
        # Heuristic: name contains date or time keywords
        name = col.lower()
        if any(keyword in name for keyword in ["date", "time", "day", "month", "year"]):
            # Try to parse at least half of the values
            try:
                parsed = pd.to_datetime(df[col], errors="coerce")
                if parsed.notna().sum() > len(df) / 2:
                    df[col] = parsed
                    return col
            except Exception:
                continue
    return None


def render_charts_in_results(df: pd.DataFrame) -> None:
    """
    Render dynamic charts within the results tab using the provided
    DataFrame. Charts are generated based on the data types present.
    """
    if df is None or df.empty:
        st.info("No data available to generate charts.")
        return
    # Work on a copy to avoid side effects
    data = df.copy()
    # Identify numeric and categorical columns
    numeric_cols = _convert_numeric_columns(data)
    categorical_cols = [col for col in data.columns if col not in numeric_cols]
    # Flag to track if any chart was rendered
    rendered_any = False
    # Bar chart (and pseudo‑pie chart) if at least one numeric and one categorical column
    if numeric_cols and categorical_cols:
        x_col = categorical_cols[0]
        y_col = numeric_cols[0]
        # Aggregate by category (sum of numeric). If grouping fails, fall back to raw data.
        try:
            bar_data = data[[x_col, y_col]].dropna()
            grouped = bar_data.groupby(x_col)[y_col].sum().reset_index()
        except Exception:
            grouped = data[[x_col, y_col]].dropna()
        if not grouped.empty:
            st.subheader(f"Sum of {y_col} by {x_col}")
            # Convert to pivot form for bar_chart (index as category)
            bar_df = grouped.set_index(x_col)[y_col]
            st.bar_chart(bar_df)
            rendered_any = True
            # Represent the distribution using another bar chart rather than a pie chart
            # to avoid unsupported pie chart rendering. Compute percentages.
            percent_series = grouped[y_col] / grouped[y_col].sum() * 100
            percent_df = pd.DataFrame({"Percentage": percent_series}).set_index(grouped[x_col])
            st.subheader(f"Percentage distribution of {y_col} by {x_col}")
            st.bar_chart(percent_df)
    # If there are at least two numeric columns, present them as a simple multi‑line chart.
    if len(numeric_cols) >= 2:
        x_num = numeric_cols[0]
        y_num = numeric_cols[1]
        # Prepare a DataFrame for multi‑line chart: using the row index as x axis
        multi_df = data[[x_num, y_num]].dropna()
        if not multi_df.empty:
            st.subheader(f"Line chart comparing {x_num} and {y_num}")
            st.line_chart(multi_df[[x_num, y_num]])
            rendered_any = True
    # If there is a date/time column and a numeric column, display a time series trend
    date_col = _detect_date_column(data)
    if date_col and numeric_cols:
        y_dt = numeric_cols[0]
        dt_data = data[[date_col, y_dt]].dropna().sort_values(date_col)
        if not dt_data.empty:
            # Create a line chart with date/time as index and numeric as value
            trend_df = dt_data.set_index(date_col)[y_dt]
            st.subheader(f"Trend of {y_dt} over {date_col}")
            st.line_chart(trend_df)
            rendered_any = True
    if not rendered_any:
        st.warning("No suitable numeric or categorical columns found to generate charts.")
