import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    LOG_LEVEL = "INFO"
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
    PINECONE_INDEX = "personalizeddb"
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
    EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER", "sonavalenidhish14@example.com")
    MIN_MODULE_CONFIDENCE = 0.40
    CONTENT_THRESHOLD = 0.30
    
    # FIXED: use a valid model name
    OPENAI_MODEL = "gpt-4-turbo"   # or "gpt-4-turbo" if you have access
    GEMINI_MODEL = "gemini-2.5-flash-lite"
    PERPLEXITY_MODEL = "sonar-pro"
    OLLAMA_MODEL = "llama3.2" 

    EMBEDDING_MODEL = "text-embedding-3-large"
    PINECONE_DIMENSION = 3072
    
    MAX_TOKENS = 8000
    MAX_LLM_RETRIES = 2
    LLM_TIMEOUT = 60