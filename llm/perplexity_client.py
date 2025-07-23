import requests
import json
import logging
import time
import random
from config import Config

logger = logging.getLogger(__name__)

def perplexity_completion(prompt):
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {Config.PERPLEXITY_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": Config.PERPLEXITY_MODEL,
        "messages": [
            {"role": "system", "content": "You are an expert educator providing comprehensive explanations."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3
    }
    
    for attempt in range(Config.MAX_LLM_RETRIES):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=Config.LLM_TIMEOUT)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except requests.exceptions.Timeout:
            logger.warning(f"Perplexity timeout on attempt {attempt+1}")
            time.sleep(random.randint(3, 8))
        except Exception as e:
            logger.error(f"Perplexity error (attempt {attempt+1}): {str(e)}")
            time.sleep(random.randint(2, 5))
    
    return "Error: Perplexity response failed"