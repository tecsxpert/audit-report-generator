import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    MODEL = 'gpt-3.5-turbo'
    MAX_TOKENS = 1500
    TEMPERATURE = 0.7