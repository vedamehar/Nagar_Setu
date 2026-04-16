"""
Configuration Management
- Load environment variables
- Validate configuration
- Setup logging
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# ============ ENVIRONMENT SETUP ============

def load_environment():
    """Load environment variables from .env file"""
    env_file = Path(__file__).parent / ".env"
    
    if env_file.exists():
        load_dotenv(env_file)
        print(f"✓ Environment variables loaded from: {env_file}")
    else:
        print(f"⚠️  .env file not found at: {env_file}")
        print("  Run: cp .env.example .env")

# ============ CONFIGURATION CLASS ============

class Config:
    """Configuration management"""
    
    # Twilio Settings
    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "")
    
    # Gemini API
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    
    # Server Settings
    SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
    SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))
    
    # Callback URL
    CALLBACK_URL = os.getenv("CALLBACK_URL", "http://localhost:8000")
    
    # Database
    DB_FILE = os.getenv("DB_FILE", "complaints.db")
    
    # Recording Settings
    COMPLAINT_MAX_LENGTH = int(os.getenv("COMPLAINT_MAX_LENGTH", "60"))
    LOCATION_MAX_LENGTH = int(os.getenv("LOCATION_MAX_LENGTH", "30"))
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "call_service.log")

# ============ CONFIGURATION VALIDATION ============

def validate_configuration():
    """Validate that all required configuration is present"""
    
    print("\n📋 CONFIGURATION VALIDATION\n")
    
    required_vars = {
        "TWILIO_ACCOUNT_SID": "Twilio Account SID",
        "TWILIO_AUTH_TOKEN": "Twilio Auth Token",
        "TWILIO_PHONE_NUMBER": "Twilio Phone Number",
        "GEMINI_API_KEY": "Gemini API Key",
    }
    
    missing = []
    for var, description in required_vars.items():
        value = getattr(Config, var, "")
        if not value:
            missing.append(f"  ❌ {description} ({var})")
            print(f"  ❌ {description} ({var})")
        else:
            # Hide sensitive values
            if var in ["TWILIO_AUTH_TOKEN", "GEMINI_API_KEY"]:
                print(f"  ✅ {description}")
            else:
                print(f"  ✅ {description}: {value}")
    
    if missing:
        print(f"\n❌ Missing {len(missing)} required configuration(s)")
        print("\nPlease update .env file with missing values")
        return False
    else:
        print("\n✅ All required configurations are present")
        return True

# ============ LOGGING SETUP ============

def setup_logging():
    """Setup logging configuration"""
    
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(log_format))
    
    # File handler
    try:
        file_handler = logging.FileHandler(Config.LOG_FILE)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(log_format))
    except Exception as e:
        print(f"Warning: Could not setup file logging: {e}")
        file_handler = None
    
    # Root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, Config.LOG_LEVEL, logging.INFO))
    logger.addHandler(console_handler)
    
    if file_handler:
        logger.addHandler(file_handler)
    
    return logger

# ============ SETUP WIZARD ============

def setup_wizard():
    """Interactive setup wizard for first-time configuration"""
    
    print("\n🚀 TWILIO VOICE COMPLAINT SYSTEM - SETUP WIZARD\n")
    print("=" * 60)
    
    env_file = Path(__file__).parent / ".env"
    
    # Check if .env exists
    if env_file.exists():
        print("✅ .env file already exists")
        return
    
    print("\n📝 Creating .env file...\n")
    
    # Get Twilio credentials
    print("🔐 TWILIO CONFIGURATION")
    account_sid = input("Enter your Twilio Account SID: ").strip()
    auth_token = input("Enter your Twilio Auth Token: ").strip()
    phone_number = input("Enter your Twilio Phone Number (e.g., +1234567890): ").strip()
    
    # Get Gemini API Key
    print("\n🔐 GEMINI API CONFIGURATION")
    gemini_key = input("Enter your Gemini API Key: ").strip()
    
    # Get server settings
    print("\n⚙️  SERVER CONFIGURATION")
    callback_url = input("Enter your callback URL (e.g., https://xxxx.ngrok.io): ").strip()
    
    # Create .env file
    env_content = f"""# Twilio Configuration
TWILIO_ACCOUNT_SID={account_sid}
TWILIO_AUTH_TOKEN={auth_token}
TWILIO_PHONE_NUMBER={phone_number}

# Gemini API Configuration
GEMINI_API_KEY={gemini_key}

# Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8000

# Callback URL (for Twilio webhooks)
CALLBACK_URL={callback_url}

# Database Configuration
DB_FILE=complaints.db

# Recording Settings
COMPLAINT_MAX_LENGTH=60
LOCATION_MAX_LENGTH=30

# Logging
LOG_LEVEL=INFO
LOG_FILE=call_service.log
"""
    
    try:
        with open(env_file, 'w') as f:
            f.write(env_content)
        print(f"\n✅ .env file created: {env_file}")
    except Exception as e:
        print(f"\n❌ Error creating .env file: {e}")
        return
    
    # Validate configuration
    load_environment()
    
    if validate_configuration():
        print("\n✅ Setup wizard completed successfully!")
        print("\nNext steps:")
        print("1. Run: python call_complaint_service.py")
        print("2. Configure Twilio webhook URL in console")
        print("3. Test by calling your Twilio number")
    else:
        print("\n❌ Setup wizard completed with errors")

# ============ MAIN ============

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Configuration Manager")
    parser.add_argument("--setup", action="store_true", help="Run setup wizard")
    parser.add_argument("--validate", action="store_true", help="Validate configuration")
    
    args = parser.parse_args()
    
    if args.setup:
        setup_wizard()
    elif args.validate:
        load_environment()
        validate_configuration()
    else:
        print("Usage:")
        print("  python config.py --setup     # Run setup wizard")
        print("  python config.py --validate  # Validate configuration")
