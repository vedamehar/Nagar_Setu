# 📞 Twilio Voice Complaint System - Project Overview

Complete voice-based complaint management system using Twilio and SQLite.

---

## 📁 Project Structure

```
📦 Calling/
├── call_complaint_service.py     # Main FastAPI application
├── admin_dashboard.py            # Admin management tool
├── config.py                     # Configuration management
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment template
├── .env                          # Environment variables (your credentials)
├── complaints.db                 # SQLite database (auto-created)
├── call_service.log              # Application logs
├── QUICKSTART.md                 # Quick start guide ⭐ START HERE
├── SETUP_GUIDE.md                # Detailed setup instructions
└── API_REFERENCE.md              # Complete API documentation
```

---

## 📄 File Descriptions

### 1. **call_complaint_service.py** (Main Application)

The core FastAPI application that handles voice calls.

**Key Features:**
- ✅ Twilio webhook integration
- ✅ Voice recording handling
- ✅ SQLite database operations
- ✅ Multi-language support (Gemini AI)
- ✅ RESTful API endpoints

**Main Classes/Functions:**
- `VoiceResponse` - TwiML response builder
- `init_database()` - Create database tables
- `/voice` - Handle incoming calls
- `/recording_complaint` - Process complaint audio
- `/recording_location` - Process location audio
- `/complaints` - Query complaints API

**Database Tables Created:**
- `complaints` - Stores all complaint records
- `call_sessions` - Tracks call sessions

---

### 2. **admin_dashboard.py** (Management Tool)

Interactive terminal interface for managing complaints.

**Features:**
- 📋 View all complaints
- ⏳ List pending complaints
- 🔍 Search by phone/status
- ✏️ Update complaint status
- 📊 View statistics
- 📤 Export to JSON/CSV

**Usage:**
```bash
python admin_dashboard.py              # Interactive mode
python admin_dashboard.py all          # Show all
python admin_dashboard.py pending      # Show pending
python admin_dashboard.py details <id> # Show details
python admin_dashboard.py stats        # Show stats
```

---

### 3. **config.py** (Configuration Manager)

Handles environment setup and validation.

**Features:**
- 🔐 Load environment variables
- ✅ Validate configuration
- 🪵 Setup logging
- 🧙 Interactive setup wizard

**Usage:**
```bash
python config.py --setup     # Interactive setup
python config.py --validate  # Validate config
```

**Configuration Class:**
- `Config.TWILIO_ACCOUNT_SID`
- `Config.GEMINI_API_KEY`
- `Config.CALLBACK_URL`
- etc.

---

### 4. **requirements.txt**

Python package dependencies.

**Packages:**
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `twilio` - Twilio SDK
- `google-generativeai` - Gemini API
- `python-dotenv` - Environment variables
- `requests` - HTTP client
- `tabulate` - Table formatting

**Install:**
```bash
pip install -r requirements.txt
```

---

### 5. **.env.example**

Template for environment variables.

**Variables to Configure:**
```
TWILIO_ACCOUNT_SID
TWILIO_AUTH_TOKEN
TWILIO_PHONE_NUMBER
GEMINI_API_KEY
CALLBACK_URL
```

**Create .env from template:**
```bash
cp .env.example .env
```

---

### 6. **.env** (Your Credentials)

Your actual environment variables. **KEEP PRIVATE!**

**Don't commit to git** - Add to `.gitignore`

```
TWILIO_ACCOUNT_SID=your_value
TWILIO_AUTH_TOKEN=your_value
...
```

---

### 7. **complaints.db**

SQLite database file (auto-created).

**Tables:**
1. `complaints` - Complaint records
2. `call_sessions` - Call history

**Auto-created by:** `call_complaint_service.py` on startup

---

### 8. **call_service.log**

Application logs (auto-created).

**Contents:**
- Startup messages
- API call logs
- Database operations
- Error messages

**View with:**
```bash
tail -f call_service.log
```

---

### 9. **QUICKSTART.md** ⭐ START HERE

Quick 5-minute setup guide.

**Contents:**
- Installation steps
- Configuration setup
- Starting the service
- Twilio webhook configuration
- Testing the system
- Troubleshooting tips

**Read this first!**

---

### 10. **SETUP_GUIDE.md**

Detailed comprehensive setup guide.

**Contains:**
- Feature overview
- Prerequisites
- Installation instructions
- Database schema
- API endpoints overview
- Multi-language support details
- Troubleshooting guide
- Roadmap

**Read for complete details**

---

### 11. **API_REFERENCE.md**

Complete API documentation.

**Includes:**
- All webhook endpoints
- Query endpoints
- Response formats
- Error handling
- cURL examples
- Complete workflows

**Reference while developing**

---

## 🚀 Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Setup configuration:**
   ```bash
   python config.py --setup
   ```

3. **Start service (Terminal 1):**
   ```bash
   python call_complaint_service.py
   ```

4. **Create tunnel (Terminal 2):**
   ```bash
   ngrok http 8000
   ```

5. **Update Twilio webhook URL** with ngrok URL

6. **Make a test call** to your Twilio number

7. **View complaints:**
   ```bash
   python admin_dashboard.py
   ```

---

## 📊 System Architecture

```
┌─────────────────┐
│  User Calls     │
│  Twilio Number  │
└────────┬────────┘
         │
         ↓
┌─────────────────────────────┐
│  Twilio Cloud               │
│  Receives voice call        │
│  Records audio              │
└────────┬────────────────────┘
         │
         ├─→ POST /voice
         │
         ├─→ POST /recording_complaint
         │
         └─→ POST /recording_location
              │
              ↓
    ┌─────────────────────┐
    │  FastAPI Server     │
    │  Processes webhooks │
    │  Saves to database  │
    └────────┬────────────┘
             │
             ↓
    ┌──────────────────┐
    │  SQLite Database │
    │  complaints.db   │
    └──────────────────┘
```

---

## 🔄 Data Flow

```
INCOMING CALL
    ↓
System asks for complaint
    ↓
User speaks complaint
    ↓
Audio saved temporarily in Twilio
    ↓
Callback to /recording_complaint
    ↓
System asks for location
    ↓
User speaks location
    ↓
Audio saved temporarily in Twilio
    ↓
Callback to /recording_location
    ↓
Both audio URLs + phone number saved to SQLite
    ↓
System says "Thank you"
    ↓
Call ends
    ↓
Admin can query database via:
  - API endpoints
  - Admin dashboard
  - SQL queries directly
```

---

## 🎯 Main Features

✅ **Voice Complaint Recording**
- Record complaint via phone call
- Record location via phone call
- Audio stored at Twilio URL

✅ **Multi-Language Support**
- English
- Hindi
- Spanish
- French

✅ **Database Management**
- SQLite for local storage
- Complaint records
- Call session tracking

✅ **Admin Tools**
- Interactive dashboard
- Export to JSON/CSV
- Search complaints
- Update status

✅ **RESTful API**
- Query complaints
- Update status
- Health checks

---

## 🔒 Security Features

🔐 **Environment Variables**
- Credentials stored in .env
- Not committed to git

🔐 **Error Handling**
- Graceful error responses
- Detailed logging

🔐 **Database**
- SQLite local storage
- Indexed queries

🔐 **Validation**
- Input validation
- Configuration validation

---

## 📈 Performance

- ⚡ FastAPI high performance
- 🗄️ SQLite for small-to-medium scale
- 🎙️ Async webhook processing
- 📊 Efficient database queries

---

## 🔮 Next Steps

### Short Term
1. Add speech-to-text for transcription
2. Add SMS notification with complaint ID
3. Deploy web dashboard

### Medium Term
1. Complaint assignment to departments
2. Officer workflow
3. Multi-channel integration (WhatsApp)

### Long Term
1. AI analytics on complaints
2. Predictive routing
3. Integration with government systems

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| QUICKSTART.md | Get running in 5 minutes |
| SETUP_GUIDE.md | Detailed setup instructions |
| API_REFERENCE.md | API endpoint documentation |
| requirements.txt | Python dependencies |
| .env.example | Configuration template |

---

## 🆘 Troubleshooting

**Issue:** Complaints not saving
**Solution:** Check Twilio webhook URL in console

**Issue:** API not responding
**Solution:** Ensure FastAPI server is running

**Issue:** Database locked
**Solution:** Close all connections and delete .db file to reset

**Issue:** Gemini API errors
**Solution:** Verify GEMINI_API_KEY in .env

---

## 📞 Support Resources

- [Twilio Documentation](https://www.twilio.com/docs)
- [FastAPI Guide](https://fastapi.tiangolo.com/)
- [SQLite Reference](https://www.sqlite.org/)
- [Google Gemini API](https://ai.google.dev/)

---

## ✅ Verified Working

- ✅ Python 3.8+
- ✅ Windows/Mac/Linux
- ✅ Twilio SDK latest
- ✅ FastAPI 0.104+
- ✅ SQLite 3.x

---

## 📝 License

Open source - MIT License

---

## 🎉 You're All Set!

Your complaint system is ready to use. Start with:

```bash
python config.py --setup
python call_complaint_service.py
```

Then read **QUICKSTART.md** for next steps!

Happy building! 🚀
