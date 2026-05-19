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
    
    # Try multiple models - Perplexity frequently updates model names
    models_to_try = [
        "sonar",
        "sonar-pro"
    ]
    
    for model in models_to_try:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are an expert educator providing comprehensive explanations."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 4000,
            "temperature": 0.3
        }
        
        try:
            logger.info(f"Trying Perplexity model: {model}")
            response = requests.post(url, headers=headers, json=payload, timeout=Config.LLM_TIMEOUT)
            response.raise_for_status()
            result = response.json()
            
            if "choices" in result and len(result["choices"]) > 0:
                logger.info(f"Success with model: {model}")
                return result["choices"][0]["message"]["content"]
            else:
                logger.warning(f"Empty response from model: {model}")
                
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 400:
                logger.warning(f"Model {model} not available or invalid")
                continue  # Try next model
            else:
                logger.error(f"HTTP error with {model}: {str(e)}")
                time.sleep(random.randint(2, 5))
        except Exception as e:
            logger.error(f"Error with model {model}: {str(e)}")
            time.sleep(random.randint(2, 5))
    
    logger.error("All Perplexity models failed")
    return "Error: Perplexity response failed"