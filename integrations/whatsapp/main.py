import os
import sys
import uuid
import socket
import mimetypes
import requests
import re
import threading
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from fastapi import FastAPI, Request, Depends, Response
from sqlalchemy.orm import Session
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client as TwilioClient

from database import Complaint, SessionLocal, get_db

# --- Firebase & NLP Setup ---
import firebase_admin
from firebase_admin import credentials, firestore, storage

load_dotenv(override=True)

# Setup NLP path
NLP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nlp_model")
if NLP_DIR not in sys.path:
    sys.path.append(NLP_DIR)
from predict_complaint_cli import load_assets, predict_complaint, resolve_device

# Initialize Firebase
cred_path = os.path.join(os.path.dirname(__file__), "civicsense-b653c-firebase-adminsdk-fbsvc-949e104fd5.json")
if not firebase_admin._apps:
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred, {
        "storageBucket": "civicsense-b653c.firebasestorage.app"
    })
db_firestore = firestore.client()
storage_bucket = storage.bucket()

# Initialize NLP Model globally to prevent reloading on each request
print("Loading NLP Model into memory...")
DEVICE = resolve_device("cpu")
NLP_MODEL_DIR = os.path.join(NLP_DIR, "model")
NLP_TOKENIZER_DIR = os.path.join(NLP_DIR, "tokenizer")
NLP_ENCODERS_PATH = os.path.join(NLP_DIR, "label_encoders.pkl")

nlp_model, nlp_tokenizer, nlp_encoders, nlp_max_length = load_assets(
    NLP_MODEL_DIR, NLP_TOKENIZER_DIR, NLP_ENCODERS_PATH, DEVICE
)
print("NLP Model loaded successfully.")
# ----------------------------

# ---------------------------------------------------------------
# Twilio REST Client (for outbound WhatsApp notifications)
# ---------------------------------------------------------------
def get_twilio_client():
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    if sid and token:
        return TwilioClient(sid, token)
    return None


def send_whatsapp_message(to_number: str, body: str, media_url: str = None):
    """Send an outbound WhatsApp message to a citizen via Twilio REST API."""
    try:
        client = get_twilio_client()
        if not client:
            print("[NOTIFY] Twilio client not available. Skipping notification.")
            return
        # Ensure the number has whatsapp: prefix
        if not to_number.startswith("whatsapp:"):
            to_number = f"whatsapp:{to_number}"
        kwargs = {
            "from_": "whatsapp:+14155238886",  # Twilio Sandbox number
            "to": to_number,
            "body": body,
        }
        if media_url:
            kwargs["media_url"] = [media_url]
        msg = client.messages.create(**kwargs)
        print(f"[NOTIFY] Sent WhatsApp to {to_number} — SID: {msg.sid}")
    except Exception as e:
        print(f"[NOTIFY] Failed to send WhatsApp message: {e}")


# ---------------------------------------------------------------
# Firestore Listener — watches TICKETS for status changes
# ---------------------------------------------------------------
_ticket_status_cache = {}  # ticketId → last known status


def get_phone_for_ticket(ticket_id: str):
    """Look up the citizen's WhatsApp phone number from the local SQLite DB."""
    db = SessionLocal()
    try:
        row = db.query(Complaint).filter(Complaint.complaint_id == ticket_id).first()
        return row.phone_number if row else None
    finally:
        db.close()


# ---------------------------------------------------------------
# Single-process mutex — only ONE uvicorn worker runs the listener
# ---------------------------------------------------------------
_listener_mutex_sock = None  # keep socket alive so it isn't GC'd
_notifications_sent_this_session = set()  # (ticket_id, status) — resets on restart


def _acquire_listener_mutex() -> bool:
    """
    Try to bind a private TCP port on localhost.
    The FIRST process to succeed owns the listener.
    The second process (uvicorn reloader watcher) fails and skips.
    """
    global _listener_mutex_sock
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
        s.bind(('127.0.0.1', 47832))  # arbitrary private port
        s.listen(1)
        _listener_mutex_sock = s  # hold reference to keep port bound
        return True
    except OSError:
        return False


def on_ticket_snapshot(doc_snapshots, changes, read_time):
    """Called by Firestore whenever any document in TICKETS changes."""
    for change in changes:
        try:
            doc = change.document
            ticket_id = doc.id
            data = doc.to_dict()
            if not data:
                continue

            new_status = data.get("status", "")
            old_status = _ticket_status_cache.get(ticket_id)

            # Cache the status so we can detect future changes
            _ticket_status_cache[ticket_id] = new_status

            # Only act on actual status transitions (skip initial population)
            if old_status is None or old_status == new_status:
                continue

            print(f"[LISTENER] Ticket {ticket_id} status changed: {old_status} → {new_status}")

            # Only notify for statuses we care about
            if new_status not in ("In Progress", "Resolved"):
                continue

            # Fetch citizen phone number from SQLite
            phone = get_phone_for_ticket(ticket_id)
            if not phone:
                print(f"[LISTENER] No phone number found for ticket {ticket_id}. Skipping.")
                continue

            # Dedup: in-memory set resets on every server restart
            # Because only ONE process runs the listener (mutex above), no cross-process duplicates
            session_key = (ticket_id, new_status)
            if session_key in _notifications_sent_this_session:
                print(f"[LISTENER] Already sent {new_status} notification for {ticket_id} this session. Skipping.")
                continue
            _notifications_sent_this_session.add(session_key)

            description = data.get("description", "your issue")

            if new_status == "In Progress":
                message = (
                    f"🛠 *Update on your complaint*\n\n"
                    f"Ticket ID: *{ticket_id}*\n"
                    f"Issue: _{description}_\n\n"
                    f"Your complaint has been assigned to an officer and is now *In Progress*. "
                    f"We'll notify you once it's resolved. Thank you for your patience!"
                )
                send_whatsapp_message(phone, message)

            elif new_status == "Resolved":
                resolution_desc = data.get("resolutionDescription", "")
                resolution_images = data.get("resolutionImageUrls", [])
                resolution_image_url = resolution_images[0] if resolution_images else None

                message = (
                    f"✅ *Your complaint has been Resolved!*\n\n"
                    f"Ticket ID: *{ticket_id}*\n"
                    f"Issue: _{description}_\n"
                )
                if resolution_desc:
                    message += f"Resolution Note: _{resolution_desc}_\n"
                message += "\nThank you for using CivicSense. Have a great day!"

                send_whatsapp_message(phone, message, media_url=resolution_image_url)

        except Exception as e:
            print(f"[LISTENER] Error processing snapshot change: {e}")


def start_firestore_listener():
    """Start the Firestore TICKETS listener — only in ONE uvicorn process."""
    if not _acquire_listener_mutex():
        print("[LISTENER] Another process already holds the listener mutex. This process will not start a listener.")
        return

    def _listen():
        print("[LISTENER] This process WON the mutex. Starting Firestore TICKETS listener...")
        collection_ref = db_firestore.collection("TICKETS")

        # Pre-load status cache AND strip stale _notified_* flags so old failed
        # runs never permanently block future notifications.
        initial_docs = collection_ref.stream()
        stale_fields_removed = 0
        for doc in initial_docs:
            d = doc.to_dict()
            if not d:
                continue
            _ticket_status_cache[doc.id] = d.get("status", "")
            # Remove any leftover _notified_* flags from previous runs
            stale = {k: firestore.DELETE_FIELD for k in d if k.startswith("_notified_")}
            if stale:
                doc.reference.update(stale)
                stale_fields_removed += len(stale)

        print(f"[LISTENER] Pre-loaded {len(_ticket_status_cache)} ticket statuses. Cleaned {stale_fields_removed} stale notification flag(s).")
        # Attach real-time listener
        collection_ref.on_snapshot(on_ticket_snapshot)
        print("[LISTENER] Firestore listener is active.")
        threading.Event().wait()  # keep thread alive

    t = threading.Thread(target=_listen, daemon=True, name="FirestoreListener")
    t.start()
    return t


# ---------------------------------------------------------------
# FastAPI lifespan — startup & shutdown
# ---------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    start_firestore_listener()
    yield
    # Shutdown (nothing to clean up; the listener thread is a daemon)
    print("[APP] Shutting down.")


app = FastAPI(lifespan=lifespan)

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

DOWNLOADS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)


def push_to_firebase(complaint: Complaint):
    """
    Run NLP classification on description and push the record to Firebase
    FireStore, alongside uploading the media to Firebase Storage.
    """
    try:
        # 1. Run NLP
        full_description = complaint.description or ""
        nlp_result = {}
        if full_description:
            preds = predict_complaint(full_description, nlp_model, nlp_tokenizer, nlp_encoders, nlp_max_length, DEVICE)
            if preds:
                nlp_result = preds[0]  # take the first part
                
        # 2. Upload image
        image_urls = []
        if complaint.media_path:
            if os.path.exists(complaint.media_path):
                import urllib.parse
                
                # Create the GCS Blob object
                blob_name = f"ticket_images/{complaint.complaint_id}{os.path.splitext(complaint.media_path)[1]}"
                blob = storage_bucket.blob(blob_name)
                
                # Injecting Firebase Storage Download token
                access_token = str(uuid.uuid4())
                metadata = {"firebaseStorageDownloadTokens": access_token}
                blob.metadata = metadata
                
                # Upload the image bytes
                blob.upload_from_filename(complaint.media_path)
                
                # Construct exactly the Firebase Client SDK URL format required by the Mobile Application
                encoded_path = urllib.parse.quote(blob_name, safe='')
                firebase_url = f"https://firebasestorage.googleapis.com/v0/b/{storage_bucket.name}/o/{encoded_path}?alt=media&token={access_token}"
                
                image_urls.append(firebase_url)
                
            elif complaint.media_path.startswith("http"):
                # Fallback: Just pass the raw Twilio URL to the app
                image_urls.append(complaint.media_path)
            
        # 3. Extract SLA securely
        res_time_str = nlp_result.get("resolution_time", "")
        sla_hours = 72
        if res_time_str:
            nums = re.findall(r'\d+', str(res_time_str))
            if nums:
                sla_hours = int(nums[0])
                
        doc_data = {
            "adjustedSlaHours": sla_hours,
            "assignedAt": firestore.SERVER_TIMESTAMP,
            "category": nlp_result.get("issue_category", "Safety"),
            "circleId": "circle_urban_dept_electricity",
            "citizenId": "dIkDBFunXYfLQtCK3OLGurYzuNf1",
            "createdAt": firestore.SERVER_TIMESTAMP,
            "currentOwnerId": "ncs4otzaKhQHHogBd3vK",
            "currentOwnerRole": "ae_elec",
            "departmentId": "dept_electricity",
            "description": full_description,
            "divisionId": "div_pune_msedcl",
            "escalationLevel": 5,
            "escalationStartLevel": 1,
            "generatedVia": "Citizen App",
            "imageUrls": image_urls,
            "isRecurrence": False,
            "latitude": float(complaint.latitude) if complaint.latitude else 0.0,
            "linkedTicketIds": [],
            "longitude": float(complaint.longitude) if complaint.longitude else 0.0,
            "nlpClassification": {
                "category": nlp_result.get("issue_category", "Safety"),
                "confidence": nlp_result.get("mean_confidence", 1.0),
                "departmentId": "dept_electricity",
                "isCriticalOverride": True,
                "method": "manual",
                "priority": nlp_result.get("priority", "Critical"),
                "slaHours": sla_hours,
                "subtype": nlp_result.get("issue_category", "Hanging electric wire"),
                "title": nlp_result.get("issue_category", "Hanging electric wire")
            },
            "officeId": "off_swargate_dept_electricity",
            "previousTicketId": "",
            "priority": nlp_result.get("priority", "Critical"),
            "rawInputText": full_description,
            "regionId": "region_swargate_dept_electricity",
            "rejectionReason": None,
            "resolvedAt": None,
            "slaHours": sla_hours,
            "slaMinutes": None,
            "status": "Assigned",
            "supervisingJEId": "QvvIuluKYCzc689jiIG8",
            "ticketId": complaint.complaint_id,
            "title": nlp_result.get("issue_category", "Hanging electric wire"),
            "updatedAt": firestore.SERVER_TIMESTAMP
        }
        db_firestore.collection("TICKETS").document(complaint.complaint_id).set(doc_data)
        print(f"Successfully pushed {complaint.complaint_id} to Firebase Firestore.")
    except Exception as e:
        print(f"Error pushing to Firebase: {e}")


@app.post("/whatsapp")
async def whatsapp_webhook(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    data = dict(form)

    from_number = data.get("From", "Unknown")
    body = data.get("Body", "").strip()
    num_media = int(data.get("NumMedia", 0))
    latitude = data.get("Latitude")
    longitude = data.get("Longitude")
    
    media_url = data.get("MediaUrl0")
    content_type = data.get("MediaContentType0", "")

    existing_complaint = db.query(Complaint).filter(
        Complaint.phone_number == from_number,
        Complaint.status != "Completed"
    ).order_by(Complaint.id.desc()).first()

    media_path = None
    complaint_id = existing_complaint.complaint_id if existing_complaint else f"CMP-{str(uuid.uuid4())[:8].upper()}"

    if num_media > 0 and media_url:
        extension = mimetypes.guess_extension(content_type) or ".jpg"
        # mimetypes sometimes returns '.jpe' for image/jpeg — force .jpg
        if extension in [".jpe", ".jfif"]:
            extension = ".jpg"
        filename = f"{complaint_id}{extension}"
        filepath = os.path.join(DOWNLOADS_DIR, filename)

        print(f"[IMAGE] Downloading media from Twilio: {media_url}")
        try:
            # Always authenticate with Twilio — unauthenticated access is unreliable
            res = requests.get(
                media_url,
                auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
                allow_redirects=True,
                timeout=30
            )
            print(f"[IMAGE] Twilio response status: {res.status_code}, Content-Type: {res.headers.get('Content-Type', 'unknown')}")

            # Verify the response is actually an image, not an HTML error page
            resp_content_type = res.headers.get("Content-Type", "")
            if res.status_code == 200 and "image" in resp_content_type:
                with open(filepath, 'wb') as f:
                    f.write(res.content)
                print(f"[IMAGE] Successfully saved image to: {filepath} ({len(res.content)} bytes)")
                media_path = filepath
            else:
                print(f"[IMAGE] Failed — status={res.status_code}, content-type={resp_content_type}")
                print(f"[IMAGE] Response preview: {res.text[:200]}")
                media_path = None
        except Exception as e:
            print(f"[IMAGE] Exception downloading image: {e}")
            media_path = None

    resp = MessagingResponse()

    if existing_complaint:
        if media_path:
            existing_complaint.media_path = media_path
        if body:
            if existing_complaint.description:
                existing_complaint.description += "\n" + body
            else:
                existing_complaint.description = body
        if latitude and longitude:
            existing_complaint.latitude = str(latitude)
            existing_complaint.longitude = str(longitude)

        db.commit()
        db.refresh(existing_complaint)

        has_media_or_desc = bool(existing_complaint.media_path or existing_complaint.description)
        has_location = bool(existing_complaint.latitude and existing_complaint.longitude)

        if has_media_or_desc and has_location:
            existing_complaint.status = "Completed"
            db.commit()
            
            # --- NLP & FIREBASE PUSH ---
            push_to_firebase(existing_complaint)
            # ---------------------------

            resp.message(f"Your complaint has been successfully registered! Complaint ID: *{existing_complaint.complaint_id}*. Thank you, we will update you on its status.")
        elif not has_location:
            existing_complaint.status = "Pending Location"
            db.commit()
            resp.message("Thanks for the details! Please drop your location (Location Pin) to fully complete the submission.")
        elif not has_media_or_desc:
            existing_complaint.status = "Pending Details"
            db.commit()
            resp.message("Thanks for the location! Please attach a photo and a brief description to complete your submission.")
        else:
            resp.message("Message received, tracking your complaint.")

    else:
        new_complaint = Complaint(
            complaint_id=complaint_id,
            phone_number=from_number,
            description=body if body else None,
            latitude=str(latitude) if latitude else None,
            longitude=str(longitude) if longitude else None,
            media_path=media_path,
            status="Pending"
        )
        db.add(new_complaint)
        db.commit()
        db.refresh(new_complaint)

        has_location = bool(new_complaint.latitude and new_complaint.longitude)
        has_media_or_desc = bool(new_complaint.media_path or new_complaint.description)

        if has_location and has_media_or_desc:
            new_complaint.status = "Completed"
            db.commit()
            
            # --- NLP & FIREBASE PUSH ---
            push_to_firebase(new_complaint)
            # ---------------------------

            resp.message(f"Your complaint has been successfully registered! Complaint ID: *{new_complaint.complaint_id}*. Thank you, we will update you on its status.")
        elif has_media_or_desc:
            new_complaint.status = "Pending Location"
            db.commit()
            resp.message("We received your photo/description. To complete the complaint, *please share your location* (Location Pin) now.")
        elif has_location:
            new_complaint.status = "Pending Details"
            db.commit()
            resp.message("We received your location. To complete the complaint, *please send a photo with a description*.")
        else:
            resp.message("We received your message, but we need more details. Please send a photo of the issue and your location.")

    return Response(content=str(resp), media_type="application/xml")

