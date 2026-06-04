# 🔍 QueryLens — AI-Powered NL2SQL Agent

> Turn plain English questions into validated Oracle SQL queries, execute them live, and explore results through charts, insights, and a conversational assistant.

---

## Overview

**QueryLens** is an AI-powered natural language to SQL (NL2SQL) agent built for Oracle databases. It leverages OCI Generative AI to interpret user questions, generate syntactically correct Oracle SQL, validate and execute queries, and present results through an interactive Streamlit interface with charts, AI-generated insights, and a multi-turn chatbot.

Originally built for the **IADS Hackathon**.

---

## Features

- **Natural Language → Oracle SQL** — Ask questions in plain English; the agent generates clean, validated Oracle SQL.
- **Clarification Flow** — If a query is ambiguous, the agent asks targeted follow-up questions (up to 3 rounds) before generating SQL.
- **Live Query Execution** — Queries are validated and executed against a live Oracle database.
- **Results Tab** — View tabular results and download as CSV.
- **Insights Tab** — AI-generated SQL explanation, auto-charts, and descriptive statistics.
- **Dynamic Charts Tab** — Additional interactive visualisations of query results.
- **Chat Assistant Tab** — Multi-turn conversational SQL assistant with context memory.
- **AI Insights Tab** — Analytical observations (patterns, trends, anomalies) from past query results.
- **Follow-Up Suggestions Tab** — AI-generated follow-up questions based on query history.
- **Query History Sidebar** — View, re-run, and manage previous queries.

---

## Project Structure

```
query-generator/
├── app.py                        # Main Streamlit application entry point
├── ai_sql_generator.py           # OCI Generative AI inference endpoint wrapper
├── validator.py                  # SQL validation logic
├── db.py                         # Oracle database connection and query execution
├── sql_explanation.py            # AI-generated SQL explanation
├── chat_tab.py                   # Multi-turn chat assistant tab
├── insight_tab.py                # AI Insights tab
├── insightful_charts_tab.py      # Insightful charts rendering
├── charts_in_results_tab.py      # Dynamic charts in results tab
├── followup_suggestions_tab.py   # Follow-up query suggestions tab
├── populate_vectors.py           # Vector store population (for RAG/semantic search)
├── DemiApp.py                    # Alternate/demo app version
├── Demi_App.py                   # Alternate/demo app version
└── .gitignore
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | [Streamlit](https://streamlit.io/) |
| AI Backend | OCI Generative AI (Oracle Cloud) |
| Database | Oracle DB (via `oracledb`) |
| Language | Python 3 |

---

## Getting Started

### Prerequisites

- Python 3.9+
- Access to an Oracle database
- OCI Generative AI credentials configured

### Installation

```bash
git clone https://github.com/ngnma/query-generator.git
cd query-generator
pip install -r requirements.txt
```

### Configuration

Set up your OCI and Oracle DB credentials as environment variables or within your OCI config file. Update connection details in `db.py` and endpoint configuration in `ai_sql_generator.py` as needed.

### Run

```bash
streamlit run app.py
```

---

## Usage

1. Type a natural language question about the Amazon sales dataset (e.g. *"Show me the top 5 products with the most reviews"*).
2. Click **Run Query**. If the question is ambiguous, answer the clarifying question(s).
3. Explore results across the **Results**, **Insights**, **SQL**, and **Charts** tabs.
4. Use the **Chat Assistant** for multi-turn exploration, the **AI Insights** tab for analytical summaries, and **Follow-Up Suggestions** to dig deeper.
5. Re-run or review past queries from the **Query History** sidebar.

---

## Database Schema

The agent is pre-configured for an `amazon` table with the following columns:

`product_id`, `product_name`, `category`, `discounted_price`, `actual_price`, `discount_percentage`, `rating`, `rating_count`, `about_product`, `user_id`, `user_name`, `review_id`, `review_title`, `review_content`, `img_link`, `product_link`

---

## Acknowledgements

- Built at the **IADS Hackathon**
- Forked from [nmakoui/nl-query-agent](https://github.com/nmakoui/nl-query-agent)
