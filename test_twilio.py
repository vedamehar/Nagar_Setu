import requests, os
from dotenv import load_dotenv
load_dotenv()
sid = os.getenv("TWILIO_ACCOUNT_SID")
token = os.getenv("TWILIO_AUTH_TOKEN")
message_sid = os.getenv("TWILIO_MESSAGE_SID")
media_sid = os.getenv("TWILIO_MEDIA_SID")
print(f"SID: {sid[:10]}...")

if not all([sid, token, message_sid, media_sid]):
    raise ValueError("Missing required env vars: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_MESSAGE_SID, TWILIO_MEDIA_SID")

url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages/{message_sid}/Media/{media_sid}"
res = requests.get(url, auth=(sid, token), allow_redirects=True, timeout=30)
ct = res.headers.get("Content-Type", "unknown")
print(f"Status: {res.status_code}")
print(f"Content-Type: {ct}")
print(f"Content-Length: {len(res.content)} bytes")
if "image" in ct:
    print("SUCCESS - can download real image from Twilio!")
    with open("test_twilio_image.jpg", "wb") as f:
        f.write(res.content)
    print("Saved to test_twilio_image.jpg")
else:
    print("FAIL - response is not an image:")
    print(res.text[:300])
