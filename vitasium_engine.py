import os
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from pinecone import Pinecone

load_dotenv()

# Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
EMBEDDING_KEY = os.getenv("GOOGLE_API_KEY_1")
PINECONE_KEY = os.getenv("PINECONE_API_KEY")

# Hardcoded English keywords for instant detection
EMERGENCY_KEYWORDS = [
    "chest pain", "difficulty breathing", "stroke", "unconscious", "heavy bleeding", 
    "heart attack", "poisoning", "suicide", "breathless", "seizure", "choking", "major burn", "head injury"
]

# Safe cache
def st_cache_decorator(func):
    try:
        import streamlit as st
        return st.cache_resource(func)
    except ImportError:
        return func

@st_cache_decorator
def load_vitasium_brain():
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001",  
        google_api_key=EMBEDDING_KEY
    )

    from pinecone import Pinecone
    from langchain_pinecone import PineconeVectorStore
    
    pc = Pinecone(api_key=PINECONE_KEY)
    index = pc.Index("vitasium-index")
    
    vectorstore = PineconeVectorStore(
        index=index,
        embedding=embeddings
    )

    llm = ChatGroq(
        temperature=0.1, 
        model_name="llama-3.3-70b-versatile",
        groq_api_key=GROQ_API_KEY
    )

    return vectorstore, llm

def get_vitasium_response(user_query, preferred_language="English", chat_history=""):
    """
    Handles Multi-Language Emergencies & Clinical Logic.
    """
    maps_link = "https://www.google.com/maps/search/hospitals+near+me/"
    
    # LAYER 1: Fast-Pass (English Hardcoded Keywords)
    query_lower = user_query.lower()
    if any(word in query_lower for word in EMERGENCY_KEYWORDS):
        user_query = "GLOBAL_EMERGENCY_DETECTED"

    try:
        vectorstore, llm = load_vitasium_brain()
        retriever = vectorstore.as_retriever(search_kwargs={"k": 2})

        # LAYER 2: LLM Intelligence (Handles Multi-Lingual Emergencies)
        system_prompt = (
            f"You are VITASIUM, a professional medical AI assistant.\n"
            f"STRICT RULE: You MUST respond ONLY in {preferred_language}.\n\n"
            
            "EMERGENCY PROTOCOL (CRITICAL):\n"
            "If the user query describes a life-threatening emergency (in ANY language),\n"
            "you MUST respond ONLY with the exact phrase: 'GLOBAL_EMERGENCY_DETECTED'.\n"
            "Do not provide medical advice if it is an emergency.\n\n"

            "SOURCE HIERARCHY & INSTRUCTIONS:\n"
            "1. PRIMARY SOURCE: You have access to a CURATED CLINICAL LIBRARY (Oxford Handbook of Clinical Medicine, IFRC First Aid, and Gale Encyclopedia). "
            "Synthesize info from these sources into a single, cohesive clinical answer.\n"
            "2. STYLE: Provide structured, bulleted advice when possible. Maintain a professional yet caring 'Doctor' persona.\n"
            "3. NO CITATION CLUTTER: Do not say 'According to source X' unless the user asks where the info came from. Just give the medical facts.\n"
            f"4. LANGUAGE: Respond ONLY in {preferred_language}.\n"
            "5. LIMITATION: If the provided context doesn't cover the specific condition, use your internal medical training (WHO/CDC/NIH standards) but state that you are using general clinical guidelines. "
            "If neither the book nor trusted sites have the info, say you don't have that data yet.\n\n"
            
            "CLINICAL CONTEXT:\n{context}\n\n"
            "CHAT HISTORY:\n{chat_history}\n\n"
            "USER QUERY:\n{input}"
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}"),
        ])

        from langchain.chains.combine_documents import create_stuff_documents_chain
        from langchain.chains import create_retrieval_chain

        question_answer_chain = create_stuff_documents_chain(llm, prompt)
        rag_chain = create_retrieval_chain(retriever, question_answer_chain)

        response = rag_chain.invoke({
            "input": user_query, 
            "chat_history": chat_history
        })
        
        answer = response.get("answer", "")

        # FINAL PROCESSING: If either of the detected emergency
        if "GLOBAL_EMERGENCY_DETECTED" in answer or user_query == "GLOBAL_EMERGENCY_DETECTED":
            return (
                "🚨 **URGENT MEDICAL ALERT**\n\n"
                "Symptoms of a serious medical emergency detected.\n"
                "1. **Call 112** (or local emergency services) immediately.\n"
                f"2. **Find Nearest Hospital:** [Click Here for Maps]({maps_link})\n\n"
                "Please do not wait for further AI analysis."
            )
        
        disclaimer = f"\n\n---\n*Assistance provided in {preferred_language}. For health awareness only, not a trained professional.*"
        return answer + disclaimer

    except Exception as e:
        print(f"[ENGINE ERROR] Details: {e}")

        return "TECHNICAL DIFFICULTY. TRY AGAIN LATER"
