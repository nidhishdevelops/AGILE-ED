import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    LOG_LEVEL = "DEBUG"
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
    PINECONE_INDEX = "personalized-learning"
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
    SERPAPI_KEY = os.getenv("SERPAPI_KEY")
    YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
    DATA_DIR = "data"
    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 200
    EMAIL_SENDER = os.getenv("EMAIL_SENDER", "sonavalenidhish14@gmail.com")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
    EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER", "sonavalenidhish14@gmail.com")
    MIN_MODULE_CONFIDENCE = 0.5
    CONTENT_THRESHOLD = 0.4
    PERPLEXITY_MODEL = "sonar"
    GEMINI_MODEL = "gemini-1.5-flash"  # Faster and more reliable
    OPENAI_MODEL = "o3-mini"  # Consistent model name
    MAX_TOKENS = 8000
    MAX_LLM_RETRIES = 3
    LLM_TIMEOUT = 60