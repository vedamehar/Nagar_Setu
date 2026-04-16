Harshal Marathe
Mayur Chikhale
Vedant Mehar
Aum Mishra

# CivicSense

CivicSense is a role-based complaint management platform built with Flutter and Firebase for citizen services and officer operations.

The app supports:
- Citizen complaint registration and tracking
- Officer workflow management across hierarchy levels
- Admin monitoring and operations
- Real-time notifications and escalation-ready flows
- Officer-side chatbot integration through an ngrok-hosted API

## Project Highlights

- Flutter frontend with Provider state management
- Firebase Authentication, Firestore, Storage, Messaging, and Functions
- Multi-role architecture: Citizen, Officer, Admin
- Role dashboards for officer hierarchy
- Complaint data seeding through CSV and scripts
- Chat assistant integrated in officer side panels

## Contributors

- Harshal Marathe
- Mayur Chikhale
- Vedant Mehar
- Aum Mishra

## Tech Stack

- Flutter (Dart)
- Firebase Auth
- Cloud Firestore
- Firebase Storage
- Firebase Cloud Messaging
- Cloud Functions (Node.js)
- Provider
- flutter_map and geolocator
- fl_chart

## Repository Structure

- lib: Main Flutter app source
- lib/screens: Screens by module and role
- lib/widgets: Shared and role-based widgets
- lib/services: Firebase and app services
- lib/chatbot: Chatbot integration layer
- functions: Cloud Functions source
- assets: Images and app assets
- scripts and tool: Utility scripts and setup helpers

## Officer Chatbot Integration

The officer chatbot is accessible from officer side panel as Chat Assistant.

### Current Chatbot Connection

- Base URL: https://comparably-pyroligneous-del.ngrok-free.dev
- Endpoint: /api/chat
- Header: Authorization: Bearer dev-chat-token-123

### Chatbot Files

- lib/chatbot/config/chatbot_config.dart
- lib/chatbot/models/chatbot_models.dart
- lib/chatbot/services/chatbot_api_service.dart
- lib/chatbot/controllers/chat_controller.dart
- lib/chatbot/ui/chatbot_screen.dart
- lib/chatbot/ui/chatbot_launcher.dart

### Runtime Override (Recommended)

Use runtime defines to switch ngrok URL or token without editing code:

flutter run --dart-define=CHATBOT_BASE_URL=https://comparably-pyroligneous-del.ngrok-free.dev --dart-define=CHATBOT_BEARER_TOKEN=dev-chat-token-123

## Setup Instructions

1. Install Flutter SDK and required platform toolchains.
2. Run dependency install:
   flutter pub get
3. Configure Firebase project files:
   - Android: android/app/google-services.json
   - iOS/macOS: GoogleService-Info.plist as needed
4. Verify Firebase options in:
   - lib/firebase_options.dart
5. Start the app:
   flutter run

## Firebase Configuration

Required Firebase services:
- Authentication
- Firestore
- Storage
- Cloud Messaging
- Functions

Rules and indexes used in project:
- firestore.rules
- storage.rules
- firestore.indexes.json

Deploy rules and indexes when needed:
- firebase deploy --only firestore:rules
- firebase deploy --only firestore:indexes
- firebase deploy --only storage

## Data and Seeding

Important seed and support files:
- officers_data.csv
- civic_complaints.csv
- unique_complaint.csv
- scripts/check_users.dart

Use these to seed, validate, or inspect data during development.

## Build and Quality Checks

Recommended commands:
- flutter analyze
- flutter test
- flutter run

Targeted chatbot validation example:
- flutter analyze lib/chatbot/services/chatbot_api_service.dart lib/chatbot/controllers/chat_controller.dart lib/chatbot/ui/chatbot_screen.dart

## Chatbot Troubleshooting

### Symptom
Chatbot endpoint is offline. Start chatbot API and ngrok on host laptop, then retry.

### Cause
The ngrok host machine is not running the chatbot API and tunnel, or URL has changed.

### Fix
1. Start chatbot API on host laptop.
2. Start ngrok tunnel on host laptop.
3. Confirm health endpoint is reachable.
4. Update CHATBOT_BASE_URL through dart-define if URL changed.

### Safe Failure Behavior
If endpoint returns non-JSON offline page, app now shows friendly error instead of crashing.

## Security Notes

- Avoid hardcoding production secrets in source code.
- Prefer runtime configuration for chatbot URL and bearer token.
- Rotate bearer tokens for production deployments.

## Platforms

Configured project targets:
- Android
- iOS
- Web
- Windows
- macOS
- Linux

## Current Status

- Officer chatbot integrated in side panel navigation
- Offline ngrok/non-JSON response handling implemented safely
- Existing dashboard and role logic preserved

## License

Internal academic or team project usage unless stated otherwise by repository owner.
