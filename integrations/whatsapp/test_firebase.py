import uuid
from main import push_to_firebase
from database import Complaint

mock_complaint = Complaint(
    complaint_id=f"CMP-{str(uuid.uuid4())[:8].upper()}",
    phone_number="+1234567890",
    description="This is a test issue with broken infrastructure",
    latitude="18.4901",
    longitude="73.8523",
    media_path=None,
    status="Completed"
)

print("Attempting to push mock complaint to Firebase...")
try:
    push_to_firebase(mock_complaint)
    print("Done!")
except Exception as e:
    print(f"Failed: {e}")
