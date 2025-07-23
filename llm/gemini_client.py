import google.generativeai as genai
from config import Config
import logging
import time
import random

logger = logging.getLogger(__name__)

try:
    genai.configure(api_key=Config.GEMINI_API_KEY)
    logger.info("Gemini configured")
except Exception as e:
    logger.error(f"Gemini config error: {str(e)}")

def generate_text(prompt, model=Config.GEMINI_MODEL):
    for attempt in range(Config.MAX_LLM_RETRIES):
        try:
            model_instance = genai.GenerativeModel(model)
            response = model_instance.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    top_p=0.95
                ),
                safety_settings={
                    'HATE': 'BLOCK_NONE',
                    'HARASSMENT': 'BLOCK_NONE',
                    'SEXUAL': 'BLOCK_NONE',
                    'DANGEROUS': 'BLOCK_NONE'
                },
                request_options={'timeout': Config.LLM_TIMEOUT}
            )
            
            # Extract text from response
            if hasattr(response, 'text'):
                return response.text
            elif hasattr(response, 'candidates') and response.candidates:
                return response.candidates[0].content.parts[0].text
            else:
                return str(response)
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "quota" in error_str.lower():
                wait_time = random.randint(5, 15) * (attempt + 1)
                logger.warning(f"Rate limit, retrying in {wait_time}s")
                time.sleep(wait_time)
            elif "500" in error_str or "internal" in error_str.lower():
                wait_time = random.randint(3, 8)
                logger.warning(f"Server error, retrying in {wait_time}s")
                time.sleep(wait_time)
            else:
                logger.error(f"Gemini API error: {error_str}")
                if attempt >= 2:  # Return after 2 non-retryable errors
                    return "Error: Gemini response failed"
    
    logger.error("Gemini response failed after retries")
    return "Error: Gemini response failed after retries"