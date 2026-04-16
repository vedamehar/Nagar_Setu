# 🚀 Quick Start Guide - Twilio Voice Complaint System

Get up and running in 5 minutes!

---

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Step 2: Setup Configuration

### Option A: Interactive Setup (Recommended)

```bash
python config.py --setup
```

This will ask for your credentials and create `.env` file automatically.

### Option B: Manual Setup

1. Copy the template:
```bash
cp .env.example .env
```

2. Edit `.env` and add:
```
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890
GEMINI_API_KEY=your_gemini_api_key
CALLBACK_URL=https://your-ngrok-url.ngrok.io
```

---

## Step 3: Validate Configuration

```bash
python config.py --validate
```

Expected output:
```
✅ Twilio Account SID
✅ Twilio Auth Token
✅ Twilio Phone Number: +1234567890
✅ Gemini API Key
✅ All required configurations are present
```

---

## Step 4: Start the Service

### Terminal 1: Start FastAPI Server

```bash
python call_complaint_service.py
```

Output:
```
✓ Database initialized
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

### Terminal 2: Create ngrok Tunnel (for testing)

```bash
ngrok http 8000
```

Output:
```
Forwarding   https://abc123-xx-xxx-xxx.ngrok.io -> http://localhost:8000
```

Copy the `https://...ngrok.io` URL

---

## Step 5: Configure Twilio Webhook

1. Go to [Twilio Console](https://www.twilio.com/console/phone-numbers/incoming)

2. Select your **Twilio Phone Number**

3. Under **Voice & Fax** → **A Call Comes In**:
   - Select: **Webhook**
   - URL: `https://your-ngrok-url.ngrok.io/voice`
   - Method: **POST**

4. Click **Save**

---

## Step 6: Test the System

### Make a Test Call

Call your Twilio phone number from any phone. You should hear:

1. "Welcome to complaint registration system"
2. It will ask you to describe your complaint
3. Record your message
4. It will ask for your location
5. Record your location
6. "Your complaint has been registered successfully"

### View Complaints

**Option A: Admin Dashboard (Interactive)**

```bash
python admin_dashboard.py
```

Choose: `1` to view all complaints

**Option B: Command Line**

```bash
python admin_dashboard.py all
python admin_dashboard.py pending
python admin_dashboard.py details <complaint_id>
```

**Option C: API Query**

```bash
curl http://localhost:8000/complaints
curl http://localhost:8000/complaints/pending
```

---

## Step 7: Export Data

### Export to JSON

```bash
python admin_dashboard.py export-json
```

Creates: `complaints.json`

### Export to CSV

```bash
python admin_dashboard.py export-csv
```

Creates: `complaints.csv`

---

## 📞 System Flow (What Happens During a Call)

```
📱 User calls +1234567890
    ↓
🔗 Twilio routes to /voice webhook
    ↓
🎤 System says: "Describe your complaint"
    ↓
⏹️ System records complaint (max 60 sec)
    ↓
🔗 Twilio calls /recording_complaint
    ↓
🎤 System says: "Where are you located?"
    ↓
⏹️ System records location (max 30 sec)
    ↓
🔗 Twilio calls /recording_location
    ↓
💾 Data saved to SQLite database
    ↓
📱 System says: "Complaint registered"
    ↓
☎️ Call ends
```

---

## 📊 Database

Your complaints are stored in: **`complaints.db`** (SQLite)

### Tables:

**1. complaints** - stores all complaint data
- Complaint audio URL
- Location audio URL
- Phone number
- Status (Pending/In Progress/Resolved)
- Timestamps

**2. call_sessions** - tracks call history
- Session ID
- Call start/end time
- Call duration

---

## 🔍 View Your Data

### Interactive Dashboard

```bash
python admin_dashboard.py
```

Menu options:
- View all complaints
- View pending complaints
- Search by phone number
- Update status
- View statistics
- Export to JSON/CSV

---

## 🧪 Troubleshooting

### Issue: "Connection refused"
- **Solution**: Make sure ngrok is running: `ngrok http 8000`

### Issue: No complaints appearing
- **Verify**: 
  1. Twilio webhook URL is set correctly
  2. Call was completed (didn't hang up early)
  3. Database file exists: `complaints.db`

### Issue: "Gemini API Error"
- **Solution**: Check GEMINI_API_KEY in `.env`

---

## 📦 Database File Locations

- **Complaints DB**: `./complaints.db`
- **Exported JSON**: `./complaints.json` (after export)
- **Exported CSV**: `./complaints.csv` (after export)

---

## 🔐 Security Checklist

- [ ] Store credentials in `.env` (never commit)
- [ ] Use HTTPS for webhook URL
- [ ] Keep `.env` out of version control
- [ ] Regular database backups
- [ ] Use strong Twilio Auth Token

---

## 📚 Next Steps

After basic setup:

1. **Speech-to-Text**: Add automatic transcription
2. **SMS Notification**: Send complaint ID via SMS
3. **Admin Dashboard**: Deploy web interface
4. **Complaint Routing**: Assign to departments
5. **Reporting**: Generate complaint statistics

---

## 🆘 Need Help?

- Check `SETUP_GUIDE.md` for detailed information
- Review logs in `call_service.log`
- Verify `.env` configuration: `python config.py --validate`

---

## 💡 Pro Tips

### Tip 1: Local Testing
Use ngrok to expose your local machine:
```bash
ngrok http 8000
```

### Tip 2: View Logs
```bash
tail -f call_service.log
```

### Tip 3: Reset Database
```bash
rm complaints.db
```
The system will recreate it on startup.

### Tip 4: Test Endpoint
```bash
curl http://localhost:8000/health
```

---

## 🎉 Congratulations!

Your complaint system is now running! 

- 📱 Users can call and file complaints
- 💾 Complaints stored in database
- 📊 Admin can view and manage complaints
- 📤 Export data anytime

**Now focus on:**
1. Multi-language transcription
2. Complaint assignment workflow
3. Officer dashboard for resolution
4. Statistics & reporting

Happy coding! 🚀
