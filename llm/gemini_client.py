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

def generate_text(prompt, model=None):
    """
    Generate text using Gemini API with fallback models
    """
    if model is None:
        model = Config.GEMINI_MODEL
    
    available_models = [
        "gemini-2.5-flash-lite",
        "gemini-1.5-pro-latest",  # Most reliable
        "gemini-1.5-pro",         # Alternative
        "gemini-1.5-flash-latest", # Faster
        "gemini-1.5-flash",        # Fast alternative
        "gemini-pro",             # Legacy
    ]
    
    # Start with configured model, then try others
    models_to_try = [model] + [m for m in available_models if m != model]
    
    for model_to_try in models_to_try:
        logger.info(f"Trying Gemini model: {model_to_try}")
        
        for attempt in range(Config.MAX_LLM_RETRIES):
            try:
                model_instance = genai.GenerativeModel(model_to_try)
                response = model_instance.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.3,
                        top_p=0.95,
                        max_output_tokens=4000
                    ),
                    safety_settings={
                        'HATE': 'BLOCK_NONE',
                        'HARASSMENT': 'BLOCK_NONE',
                        'SEXUAL': 'BLOCK_NONE',
                        'DANGEROUS': 'BLOCK_NONE'
                    }
                )
                
                if response.text:
                    logger.info(f"Success with Gemini model: {model_to_try}")
                    return response.text
                else:
                    logger.warning(f"Empty response from Gemini model: {model_to_try}")
                    break  # Try next model
                    
            except Exception as e:
                error_str = str(e)
                
                # Rate limit - wait and retry same model
                if "429" in error_str or "quota" in error_str.lower() or "rate limit" in error_str.lower():
                    wait_time = random.randint(10, 30)  # Longer wait for rate limits
                    logger.warning(f"Gemini rate limit on {model_to_try}, waiting {wait_time}s (attempt {attempt+1})")
                    time.sleep(wait_time)
                    continue  # Retry same model
                
                # Model not found - try next model immediately
                elif "404" in error_str or "not found" in error_str.lower():
                    logger.warning(f"Gemini model {model_to_try} not available")
                    break  # Try next model
                
                # Other errors
                else:
                    logger.error(f"Gemini error with model {model_to_try}: {error_str}")
                    if attempt >= 2:
                        break  # Move to next model after 3 attempts
    
    logger.error("All Gemini models failed")
    return "Error: Gemini response failed"