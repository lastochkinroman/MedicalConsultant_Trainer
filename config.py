import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    GROQ_API_KEY = os.getenv('GROQ_API_KEY')

    GROQ_MODEL = "llama3-70b-8192"
    GROQ_TEMPERATURE = 0.7

    MAX_MESSAGES_PER_SESSION = 20
    MIN_MESSAGES_FOR_ANALYSIS = 3
