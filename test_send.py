import os
from dotenv import load_dotenv
load_dotenv(override=True)

from twilio.rest import Client
sid = os.getenv("TWILIO_ACCOUNT_SID")
token = os.getenv("TWILIO_AUTH_TOKEN")
client = Client(sid, token)

print("=== Sandbox Participants (numbers that joined your sandbox) ===")
try:
    participants = client.messaging.v1.services.list(limit=20)
    if not participants:
        print("No messaging services found")
    for p in participants:
        print(f"  Service: {p.friendly_name} SID={p.sid}")
except Exception as e:
    print(f"Messaging services error: {e}")

print("\n=== Checking WhatsApp sandbox sender number ===")
try:
    sandboxes = client.messaging.v1.services.list()
    print(f"Found {len(sandboxes)} messaging service(s)")
except Exception as e:
    print(f"Error: {e}")

print("\n=== Outgoing caller IDs (phone numbers on this account) ===")
try:
    numbers = client.incoming_phone_numbers.list(limit=10)
    for n in numbers:
        print(f"  {n.phone_number} — {n.friendly_name}")
    if not numbers:
        print("  (no numbers purchased on this account — using Sandbox)")
except Exception as e:
    print(f"Error: {e}")

print("\n=== Trying to send a test WhatsApp message ===")
test_to = input("Enter your WhatsApp number to test (e.g. +919876543210): ").strip()
if test_to:
    if not test_to.startswith("+"):
        test_to = "+" + test_to
    try:
        msg = client.messages.create(
            from_="whatsapp:+14155238886",
            to=f"whatsapp:{test_to}",
            body="CivicSense test message - new credentials working!"
        )
        print(f"SUCCESS! Message SID: {msg.sid}, Status: {msg.status}")
    except Exception as e:
        print(f"FAILED: {e}")
