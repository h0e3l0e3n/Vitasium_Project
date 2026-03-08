import streamlit as st
from vitasium_engine import get_vitasium_response, load_vitasium_brain

# PAGE CONFIG 
st.set_page_config(page_title="Vitasium AI", page_icon="🩺", layout="centered")

# Glassmorphism & Floating Icons
st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg,#020617,#0f172a,#020617);
    color:white;
}
.stChatMessage {
    border-radius:12px;
    padding:8px;
    border: 1px solid rgba(255,255,255,0.1);
}
.block-container {
    background: rgba(255,255,255,0.03);
    backdrop-filter: blur(10px);
    border-radius:15px;
    padding:20px;
}
.floating {
    position:fixed; top:0; left:0; width:100%; height:100%;
    pointer-events:none; z-index:-1; overflow:hidden;
}
.med {
    position:absolute; font-size:28px; opacity:0.1;
    animation: float linear infinite;
}
@keyframes float {
    0% {transform: translateY(110vh) rotate(0deg);}
    100% {transform: translateY(-10vh) rotate(360deg);}
}
.med:nth-child(1){left:10%;animation-duration:25s;}
.med:nth-child(2){left:25%;animation-duration:18s;}
.med:nth-child(3){left:40%;animation-duration:22s;}
.med:nth-child(4){left:60%;animation-duration:20s;}
.med:nth-child(5){left:75%;animation-duration:26s;}
.med:nth-child(6){left:90%;animation-duration:24s;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="floating">
    <div class="med">🧬</div><div class="med">💊</div><div class="med">🧬</div>
    <div class="med">💉</div><div class="med">🧬</div><div class="med">💊</div>
</div>
""", unsafe_allow_html=True)

# SESSION STATE
if "messages" not in st.session_state:
    st.session_state.messages = []
if "step" not in st.session_state:
    st.session_state.step = "welcome"
if "language" not in st.session_state:
    st.session_state.language = None

# SIDEBAR
with st.sidebar:
    st.header("🩺 Vitasium AI")
    st.info(f"**Current Language:** {st.session_state.language if st.session_state.language else 'Not Selected'}")
    st.markdown("""
    **Clinical Library Active:**
    - Oxford Clinical Handbook
    - IFRC First Aid
    - Gale Medical Encyclopedia
    """)
    if st.button("🔄 Reset Session"):
        for key in st.session_state.keys():
            del st.session_state[key]
        st.rerun()

st.title("🩺 Vitasium Medical AI")
st.caption("Multilingual Clinical Assistant | Emergency Response System")

# CHAT LOGIC

# WELCOME & LANGUAGE SELECTION
if st.session_state.step == "welcome":
    with st.chat_message("assistant", avatar="🩺"):
        st.markdown("Welcome to **Vitasium**.\n\nI am your AI medical assistant. **What language would you like to communicate in?**")

    if lang_input := st.chat_input("Enter language (e.g., English, French, Spanish, Japanese, Tamil, Arabic)..."):
        st.session_state.language = lang_input
        st.session_state.step = "init_greeting"
        st.rerun()

# NATIVE GREETING GENERATION
elif st.session_state.step == "init_greeting":
    with st.spinner(f"Configuring Vitasium for {st.session_state.language}..."):
        # AI to provide the translated version
        instruction = (
            f"Translate the following into {st.session_state.language} and respond ONLY with that translation: "
            f"'Hello! I am Vitasium, your medical assistant. I am now set to {st.session_state.language}. How can I help you today?'"
        )
    
        greeting = get_vitasium_response(instruction, st.session_state.language, "")
        
        st.session_state.messages.append({"role": "assistant", "content": greeting})
        st.session_state.step = "chatting"
        st.rerun()

# MAIN CHAT INTERFACE
elif st.session_state.step == "chatting":
    # Display previous messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"], avatar="🩺" if message["role"] == "assistant" else None):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ask your medical question..."):
        # Add user message to state
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Build context from last 6 messages
        history_context = ""
        for msg in st.session_state.messages[-6:]:
            history_context += f"{msg['role'].capitalize()}: {msg['content']}\n"

        # Generate AI Response
        with st.chat_message("assistant", avatar="🩺"):
            with st.spinner("Consulting Clinical Library..."):
                response = get_vitasium_response(
                    prompt, 
                    st.session_state.language, 
                    history_context
                )
                
                # Check for the Emergency Code from the engine
                if "GLOBAL_EMERGENCY_DETECTED" in response:
                    st.error("🚨 **URGENT MEDICAL ALERT**")
                    st.markdown("Symptoms of a serious medical emergency detected.")
                    st.markdown("1. **Call 112** (India) immediately.")
                    st.link_button("🏥 Find Nearest Hospital", "https://www.google.com/maps/search/hospitals+near+me/")
                else:
                    st.markdown(response)
                
                st.session_state.messages.append({"role": "assistant", "content": response})