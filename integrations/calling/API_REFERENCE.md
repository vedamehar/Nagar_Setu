# 📚 API Reference - Twilio Voice Complaint System

Complete API documentation for the Call Complaint Service.

---

## 📋 API Overview

Base URL: `http://localhost:8000` (or your deployed domain)

All endpoints default to JSON responses except Twilio webhooks return TwiML XML.

---

## 🔌 Webhook Endpoints (Twilio Callbacks)

These are called automatically by Twilio during calls.

### POST /voice

Webhook triggered when someone calls your Twilio number.

**Called by:** Twilio (automatically)

**Returns:** TwiML XML for voice response

**Flow:**
1. System says welcome message
2. Records complaint (max 60 seconds)
3. Calls `/recording_complaint`

**Example Response:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Welcome to complaint registration system.</Say>
    <Say>Please describe your complaint after the beep.</Say>
    <Record 
        maxLength="60" 
        action="/recording_complaint?session_id=abc123" 
        method="POST" 
    />
</Response>
```

---

### POST /recording_complaint

Webhook called after complaint is recorded.

**Query Parameters:**
- `session_id` - Current call session ID

**Form Data:**
- `RecordingUrl` - URL to complaint audio file
- `From` - Caller's phone number
- `CallSid` - Twilio call ID

**Returns:** TwiML XML asking for location

**Example Request:**
```
POST /recording_complaint?session_id=abc123
From: +1234567890
RecordingUrl: https://api.twilio.com/2010-04-01/.../Recordings/abc
```

**Example Response:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Thank you. Please tell us your location after the beep.</Say>
    <Record 
        maxLength="30" 
        action="/recording_location?session_id=abc123&complaint_audio=https://..." 
        method="POST" 
    />
</Response>
```

---

### POST /recording_location

Webhook called after location is recorded.

**Query Parameters:**
- `session_id` - Current call session ID
- `complaint_audio` - URL to complaint recording

**Form Data:**
- `RecordingUrl` - URL to location audio file
- `From` - Caller's phone number
- `CallSid` - Twilio call ID

**Returns:** TwiML XML and saves to database

**Database Action:** 
- Creates complaint record
- Stores complaint audio URL
- Stores location audio URL
- Records phone number
- Sets status to "Pending"

**Example Response:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Your complaint has been registered successfully. Thank you for using our service.</Say>
    <Hangup />
</Response>
```

---

### POST /recording_status

Status callback for recording events.

**Query Parameters:**
- `session_id` - Current call session ID

**Form Data:**
- `RecordingStatus` - Status (completed, failed, etc)
- `RecordingUrl` - URL to recording
- `RecordingDuration` - Duration in seconds

**Returns:** HTTP 200

---

## 📊 Query Endpoints

### GET /complaints

Get all complaints with pagination.

**Response:**
```json
{
  "status": "success",
  "count": 5,
  "complaints": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "phone_number": "+1234567890",
      "complaint_audio_url": "https://api.twilio.com/.../Recordings/abc",
      "complaint_text": "",
      "complaint_language": "en",
      "location_audio_url": "https://api.twilio.com/.../Recordings/def",
      "location_text": "Near Market Street",
      "location_language": "en",
      "status": "Pending",
      "created_at": "2024-01-15 10:30:45",
      "updated_at": "2024-01-15 10:35:20"
    }
  ]
}
```

**Status Codes:**
- `200 OK` - Success
- `500` - Database error

---

### GET /complaints/pending

Get all pending complaints.

**Response:**
```json
{
  "status": "success",
  "count": 3,
  "complaints": [ ... ]
}
```

**Filter:** Only returns complaints with `status = "Pending"`

---

### GET /complaints/{complaint_id}

Get details of a specific complaint.

**Parameters:**
- `complaint_id` - UUID of the complaint

**Response:**
```json
{
  "status": "success",
  "complaint": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "phone_number": "+91234567890",
    "complaint_audio_url": "https://api.twilio.com/.../Recordings/abc",
    "complaint_text": "",
    "complaint_language": "en",
    "location_audio_url": "https://api.twilio.com/.../Recordings/def",
    "location_text": "Sector 5, Near Park",
    "location_language": "hi",
    "status": "Pending",
    "created_at": "2024-01-15 10:30:45",
    "updated_at": "2024-01-15 10:35:20"
  }
}
```

---

### PUT /complaints/{complaint_id}/status

Update complaint status.

**Parameters:**
- `complaint_id` - UUID of complaint
- `status` - New status (query param)

**Valid Statuses:**
- `Pending` - Initial status
- `In Progress` - Being handled
- `Resolved` - Issue fixed
- `Closed` - Case closed
- `Rejected` - Invalid complaint

**Request:**
```bash
PUT /complaints/550e8400-e29b-41d4-a716-446655440000/status?status=In%20Progress
```

**Response:**
```json
{
  "status": "success",
  "message": "Status updated"
}
```

**Side Effects:**
- `updated_at` timestamp updated to current time
- Status changed in database

---

## 🏥 Health & Testing Endpoints

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "service": "Call Complaint System"
}
```

**Use For:** Monitoring, uptime checks

---

### POST /test-call

Make a test call (sends call to phone number).

**Parameters:**
- `phone_number` - Phone number to call (query param, URL encoded)

**Request:**
```bash
POST /test-call?phone_number=%2B917834902399
```

**Response:**
```json
{
  "status": "success",
  "call_sid": "CA1234567890abcdef1234567890abcdef"
}
```

**Requirements:**
- Valid Twilio account credentials
- Phone number must support receiving calls
- Number must be verified in Twilio account

**Note:** Only works if Twilio credentials are configured

---

## 📝 Data Models

### Complaint Object

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "phone_number": "+1234567890",
  "complaint_audio_url": "https://api.twilio.com/.../Recordings/abc",
  "complaint_text": "Road is damaged",
  "complaint_language": "en",
  "location_audio_url": "https://api.twilio.com/.../Recordings/def",
  "location_text": "Main Street near Market",
  "location_language": "en",
  "status": "Pending",
  "created_at": "2024-01-15T10:30:45",
  "updated_at": "2024-01-15T10:35:20"
}
```

### Call Session Object

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440001",
  "phone_number": "+1234567890",
  "complaint_id": "550e8400-e29b-41d4-a716-446655440000",
  "call_duration": 125,
  "started_at": "2024-01-15T10:30:45",
  "ended_at": "2024-01-15T10:32:50"
}
```

---

## 🚀 Usage Examples

### Check System Health

```bash
curl http://localhost:8000/health
```

### Get All Complaints

```bash
curl http://localhost:8000/complaints
```

### Get Pending Complaints

```bash
curl http://localhost:8000/complaints/pending
```

### Get Specific Complaint

```bash
curl http://localhost:8000/complaints/550e8400-e29b-41d4-a716-446655440000
```

### Update Complaint Status

```bash
curl -X PUT "http://localhost:8000/complaints/550e8400-e29b-41d4-a716-446655440000/status?status=In%20Progress"
```

### Make Test Call

```bash
curl -X POST "http://localhost:8000/test-call?phone_number=%2B917834902399"
```

---

## 🔐 Error Handling

### Error Response Format

```json
{
  "status": "error",
  "message": "Complaint not found"
}
```

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| Complaint not found | Invalid complaint_id | Verify complaint ID |
| Invalid status | Status not in valid list | Use: Pending/In Progress/Resolved/Closed/Rejected |
| Database error | SQLite connection issue | Check database file permissions |
| Twilio error | Invalid credentials | Verify .env configuration |

---

## 🔄 Workflow Example

### Complete Call Flow

1. **User calls +1234567890**
   
2. **Twilio calls POST /voice**
   - System answers call
   - Play greeting
   - Start recording complaint

3. **Complaint recorded by Twilio**
   
4. **Twilio calls POST /recording_complaint**
   - Send complaint audio URL
   - System asks for location
   - Start recording location

5. **Location recorded by Twilio**

6. **Twilio calls POST /recording_location**
   - Send location audio URL
   - **API: Save to database**
   - Play confirmation
   - Hang up

7. **Admin queries the complaint**
   ```bash
   GET /complaints/{complaint_id}
   ```

8. **Admin updates status**
   ```bash
   PUT /complaints/{complaint_id}/status?status=In%20Progress
   ```

---

## 🧪 cURL Test Scripts

### Script 1: Get All Complaints

```bash
#!/bin/bash
curl -s http://localhost:8000/complaints | json_pp
```

### Script 2: Get Specific Complaint (using jq)

```bash
#!/bin/bash
COMPLAINT_ID="550e8400-e29b-41d4-a716-446655440000"
curl -s http://localhost:8000/complaints/$COMPLAINT_ID | jq '.'
```

### Script 3: Update Status

```bash
#!/bin/bash
COMPLAINT_ID="550e8400-e29b-41d4-a716-446655440000"
NEW_STATUS="In Progress"

curl -X PUT \
  "http://localhost:8000/complaints/$COMPLAINT_ID/status?status=$(echo -n '$NEW_STATUS' | jq -sRr @uri)"
```

---

## 📊 Rate Limiting

Currently no rate limiting implemented. Recommendations:

- Implement for production
- Limit complaints per phone number
- Prevent DoS attacks
- Track API usage

---

## 🔮 Planned Enhancements

- [ ] Authentication/Authorization
- [ ] Rate limiting
- [ ] API versioning
- [ ] Batch export
- [ ] Advanced filtering
- [ ] Complaint assignment
- [ ] Webhook for external systems

---

## 📞 Support

For API issues:
1. Check `.env` configuration
2. Verify Twilio webhook URL
3. Review logs: `tail -f call_service.log`
4. Test health endpoint: `GET /health`

