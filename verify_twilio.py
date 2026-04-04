import os
from dotenv import load_dotenv
load_dotenv(override=True)

sid = os.getenv("TWILIO_ACCOUNT_SID")
token = os.getenv("TWILIO_AUTH_TOKEN")

print(f"SID loaded:   {sid}")
print(f"Token loaded: {token[:6]}...{token[-4:]}")

from twilio.rest import Client
client = Client(sid, token)

# Verify the account is reachable
try:
    account = client.api.accounts(sid).fetch()
    print(f"\nAccount status: {account.status}")
    print(f"Account name:   {account.friendly_name}")
    print("\nCredentials are VALID!")
except Exception as e:
    print(f"\nCredential check FAILED: {e}")
