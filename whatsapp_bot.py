from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from vitasium_engine import get_vitasium_response, load_vitasium_brain
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Pre-loading for speed
print("[INIT] Booting Vitasium Brain...")
try:
    load_vitasium_brain()
    print("[INIT] Brain System Online.")
except Exception as e:
    print(f"[INIT] Critical Start-up Error: {e}")

# Session storage
user_sessions = {}

@app.route("/whatsapp", methods=['POST'])
def whatsapp_reply():
    user_msg = request.values.get('Body', '').strip()
    sender_id = request.values.get('From', '')
    resp = MessagingResponse()

    # NEW SESSION - Language Selection Request
    if sender_id not in user_sessions:
        user_sessions[sender_id] = {
            "step": "awaiting_language", 
            "language": "English", 
            "history": []
        }
        resp.message(
            "Welcome to *Vitasium*. I am your medical assistant.\n\n"
            "*What language would you like to communicate in?* (e.g., English, French, Spanish, Japanese, Tamil, Arabic)"
        )
        return str(resp)

    session = user_sessions[sender_id]

    # SETTING LANGUAGE & GENERATING NATIVE GREETING
    if session["step"] == "awaiting_language":
        session["language"] = user_msg
        session["step"] = "chatting"
        
        # Generate the SPECIFIC greeting in preferred language
        greeting_instruction = (
            f"Respond ONLY with the following greeting translated into {user_msg}: "
            f"'Hello! I am Vitasium, your medical assistant. I am now set to {user_msg}. "
            f"How can I help you today?'"
        )
        
        print(f"[LANG] Requesting {user_msg} greeting for {sender_id}")
        
        # Returns the ACTUAL text in user preferred language
        native_greeting = get_vitasium_response(greeting_instruction, preferred_language=user_msg)
        
        resp.message(native_greeting)
        return str(resp)

    # CHAT
    if session["step"] == "chatting":
        # Short history since free tier in Render
        chat_history_string = "\n".join(session["history"][-6:])
        
        try:
            # Clinical response in the user's chosen language
            ai_response = get_vitasium_response(
                user_query=user_msg, 
                preferred_language=session["language"], 
                chat_history=chat_history_string
            )

            # Update Session History
            session["history"].append(f"User: {user_msg}")
            session["history"].append(f"Vitasium: {ai_response}")
            
            # Ensuring that response doesn't exceed Twilio's character limit
            if len(ai_response) > 1550:
                ai_response = ai_response[:1550] + "..."

            resp.message(ai_response)
            print(f"[SUCCESS] Response delivered to {sender_id}")

        except Exception as e:
            print(f"[ERROR] Chat Failed: {e}")
            resp.message("Vitasium is experiencing high traffic. Please try your question again in a moment.")

        return str(resp)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)