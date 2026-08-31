import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("MISTRAL_API_KEY")

if api_key:
    print("✅ MISTRAL_API_KEY loaded successfully")
    print("Key length:", len(api_key))
else:
    print("❌ MISTRAL_API_KEY was NOT loaded")