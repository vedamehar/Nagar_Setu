# 📞 Twilio Voice Complaint System - Setup Guide

A FastAPI-based voice complaint management system that collects complaints via phone calls, records audio, and stores data in SQLite.

---

## 📋 Features

✅ **Interactive Voice Response (IVR)**
- Answers incoming calls automatically
- Asks for complaint description
- Records user's voice

✅ **Multi-Language Support**
- English (en)
- Hindi (hi)
- Spanish (es)
- French (fr)
- Powered by Gemini API

✅ **SQLite Database**
- Stores complaint records
- Tracks call sessions
- Records audio URLs

✅ **RESTful API**
- Query complaints
- Update status
- View call history

✅ **Integration Ready**
- Works with Twilio Voice
- Gemini API for processing
- ngrok for local testing

---

## 🔧 Prerequisites

- Python 3.8+
- Twilio Account
- Google Gemini API Key
- ngrok (for local testing)

---

## 📦 Installation

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 2: Set Up Environment Variables

1. Copy `.env.example` to `.env`

```bash
cp .env.example .env
```

2. Fill in your credentials:

```
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890
GEMINI_API_KEY=your_gemini_api_key
```

### Step 3: Obtain Twilio Credentials

1. Go to [Twilio Console](https://www.twilio.com/console)
2. Note your **Account SID** and **Auth Token**
3. Buy a phone number that supports **Voice**

### Step 4: Obtain Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikeys)
2. Create a new API key
3. Copy it to `.env` file

---

## 🚀 Running the Service

### Option 1: Local Development with ngrok

```bash
# Terminal 1: Start the FastAPI server
python call_complaint_service.py
```

```bash
# Terminal 2: Start ngrok tunnel
ngrok http 8000
```

Output:
```
Forwarding   https://xxxx-xx-xxx-xxx.ngrok.io -> http://localhost:8000
```

### Option 2: Production Deployment

```bash
python call_complaint_service.py
```

---

## 🔗 Configure Twilio Webhook

1. Go to [Twilio Console](https://www.twilio.com/console/phone-numbers/incoming)
2. Select your **Twilio Phone Number**
3. Under **Voice & Fax** → **A Call Comes In**:
   - Select **Webhook**
   - URL: `https://your-domain.com/voice` (use ngrok URL for testing)
   - Method: **POST**

---

## 📞 Call Flow

```
User calls your Twilio number
        ↓
/voice webhook triggered
        ↓
System says: "Welcome to complaint registration system"
        ↓
System says: "Please describe your complaint after the beep"
        ↓
User records complaint (max 60 seconds)
        ↓
/recording_complaint webhook processes audio
        ↓
System says: "Please tell us your location after the beep"
        ↓
User records location (max 30 seconds)
        ↓
/recording_location webhook processes audio
        ↓
System saves to SQLite database
        ↓
System says: "Complaint registered successfully"
        ↓
Call ends
```

---

## 📊 Database Schema

### `complaints` Table

```sql
id              - Unique complaint ID (UUID)
phone_number    - Caller's phone number
complaint_audio_url - URL to complaint recording
complaint_text  - Transcribed complaint text
complaint_language - Detected language
location_audio_url - URL to location recording
location_text   - Transcribed location text
location_language - Detected language
status          - Complaint status (Pending, In Progress, Resolved)
created_at      - Timestamp when complaint was registered
updated_at      - Last updated timestamp
```

### `call_sessions` Table

```sql
session_id      - Unique session ID (UUID)
phone_number    - Caller's phone number
complaint_id    - Link to complaint
call_duration   - Call duration in seconds
started_at      - Call start time
ended_at        - Call end time
```

---

## 🔌 API Endpoints

### Get All Complaints
```bash
GET /complaints
```

Response:
```json
{
  "status": "success",
  "count": 5,
  "complaints": [
    {
      "id": "abc123",
      "phone_number": "+1234567890",
      "complaint_audio_url": "https://...",
      "status": "Pending",
      "created_at": "2024-01-15 10:30:00"
    }
  ]
}
```

### Get Pending Complaints
```bash
GET /complaints/pending
```

### Get Specific Complaint
```bash
GET /complaints/{complaint_id}
```

### Update Complaint Status
```bash
PUT /complaints/{complaint_id}/status?status=In%20Progress
```

---

## 🧪 Testing

### Test Endpoint
```bash
curl http://localhost:8000/health
```

Response:
```json
{"status": "ok", "service": "Call Complaint System"}
```

### Make a Test Call (requires Twilio credentials)
```bash
curl -X POST "http://localhost:8000/test-call?phone_number=%2B917834902399"
```

---

## 🌐 Multi-Language Support

The system automatically detects the language of complaint and location using Gemini API.

**Supported Languages:**
- English (en)
- Hindi (हिंदी)
- Spanish (Español)
- French (Français)

---

## 🔒 Security Considerations

- [ ] Use environment variables for all secrets
- [ ] Enable HTTPS for all webhooks
- [ ] Validate Twilio requests using signature verification
- [ ] Implement rate limiting
- [ ] Add authentication to API endpoints
- [ ] Encrypt sensitive data in database
- [ ] Use database backups

---

## 📈 Roadmap

### Phase 1: Current ✅
- Voice complaint recording
- Location recording
- SQLite storage

### Phase 2: Soon
- [ ] Speech-to-text transcription
- [ ] Automatic location parsing
- [ ] SMS notifications with complaint ID
- [ ] Admin dashboard

### Phase 3: Future
- [ ] Complaint assignment to departments
- [ ] Officer resolution uploads
- [ ] WhatsApp integration
- [ ] Multi-channel complaint platform

---

## 🐛 Troubleshooting

### Issue: Twilio webhook not being called

**Solution:**
1. Check ngrok is running: `ngrok http 8000`
2. Update Twilio webhook URL
3. Verify allowed traffic on firewall

### Issue: Recording not captured

**Solution:**
1. Check audio permissions
2. Verify `RecordingUrl` is accessible
3. Check Twilio account has recording enabled

### Issue: Database errors

**Solution:**
1. Check `complaints.db` file permissions
2. Verify storage space available
3. Check SQLite version compatibility

---

## 📚 Resources

- [Twilio Voice Documentation](https://www.twilio.com/docs/voice)
- [Twilio TwiML Reference](https://www.twilio.com/docs/voice/twiml)
- [Google Gemini API](https://ai.google.dev/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLite Documentation](https://www.sqlite.org/docs.html)

---

## 📝 License

This project is open source and available under the MIT License.

---

## 🤝 Support

For issues or questions, please create an issue or contact the development team.
