import streamlit as st # Streamlit is our frontend framework. It turns Python scripts into web apps.
from ai_sql_generator import process_interactive_query # The backend team's AI function that returns (Flag, Output)
from validator import validate_sql # Our safety check to make sure no one deletes the database
from db import run_sql # The function that actually connects to Oracle Cloud Infrastructure (OCI)

#the map (schema)
# We store this as a multi-line string. The backend uses this to know what columns exist.
SCHEMA_TEXT = """
Table: AMAZON_SALES
Columns:
- ORDER_ID
- ORDER_DATE
- SHIP_DATE
- REGION
- COUNTRY
- CITY
- CATEGORY
- PRODUCT_NAME
- SALES
- QUANTITY
- PROFIT
- DISCOUNT
"""

#managing memory
def manage_clarification(user_input):
    """
    Streamlit runs from top to bottom every time a button is clicked. 
    Because of this, it forgets everything that happened a second ago.
    'st.session_state' is used as a permanent memory bank so it remembers the conversation.
    """
    
    # 1. INITIALIZE MEMORY
    # Check if this is a brand new question. 
    # If "current_q" isn't in memory, or if the user typed a totally new question in the main box...
    if "current_q" not in st.session_state or st.session_state.get("original_q") != user_input:
        
        # ...we save their exact text into our memory bank.
        st.session_state.original_q = user_input # Saves the first thing they asked
        st.session_state.current_q = user_input  # This one will grow as we add follow-up answers
        st.session_state.conversation_history = f"Initial User Query: {user_input}"
        st.session_state.follow_up_count = 0
        # st.spinner() pauses the app and shows a spinning loading wheel to the user.
        # Everything indented under 'with st.spinner' happens while the wheel is spinning.
        with st.spinner("Analyzing request..."):
            
            # We call the backend team's function. 
            # is_ready = True/False. response = The SQL string OR the follow-up question.
            evaluate_ai_response()
            
        # Save the AI's answers into memory so we don't lose them when the page refreshed

    # 2. SUCCESS SCENARIO
    # If the backend returned True (it generated SQL), we immediately return that SQL string to the main app.
    if st.session_state.is_ready:
        return True, st.session_state.ai_message, st.session_state.conversation_history

    # 3. FOLLOW-UP SCENARIO (Flag was False)
    # st.info() draws a blue, highlighted alert box on the screen to grab the user's attention.
    st.info(f"**Clarification Needed ({st.session_state.follow_up_count + 1}/3):** {st.session_state.ai_message}")
    
    # st.text_input() draws a text box for the user to type their clarification.
    # The 'key' argument forces Streamlit to uniquely identify this specific input box.
    user_answer = st.text_input("Your answer:", key="followup_input")
    
    # Check if the user clicked the submit button AND actually typed something in the box.
    if st.button("Submit Clarification") and user_answer:
        st.session_state.conversation_history += f"\nAI Clarification Question Asked: {st.session_state.ai_message}\nUser Clarification Answer Provided: {user_answer}"
        st.session_state.follow_up_count +=1
        
        # We take their original question from memory and attach their new answer to the end of it.
        # Example: "Show me sales." + " For 2026." = "Show me sales. For 2026."
        
        # Show the loading wheel again while we send the new, longer question back to the AI.
        with st.spinner("Re-evaluating..."):
            evaluate_ai_response()
        # Update our memory with the newest AI evaluation
        
        # st.rerun() is the magic command! It tells Streamlit: "Stop what you are doing, 
        # go back to line 1 of this whole file, and redraw the entire webpage using the new memory."
        st.rerun() 

    # If the AI isn't ready, and the user hasn't successfully submitted a clarification yet,
    # we return None. This prevents the main app from trying to run the database query.
    return False, None, st.session_state.conversation_history


#building the web

# st.title() prints a massive header at the top of the webpage.
st.title("Natural Language Query Agent")

# This is the main input box where the user starts the whole process.
user_question = st.text_input("Ask a question about the Amazon sales data:")

# st.button() creates a clickable button. It returns True if clicked.
# The 'or' statement ensures that if we are currently stuck in a follow-up loop, 
# the app keeps running this block even if they didn't explicitly click "Run Query" again.
if st.button("Run Query") or st.session_state.get("original_q") == user_question:
    
    # Basic validation: If the user clicked the button but left the box empty...
    if not user_question:
        # st.warning() draws a yellow alert box telling them to fix it.
        st.warning("Please enter a question.")
    
    else:
        # try/except is a Python safety net. If anything crashes inside the 'try' block,
        # it instantly jumps to 'except' instead of crashing the whole webpage.
        try:
            # 1. Call our helper function above. It will either return a SQL string, or None.
            final_sql = manage_clarification(user_question)

            # 2. If 'final_sql' actually has data in it (meaning the AI gave us a True flag)...
            if final_sql:
                
                # st.subheader() draws a medium-sized title on the page.
                st.subheader("Generated SQL")
                
                # st.code() formats the string to look exactly like a hacker/code block on the screen.
                # language="sql" adds proper color highlighting to SELECT, FROM, WHERE, etc.
                st.code(final_sql, language="sql")
                
                # Run our safety check function. If it detects "DROP TABLE", it raises an error.
                validate_sql(final_sql)
                
                # Turn on the loading wheel while Oracle does the heavy lifting.
                with st.spinner("Running query on Oracle Database..."):
                    # Call the OCI connection file to get the data format (usually a Pandas DataFrame).
                    result_df = run_sql(final_sql)
                    
                st.subheader("Query Result")
                
                # st.dataframe() takes raw spreadsheet/table data and draws an interactive, 
                # scrollable table right on the webpage.
                st.dataframe(result_df)
                
        # If any function above crashes (like the database goes offline or validate_sql fails),
        # it catches the error (e) here.
        except Exception as e:
            # st.error() draws a red alert box displaying the exact crash reason to the user.
            st.error(f"Error: {e}")
