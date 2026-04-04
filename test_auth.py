import os
import requests
import sys
from dotenv import load_dotenv

load_dotenv()

sid = os.getenv("TWILIO_ACCOUNT_SID")
token = os.getenv("TWILIO_AUTH_TOKEN")
message_sid = os.getenv("TWILIO_MESSAGE_SID")
media_sid = os.getenv("TWILIO_MEDIA_SID")

if not all([sid, token, message_sid, media_sid]):
    print("Missing Twilio env vars. Required: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_MESSAGE_SID, TWILIO_MEDIA_SID")
    sys.exit(1)

url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages/{message_sid}/Media/{media_sid}"

print("Trying with standard auth and redirects...")
res1 = requests.get(url, auth=(sid, token))
print(f"Status: {res1.status_code}")
if res1.status_code != 200:
    print(res1.text[:200])

print("\nTrying with disabled redirects...")
res2 = requests.get(url, auth=(sid, token), allow_redirects=False)
print(f"Status: {res2.status_code}")
if res2.status_code in [301, 302, 307]:
    redirect_url = res2.headers.get("Location")
    print("Redirected to:", redirect_url[:50] + "...")
    res3 = requests.get(redirect_url) # No auth
    print(f"Final status: {res3.status_code}")
