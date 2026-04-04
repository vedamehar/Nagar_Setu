import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.Certificate("civicsense-b653c-firebase-adminsdk-fbsvc-949e104fd5.json")
firebase_admin.initialize_app(cred, {
    "storageBucket": "civicsense-b653c.firebasestorage.app"
})
db = firestore.client()

docs = db.collection("TICKETS").order_by("createdAt", direction=firestore.Query.DESCENDING).limit(1).stream()
for doc in docs:
    data = doc.to_dict()
    print("Ticket:", data.get("ticketId"))
    print("ImageUrls:", data.get("imageUrls"))
