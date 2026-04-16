"""
Twilio Voice Complaint System
- Takes complaint description via voice
- Records user location via voice
- Stores data in SQLite database
- Supports multiple languages via Gemini API
"""

import os
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, Request
from fastapi.responses import Response
from twilio.twiml.voice_response import VoiceResponse
from twilio.rest import Client
import google.generativeai as genai
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent / ".env")

# ============ CONFIGURATION ============
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CALLBACK_URL = os.getenv("CALLBACK_URL", "http://localhost:8000")

# Initialize Twilio client lazily so app can start even if test-call creds are missing.
twilio_client: Optional[Client] = None


def get_twilio_client() -> Client:
    """Create Twilio client only when needed."""
    global twilio_client

    if twilio_client is not None:
        return twilio_client

    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        raise RuntimeError(
            "Missing Twilio credentials. Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN in .env"
        )

    twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    return twilio_client

# Initialize Gemini API
genai.configure(api_key=GEMINI_API_KEY)

# Database configuration
DB_FILE = "complaints.db"

# FastAPI app
app = FastAPI()

# ============ DATABASE SETUP ============

def init_database():
    """Initialize SQLite database for complaints"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS complaints (
            id TEXT PRIMARY KEY,
            phone_number TEXT NOT NULL,
            complaint_audio_url TEXT,
            complaint_text TEXT,
            complaint_language TEXT,
            location_audio_url TEXT,
            location_text TEXT,
            location_language TEXT,
            status TEXT DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS call_sessions (
            session_id TEXT PRIMARY KEY,
            phone_number TEXT NOT NULL,
            complaint_id TEXT,
            call_duration INTEGER,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ended_at TIMESTAMP,
            FOREIGN KEY (complaint_id) REFERENCES complaints(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS session_context (
            session_id TEXT PRIMARY KEY,
            complaint_text TEXT,
            complaint_language TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()
    print("✓ Database initialized")

# ============ HELPER FUNCTIONS ============

async def extract_text_from_audio(audio_url: str, language_code: str = "en") -> Optional[str]:
    """
    Download audio from URL and extract text using Gemini API
    Supports speech-to-text conversion
    """
    try:
        # Download audio file
        audio_response = requests.get(audio_url, timeout=10)
        if audio_response.status_code != 200:
            print(f"Failed to download audio: {audio_url}")
            return None
        
        # Use Gemini API to process audio
        # Note: For production, consider using Google Cloud Speech-to-Text API
        # This is a placeholder for audio processing
        
        print(f"Audio downloaded from: {audio_url}")
        return audio_url  # Return URL for now, can enhance with transcription later
        
    except Exception as e:
        print(f"Error extracting text from audio: {e}")
        return None

def detect_language(text: str) -> str:
    """Detect language of the text using Gemini API"""
    try:
        model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content(
            f"Detect the language of this text and return only the language code (e.g., 'en', 'hi', 'es'): {text}"
        )
        return response.text.strip()
    except Exception as e:
        print(f"Error detecting language: {e}")
        return "unknown"

def translate_text(text: str, target_language: str = "en") -> str:
    """Translate text to target language using Gemini API"""
    try:
        model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content(
            f"Translate this text to {target_language}: {text}"
        )
        return response.text.strip()
    except Exception as e:
        print(f"Error translating text: {e}")
        return text

def save_complaint_to_db(
    phone_number: str,
    complaint_audio_url: str,
    complaint_text: str,
    complaint_language: str,
    location_audio_url: str,
    location_text: str,
    location_language: str,
    session_id: str
) -> str:
    """Save complaint data to SQLite database"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        complaint_id = str(uuid.uuid4())
        
        cursor.execute("""
            INSERT INTO complaints (
                id,
                phone_number,
                complaint_audio_url,
                complaint_text,
                complaint_language,
                location_audio_url,
                location_text,
                location_language,
                status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            complaint_id,
            phone_number,
            complaint_audio_url,
            complaint_text,
            complaint_language,
            location_audio_url,
            location_text,
            location_language,
            "Pending"
        ))
        
        # Update session
        cursor.execute("""
            UPDATE call_sessions
            SET complaint_id = ?
            WHERE session_id = ?
        """, (complaint_id, session_id))
        
        conn.commit()
        conn.close()
        
        print(f"✓ Complaint saved with ID: {complaint_id}")
        return complaint_id
        
    except Exception as e:
        print(f"Error saving complaint to database: {e}")
        return None

def create_call_session(phone_number: str) -> str:
    """Create a new call session"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        session_id = str(uuid.uuid4())
        
        cursor.execute("""
            INSERT INTO call_sessions (session_id, phone_number)
            VALUES (?, ?)
        """, (session_id, phone_number))
        
        conn.commit()
        conn.close()
        
        return session_id
        
    except Exception as e:
        print(f"Error creating call session: {e}")
        return None


def save_session_context(session_id: str, complaint_text: str, complaint_language: str = "unknown"):
    """Store temporary complaint context for the active call session."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO session_context (session_id, complaint_text, complaint_language, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(session_id) DO UPDATE SET
                complaint_text=excluded.complaint_text,
                complaint_language=excluded.complaint_language,
                updated_at=CURRENT_TIMESTAMP
        """, (session_id, complaint_text, complaint_language))

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error saving session context: {e}")


def get_session_context(session_id: str):
    """Fetch temporary complaint context for the active call session."""
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT complaint_text, complaint_language FROM session_context WHERE session_id = ?",
            (session_id,)
        )
        row = cursor.fetchone()
        conn.close()
        if not row:
            return "", "unknown"
        return row["complaint_text"] or "", row["complaint_language"] or "unknown"
    except Exception as e:
        print(f"Error fetching session context: {e}")
        return "", "unknown"


def clear_session_context(session_id: str):
    """Delete temporary complaint context once complaint is saved."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM session_context WHERE session_id = ?", (session_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error clearing session context: {e}")

def get_greeting_message(language: str = "en") -> str:
    """Get greeting message based on language"""
    greetings = {
        "en": "Welcome to our complaint registration system. Please describe your complaint after the beep.",
        "hi": "हमारी शिकायत पंजीकरण प्रणाली में स्वागत है। कृपया बीप के बाद अपनी शिकायत का वर्णन करें।",
        "es": "Bienvenido a nuestro sistema de registro de quejas. Por favor, describa su queja después del pitido.",
        "fr": "Bienvenue dans notre système d'enregistrement des plaintes. Veuillez décrire votre plainte après le bip.",
    }
    return greetings.get(language, greetings["en"])

def get_location_message(language: str = "en") -> str:
    """Get location request message based on language"""
    messages = {
        "en": "Thank you. Please tell us your location or nearby landmark after the beep.",
        "hi": "धन्यवाद। कृपया बीप के बाद अपना स्थान या नजदीकी स्थान बताएं।",
        "es": "Gracias. Por favor, díganos su ubicación o punto de referencia cercano después del pitido.",
        "fr": "Merci. Veuillez nous dire votre localisation ou un point de repère à proximité après le bip.",
    }
    return messages.get(language, messages["en"])

def get_confirmation_message(language: str = "en") -> str:
    """Get confirmation message based on language"""
    messages = {
        "en": "Your complaint has been registered successfully. Thank you for using our service. Goodbye.",
        "hi": "आपकी शिकायत सफलतापूर्वक दर्ज हो गई है। हमारी सेवा का उपयोग करने के लिए धन्यवाद। अलविदा।",
        "es": "Su queja ha sido registrada con éxito. Gracias por usar nuestro servicio. Adiós.",
        "fr": "Votre plainte a été enregistrée avec succès. Merci d'avoir utilisé notre service. Au revoir.",
    }
    return messages.get(language, messages["en"])

# ============ TWILIO VOICE WEBHOOKS ============

@app.post("/voice")
async def voice_webhook(request: Request):
    """
    Main voice webhook - answers call and starts complaint recording
    """
    form = await request.form()
    phone_number = form.get("From") or "unknown"
    
    # Create session
    session_id = create_call_session(phone_number)
    
    # Generate TwiML response
    response = VoiceResponse()
    
    # Ask caller to speak complaint description.
    gather = response.gather(
        input="speech",
        action=f"/recording_complaint?session_id={session_id}",
        method="POST",
        language="en-IN",
        speech_timeout="auto",
    )
    gather.say("Welcome to our complaint registration system.")
    gather.say("Please describe your complaint in detail after the beep.")

    # If speech is not captured, restart the flow.
    response.say("We did not receive your complaint. Let us try again.")
    response.redirect("/voice", method="POST")
    
    return Response(content=str(response), media_type="application/xml")


@app.post("/recording_complaint")
async def recording_complaint(request: Request):
    """
    Process complaint speech and ask for location
    """
    form = await request.form()
    session_id = request.query_params.get("session_id")

    complaint_text = (form.get("SpeechResult") or "").strip()
    from_number = form.get("From") or "unknown"

    print(f"Session: {session_id}")
    print(f"Complaint Text: {complaint_text}")
    print(f"Caller: {from_number}")

    response = VoiceResponse()

    if not complaint_text:
        retry = response.gather(
            input="speech",
            action=f"/recording_complaint?session_id={session_id}",
            method="POST",
            language="en-IN",
            speech_timeout="auto",
        )
        retry.say("Sorry, we did not catch your complaint. Please repeat your complaint after the beep.")
        response.redirect("/voice", method="POST")
        return Response(content=str(response), media_type="application/xml")

    complaint_language = detect_language(complaint_text)
    save_session_context(session_id, complaint_text, complaint_language)

    # Generate response
    location_gather = response.gather(
        input="speech",
        action=f"/recording_location?session_id={session_id}",
        method="POST"
    )
    location_gather.say("Thank you. Please tell us your nearby location or landmark after the beep.")

    response.say("We did not receive your location. Let us try again.")
    response.redirect(f"/recording_complaint?session_id={session_id}", method="POST")
    
    return Response(content=str(response), media_type="application/xml")


@app.post("/recording_location")
async def recording_location(request: Request):
    """
    Process location speech and save to database
    """
    form = await request.form()
    session_id = request.query_params.get("session_id")
    location_text = (form.get("SpeechResult") or "").strip()
    from_number = form.get("From") or "unknown"

    complaint_text, complaint_language = get_session_context(session_id)
    location_language = detect_language(location_text) if location_text else "unknown"

    print(f"Location Text: {location_text}")

    if not location_text:
        response = VoiceResponse()
        retry = response.gather(
            input="speech",
            action=f"/recording_location?session_id={session_id}",
            method="POST",
            language="en-IN",
            speech_timeout="auto",
        )
        retry.say("Sorry, we did not catch your location. Please say your nearby location after the beep.")
        return Response(content=str(response), media_type="application/xml")
    
    # Save to database
    complaint_id = save_complaint_to_db(
        phone_number=from_number,
        complaint_audio_url="",
        complaint_text=complaint_text,
        complaint_language=complaint_language,
        location_audio_url="",
        location_text=location_text,
        location_language=location_language,
        session_id=session_id
    )

    clear_session_context(session_id)
    
    # Generate confirmation response
    response = VoiceResponse()
    response.say("Your complaint has been registered successfully. Thank you for using our service.")
    response.hangup()
    
    print(f"Complaint registered with ID: {complaint_id}")
    
    return Response(content=str(response), media_type="application/xml")


@app.post("/recording_status")
async def recording_status(request: Request):
    """
    Handle recording status callbacks
    """
    form = await request.form()
    session_id = request.query_params.get("session_id")
    
    recording_status = form.get("RecordingStatus")
    recording_url = form.get("RecordingUrl")
    
    print(f"Recording Status: {recording_status}")
    print(f"Recording URL: {recording_url}")
    
    return Response(status_code=200)


# ============ DATABASE QUERY ENDPOINTS ============

@app.get("/complaints")
async def get_all_complaints():
    """Get all complaints from database"""
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM complaints ORDER BY created_at DESC")
        complaints = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return {"status": "success", "count": len(complaints), "complaints": complaints}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/complaints/pending")
async def get_pending_complaints():
    """Get pending complaints"""
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM complaints WHERE status = 'Pending' ORDER BY created_at DESC")
        complaints = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return {"status": "success", "count": len(complaints), "complaints": complaints}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/complaints/{complaint_id}")
async def get_complaint_details(complaint_id: str):
    """Get details of a specific complaint"""
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM complaints WHERE id = ?", (complaint_id,))
        complaint = cursor.fetchone()
        
        conn.close()
        
        if complaint:
            return {"status": "success", "complaint": dict(complaint)}
        else:
            return {"status": "error", "message": "Complaint not found"}
            
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.put("/complaints/{complaint_id}/status")
async def update_complaint_status(complaint_id: str, status: str):
    """Update complaint status"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE complaints
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (status, complaint_id))
        
        conn.commit()
        conn.close()
        
        return {"status": "success", "message": "Status updated"}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============ UTILITY ENDPOINTS ============

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "service": "Call Complaint System"}


@app.post("/test-call")
async def test_call(phone_number: str):
    """
    Make a test call to a phone number
    Useful for testing the webhook
    """
    try:
        if not TWILIO_PHONE_NUMBER:
            raise RuntimeError("Missing TWILIO_PHONE_NUMBER in .env")

        client = get_twilio_client()
        callback = f"{CALLBACK_URL.rstrip('/')}/voice"

        call = client.calls.create(
            to=phone_number,
            from_=TWILIO_PHONE_NUMBER,
            url=callback,
        )
        return {"status": "success", "call_sid": call.sid}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============ INITIALIZATION ============

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_database()


if __name__ == "__main__":
    import uvicorn
    
    # Initialize database
    init_database()
    
    # Start server
    uvicorn.run(app, host="0.0.0.0", port=8000)
