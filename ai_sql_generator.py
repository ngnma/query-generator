import json
import oci
import oracledb
from oci.generative_ai_inference import GenerativeAiInferenceClient
from oci.generative_ai_inference.models import OnDemandServingMode, ChatDetails, CohereChatRequest

# ==========================================
# DATABASE CREDENTIALS (FOR EXTRACTING RAG)
# ==========================================
DB_USER = "ADMIN"
DB_PASSWORD = "YourDBPasswordHere"
DB_DSN = "your_db_high_or_medium_service_name_spec"

def call_ai_inference_endpoint(prompt_payload):
    """
    Internal helper to execute the raw network invocation call to the OCI AI platform.
    """
    signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
    gen_ai_client = GenerativeAiInferenceClient(
        config={},
        signer=signer,
        service_endpoint="https://inference.generativeai.uk-london-1.oci.oraclecloud.com"
    )
    compartment_id = "ocid1.tenancy.oc1..aaaaaaaapigjcw7dwdp6onerp5wqcu3z5pzsckmokdiqjezvoodfi2corv6q"
    model_id = "cohere.command-r-plus-08-2024"

    chat_request = CohereChatRequest()
    chat_request.message = prompt_payload
    chat_request.max_tokens = 500
    chat_request.temperature = 0.0

    chat_detail = ChatDetails()
    chat_detail.compartment_id = compartment_id
    chat_detail.serving_mode = OnDemandServingMode(model_id=model_id)
    chat_detail.chat_request = chat_request

    response = gen_ai_client.chat(chat_detail)
    raw_text = response.data.chat_response.text.strip()
    
    # Clean formatting strings
    raw_text = raw_text.replace("```json", "").replace("```", "").strip()
    raw_text = raw_text.replace("\n", " ").replace("\r", " ")
    return raw_text


def get_query_embedding(user_prompt_string):
    """
    Helper function to turn the user query text into a stringified JSON array vector
    using the OCI Cohere v3 embedding engine.
    """
    signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
    gen_ai_client = GenerativeAiInferenceClient(
        config={},
        signer=signer,
        service_endpoint="https://inference.generativeai.uk-london-1.oci.oraclecloud.com"
    )
    compartment_id = "ocid1.tenancy.oc1..aaaaaaaapigjcw7dwdp6onerp5wqcu3z5pzsckmokdiqjezvoodfi2corv6q"
    
    embed_request = oci.generative_ai_inference.models.EmbedTextDetails(
        inputs=[user_prompt_string],
        serving_mode=oci.generative_ai_inference.models.OnDemandServingMode(
            model_id="cohere.embed-english-v3.0"
        ),
        compartment_id=compartment_id,
        input_type="SEARCH_QUERY"  # Tells Cohere this is a lookup prompt
    )
    
    response = gen_ai_client.embed_text(embed_request)
    raw_vector_array = response.data.embeddings[0]
    return json.dumps(raw_vector_array)


def run_conversational_loop():
    print("\n--- Starting Natural Language Query Loop ---")
    initial_prompt = input("Enter your database query or descriptive concept: ")
    
    conversation_history = f"Initial User Query: {initial_prompt}"
    loop_active = True
    follow_up_count = 0  

    while loop_active:
        force_generation = "false"
        if follow_up_count >= 3:
            force_generation = "true"

        prompt_payload = f"""
        You are an expert Oracle SQL architect and natural language classifier.
        
        Your task is to analyze the user's inquiry stream. You must determine if the total context accumulated across the conversation history is specific enough to build a definitive Oracle SQL query.

        Database Schema:
        Table name: amazon
        Columns:
        - product_id (VARCHAR2)
        - product_name (VARCHAR2)
        - category (VARCHAR2)
        - discounted_price (VARCHAR2)
        - actual_price (VARCHAR2)
        - discount_percentage (VARCHAR2)
        - rating (VARCHAR2)
        - rating_count (VARCHAR2)
        - about_product (VARCHAR2)
        - user_id (VARCHAR2)
        - user_name (VARCHAR2)
        - review_id (VARCHAR2)
        - review_title (VARCHAR2)
        - review_content (VARCHAR2)
        - img_link (VARCHAR2)
        - product_link (VARCHAR2)
        - product_vector_clob (CLOB) -> Stores stringified float array vectors.

        CRITICAL RAG RULE:
        If the user is describing features, qualities, feelings, use-cases, or abstract concepts (e.g., 'good for traveling', 'comfortable workout gear', 'cheap gaming setup') instead of explicit relational column filters, you MUST generate a Vector RAG query using the custom math function below.

        Vector Search Syntax Rule:
        To calculate similarity scores, you must structure the select query exactly like this:
        SELECT product_name, discounted_price, rating, CALCULATE_COSINE_SIMILARITY(product_vector_clob, 'PLACEHOLDER_VECTOR') AS similarity_score FROM amazon WHERE product_vector_clob IS NOT NULL ORDER BY similarity_score DESC FETCH FIRST 5 ROWS ONLY;

        HARD GRADUATION RULE:
        Is force_generation equal to true? [Value: {force_generation}]
        If force_generation is true, you MUST set "status": "success" and output your absolute best guess SELECT query using the columns available.
        
        Rules for Classification (If force_generation is false):
        1. If context is missing clear metrics and isn't a descriptive concept search, set "status": "ambiguous" and provide a follow-up question in "follow_up_message". Leave "sql" as null.
        2. If specific enough, set "status": "success", "follow_up_message": null, and generate the valid Oracle SQL string in "sql".
        
        SQL Generation Rules:
        - Use Oracle SQL syntax. FETCH FIRST N ROWS ONLY instead of LIMIT.
        - Always use TO_NUMBER(REGEXP_REPLACE(column_name, '[^0-9.]', '')) when filtering or sorting numeric columns.
        
        You MUST respond with a raw JSON object matching this structure exactly:
        {{
            "status": "success" or "ambiguous",
            "follow_up_message": "Clarification question text here if ambiguous, otherwise null",
            "sql": "The generated SQL query here if success, otherwise null"
        }}
        
        [CONVERSATION HISTORY TRACKER]
        {conversation_history}
        
        Output:
        """

        try:
            raw_response = call_ai_inference_endpoint(prompt_payload)
            result_data = json.loads(raw_response, strict=False)
            
            if result_data.get("status") == "success" or force_generation == "true":
                generated_sql = result_data.get('sql')
                print("\n🎉 Success! SQL generated natively.")
                
                # --- HYBRID ROUTER DETECTION ---
                # Check if the generated SQL requires dynamic runtime Vector embedding injections
                if "PLACEHOLDER_VECTOR" in generated_sql:
                    print("[RAG] Vector query signature recognized! Converting user search string to dynamic float array coordinates...")
                    # Extract the original user string or final context block to build coordinates
                    query_vector_string = get_query_embedding(initial_prompt)
                    # Dynamically patch the string token placeholder with the live math vector block
                    final_executable_sql = generated_sql.replace("'PLACEHOLDER_VECTOR'", f"'{query_vector_string}'")
                else:
                    final_executable_sql = generated_sql

                print(f"Executable SQL: {final_executable_sql}\n")
                
                # --- LIVE ACTION TEST RUN ---
                try:
                    print("[Database] Fetching direct query matches...")
                    connection = oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=DB_DSN)
                    cursor = connection.cursor()
                    cursor.execute(final_executable_sql)
                    db_rows = cursor.fetchall()
                    
                    print("\n📦 --- RETURNED INVENTORY RECORDS --- 📦")
                    for r in db_rows[:5]:
                        print(r)
                    cursor.close()
                    connection.close()
                except Exception as db_err:
                    print(f"⚠️ Live DB evaluation warning: {db_err}")

                conversation_history += f"\nFinal Generated SQL Statement: {final_executable_sql}"
                loop_active = False
                return True, conversation_history
                
            else:
                follow_up_count += 1
                print(f"\n🤖 Follow-up Question from AI ({follow_up_count}/3): {result_data.get('follow_up_message')}")
                user_clarification = input("Your response: ")
                conversation_history += f"\nAI Clarification Question Asked: {result_data.get('follow_up_message')}\nUser Clarification Answer Provided: {user_clarification}"
                
        except Exception as e:
            print(f"\n⚠️ Structural Parsing Exception hit: {e}. Defaulting emergency crash exit.")
            return True, conversation_history

if __name__ == "__main__":
    run_conversational_loop()
