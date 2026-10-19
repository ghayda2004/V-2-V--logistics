import os
from dotenv import load_dotenv

# Load variables from the .env file
load_dotenv()

class Settings:
    # OpenRouteService key for real-world distances
    ORS_API_KEY: str = os.getenv("ORS_API_KEY", "eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6IjM3NGM3MWFiODAyOTQ2ODFiNzRhMTZiOGU2YzY1NGI4IiwiaCI6Im11cm11cjY0In0=")
    
    # Telegram Bot Token for sending messages to drivers
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    
    # Traccar URL for fetching live tracking data
    TRACCAR_URL: str = os.getenv("TRACCAR_URL", "http://demo.traccar.org/api")

    # PostgreSQL Database URL
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:2026@localhost:5432/postgres?client_encoding=utf8")

settings = Settings()

