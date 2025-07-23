from openai import OpenAI
from config import Config
import time
import logging
import numpy as np
import random

logger = logging.getLogger(__name__)
client = OpenAI(api_key=Config.OPENAI_API_KEY)

def chat_completion(prompt, model=Config.OPENAI_MODEL):
    for attempt in range(Config.MAX_LLM_RETRIES):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            return response.choices[0].message.content
        except Exception as e:
            error_str = str(e)
            if "RateLimit" in error_str or "quota" in error_str.lower():
                wait = random.randint(2, 10) * (attempt + 1)
                logger.warning(f"Rate limit, retrying in {wait}s")
                time.sleep(wait)
            elif "Unsupported parameter" in error_str:
                # Fallback for parameter issues
                try:
                    response = client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    return response.choices[0].message.content
                except Exception as fallback_e:
                    logger.error(f"Fallback OpenAI error: {str(fallback_e)}")
                    return "Error: OpenAI response failed"
            else:
                logger.error(f"OpenAI API error: {str(e)}")
                if attempt == Config.MAX_LLM_RETRIES - 1:
                    return "Error: OpenAI response failed"
    
    return "Error: OpenAI response failed after retries"

def get_embedding(text, model="text-embedding-3-small"):
    if not text.strip():
        return [0.0] * 1536
        
    for attempt in range(Config.MAX_LLM_RETRIES):
        try:
            response = client.embeddings.create(input=[text], model=model)
            return response.data[0].embedding
        except Exception as e:
            if "RateLimit" in str(e) or "quota" in str(e).lower():
                wait = random.randint(1, 5) * (attempt + 1)
                logger.warning(f"Embedding rate limit, retrying in {wait}s")
                time.sleep(wait)
            else:
                logger.error(f"Embedding error: {str(e)}")
                if attempt == Config.MAX_LLM_RETRIES - 1:
                    return [0.0] * 1536
    
    return [0.0] * 1536

def is_zero_vector(embedding):
    return all(abs(x) < 1e-6 for x in embedding)