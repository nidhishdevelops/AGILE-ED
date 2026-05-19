import requests
import json
import logging
import time
from config import Config

logger = logging.getLogger(__name__)

def ollama_completion(prompt, model="llama3.2"):
    """
    Generate text using Ollama's API.
    Default model can be changed in config.
    """
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.3,
            "top_p": 0.95,
            "num_predict": 4000
        }
    }
    
    try:
        response = requests.post(url, json=payload, timeout=Config.LLM_TIMEOUT)
        response.raise_for_status()
        result = response.json()
        return result.get("response", "")
    except Exception as e:
        logger.error(f"Ollama error: {str(e)}")
        return "Error: Ollama response failed"