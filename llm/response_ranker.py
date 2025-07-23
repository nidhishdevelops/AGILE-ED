from llm.openai_client import chat_completion
import json
import re
from config import Config

def select_best_response(query, responses, context):
    # Filter out error responses
    valid_responses = []
    models = []
    
    for i, resp in enumerate(responses):
        if "Error" not in resp:
            valid_responses.append(resp)
            models.append(["OpenAI", "Gemini", "Perplexity"][i])
    
    if not valid_responses:
        return {"content": "All LLMs failed to respond", "model": "System"}
    
    if len(valid_responses) == 1:
        return {"content": valid_responses[0], "model": models[0]}
    
    # Truncate context to fit within token limits
    context = context[:3000] + "..." if len(context) > 3000 else context
    
    comparison_prompt = f"""
    Compare {len(valid_responses)} responses to: "{query}"
    Evaluation Criteria:
    1. Accuracy to context (40%)
    2. Depth of analysis (3000-5000 words) (30%)
    3. Source citation accuracy (20%)
    4. Clarity and structure (10%)
    
    Context: {context}
    
    Responses:
    {''.join([f'\nResponse {chr(65+i)}:\n{r}\n' for i, r in enumerate(valid_responses)])}
    
    Output JSON: {{"choice": "A", "B", or "C", "reason": "Explanation"}}
    """
    
    result = chat_completion(comparison_prompt)
    
    try:
        # Extract JSON from response
        json_match = re.search(r'\{.*\}', result, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0))
            choice = data.get("choice", "A")
        else:
            choice = "A"
    except:
        choice = "A"
    
    choice_index = ord(choice) - 65
    if choice_index < len(valid_responses):
        return {
            "content": valid_responses[choice_index],
            "model": models[choice_index]
        }
    
    # Fallback to first valid response
    return {
        "content": valid_responses[0],
        "model": models[0]
    }