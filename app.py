import streamlit as st
import pandas as pd

#session state persists data between reruns of the app.
#basically every time a user clicks a button, Streamlit reruns the whole script and without it the history will be delted each time
if "history" not in st.session_state:
    st.session_state.history = []

st.set_page_config(page_title = "Data Query Assistant", layout = "wide")
st.title("Data Query Assistant")
st.caption("Ask question about your data")

st.divider()

user_query = st.text_input(label = "Question", 
                           placeholder = "e.g. What were the total sales in th elast quarter broken down by region in the UK?"
                           )

run_button = st.button("Run Query")

#here a mock backed function is used since we don't have ant AI core yet, when the core is finished, this chunck will be replaced

def mock_run_query(question):
    fake_sql = "Select region, SUM(Sales_amount) AS total_sales FROM orders GROUP BY region "
    fake_df = pd.DataFrame(
        {"region": ["England", "Wales", "Scotland", "Northern Ireland"],
         "total sales": [120000, 180000,210000, 360000]}
    )
    fake_summary = (" Northern Ireland had the highest sales, "
                    "followed by Scotland, Wales and England")
    
    return{"sql": fake_sql, "results": fake_df, "summary": fake_summary, "error": None}

#this part should run when there is a button clicked and something typed
if run_button and user_query:

    with st.spinner("Generating query and fetching results..."):
        response = mock_run_query(user_query)
        #when the time comes, I'll swap it with the real thing
    if response["error"]:
        st.error(f"something went wrong: {response['error']}")
    else:
        st.session_state.history.append({
            "question": user_query, "sql": response["sql"], "summary": response["summary"]
        })
        with st.expander("view genrated sql"):
            st.code(response["sql"], language = "sql")

        st.subheader("results")
        st.dataframe(response["results"], use_container_width = True)
         # Shows the plain-English summary
        st.subheader("Summary")
        st.write(response["summary"])

        # Lets the user download the results as a CSV file
        csv = response["results"].to_csv(index=False)
        st.download_button(
            label="⬇️ Download results as CSV",
            data=csv,
            file_name="query_results.csv",
            mime="text/csv"
        )    
# This appears as a collapsible panel on the left and shows every question the user has asked this session.
with st.sidebar:
    st.header("Query History")

    if not st.session_state.history:
        st.caption("Your previous questions will appear here.")
    else:
        # Loop through history in reverse so newest is at the top
        for i, item in enumerate(reversed(st.session_state.history)):
            with st.expander(f"Q: {item['question'][:40]}..."):
                st.caption("Generated SQL:")
                st.code(item["sql"], language="sql")
                st.caption("Summary:")
                st.write(item["summary"])

        # Button to wipe the history
        if st.button("Clear history"):
            st.session_state.history = []
            st.rerun()        