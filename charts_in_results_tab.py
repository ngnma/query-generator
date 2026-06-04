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
import matplotlib.pyplot as plt
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
    # Bar and pie charts if at least one numeric and one categorical column
    if numeric_cols and categorical_cols:
        x_col = categorical_cols[0]
        y_col = numeric_cols[0]
        # Aggregate by category (sum of numeric)
        try:
            bar_data = data[[x_col, y_col]].dropna()
            grouped = bar_data.groupby(x_col)[y_col].sum().reset_index()
        except Exception:
            grouped = data[[x_col, y_col]].dropna()
        # Bar chart
        fig_bar, ax_bar = plt.subplots()
        ax_bar.bar(grouped[x_col], grouped[y_col])
        ax_bar.set_xlabel(x_col)
        ax_bar.set_ylabel(y_col)
        ax_bar.set_title(f"Sum of {y_col} by {x_col}")
        plt.xticks(rotation=45, ha="right")
        st.pyplot(fig_bar)
        rendered_any = True
        # Pie chart
        fig_pie, ax_pie = plt.subplots()
        ax_pie.pie(grouped[y_col], labels=grouped[x_col], autopct="%1.1f%%")
        ax_pie.set_title(f"Distribution of {y_col} by {x_col}")
        st.pyplot(fig_pie)
    # Scatter chart if at least two numeric columns exist
    if len(numeric_cols) >= 2:
        x_num = numeric_cols[0]
        y_num = numeric_cols[1]
        fig_scatter, ax_scatter = plt.subplots()
        ax_scatter.scatter(data[x_num], data[y_num])
        ax_scatter.set_xlabel(x_num)
        ax_scatter.set_ylabel(y_num)
        ax_scatter.set_title(f"Scatter Plot: {y_num} vs {x_num}")
        st.pyplot(fig_scatter)
        rendered_any = True
    # Line chart if a date/time column exists
    date_col = _detect_date_column(data)
    if date_col and numeric_cols:
        y_dt = numeric_cols[0]
        dt_data = data[[date_col, y_dt]].dropna().sort_values(date_col)
        fig_line, ax_line = plt.subplots()
        ax_line.plot(dt_data[date_col], dt_data[y_dt])
        ax_line.set_xlabel(date_col)
        ax_line.set_ylabel(y_dt)
        ax_line.set_title(f"Trend of {y_dt} over {date_col}")
        plt.xticks(rotation=45, ha="right")
        st.pyplot(fig_line)
        rendered_any = True
    if not rendered_any:
        st.warning("No suitable numeric or categorical columns found to generate charts.")
