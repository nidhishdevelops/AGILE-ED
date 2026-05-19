from llm import openai_client, gemini_client, perplexity_client
import json
import re
import numpy as np
from config import Config
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Import the result logger instance
try:
    from utils.result_logger import result_logger
except ImportError:
    # Create a dummy logger if import fails
    class DummyLogger:  
        def log_evaluation(self, *args, **kwargs): 
            logger.info(f"Evaluation log attempt: {args}, {kwargs}")
        def log_llm_comparison(self, *args, **kwargs): pass
    result_logger = DummyLogger()


def select_best_response(query, responses, context):
    # DEBUG: Log what we're receiving
    logger.info(f"select_best_response called with {len(responses)} responses")
    for i, resp in enumerate(responses):
        logger.info(f"Response {i} type: {type(resp)}, length: {len(str(resp)) if resp else 0}, "
                   f"first 100 chars: '{str(resp)[:100] if resp else 'EMPTY'}'")
    
    # Filter out error responses and collect valid ones
    valid_responses = []
    models = []
    model_names = ["OpenAI", "Gemini", "Perplexity"]
    
    for i, resp in enumerate(responses):
        # Check if response is valid
        is_valid = True
        
        # Check for various error conditions
        if resp is None:
            logger.warning(f"Response {i} ({model_names[i]}) is None")
            is_valid = False
        elif not resp.strip():
            logger.warning(f"Response {i} ({model_names[i]}) is empty or whitespace only")
            is_valid = False
        elif isinstance(resp, str) and resp.startswith("Error:") and len(resp) < 200:
            logger.warning(f"Response {i} ({model_names[i]}) contains 'Error': {resp[:100]}")
            is_valid = False
        elif isinstance(resp, str) and len(resp.strip()) < 50:  # Very short response
            logger.warning(f"Response {i} ({model_names[i]}) is too short: {len(resp)} chars")
            is_valid = False
        
        if is_valid:
            valid_responses.append(resp)
            models.append(model_names[i])
            logger.info(f" Valid response from {model_names[i]}: {len(resp)} chars")
        else:
            logger.warning(f" Invalid response from {model_names[i]}")
    
    logger.info(f"Total valid responses: {len(valid_responses)} (OpenAI: {'OpenAI' in models}, "
               f"Gemini: {'Gemini' in models}, Perplexity: {'Perplexity' in models})")
    
    if not valid_responses:
        logger.error("No valid responses from any LLM")
        return {"content": "All LLMs failed to respond", "model": "System"}
    
    if len(valid_responses) == 1:
        logger.info(f"Only 1 valid response, using {models[0]}")
        return {"content": valid_responses[0], "model": models[0]}
    
    # Apply paper's mathematical scoring with complete blind peer review
    logger.info(f"Starting complete blind peer review with {len(valid_responses)} responses")
    scores = complete_blind_peer_review(valid_responses, query, context, models)
    
    # Select response with highest score
    best_index = np.argmax(scores)
    
    logger.info(f"Selected response {best_index} from {models[best_index]} with score {scores[best_index]:.3f}")
    
    return {
        "content": valid_responses[best_index],
        "model": models[best_index],
        "score": float(scores[best_index])
    }

def complete_blind_peer_review(responses, query, context, model_names):
    """
    Complete blind peer review: Each model evaluates ALL responses
    Total evaluations: M models × N responses evaluations
    """
    
    # Criterion weights as per paper
    CRITERIA_WEIGHTS = {
        "accuracy": 0.4,
        "depth": 0.3,
        "citations": 0.2,
        "clarity": 0.1
    }
    
    N = len(responses)  # Number of valid responses
    M = len(model_names)  # Number of evaluators
    
    logger.info(f"Starting peer review: {M} evaluators will evaluate {N} responses")
    logger.info(f"Evaluators: {model_names}")
    logger.info(f"Response counts: {N}")
    
    scores = np.zeros(N)
    all_evaluations = []
    
    # Truncate context for scoring prompts
    scoring_context = context[:2000] + "..." if len(context) > 2000 else context
    
    # Create anonymized responses for evaluation
    anonymized_responses = []
    for i, resp in enumerate(responses):
        truncated_resp = resp[:1500] + "..." if len(resp) > 1500 else resp
        anonymized_responses.append(truncated_resp)
        logger.info(f"Response {i} truncated to {len(truncated_resp)} chars")
    
    # Each evaluator evaluates ALL responses
    for evaluator_idx, evaluator_name in enumerate(model_names):
        logger.info(f"=== {evaluator_name} evaluating all {N} responses ===")
        
        evaluator_model = get_evaluator_model(evaluator_idx)
        
        # This evaluator evaluates ALL responses
        for response_idx in range(N):
            logger.info(f"{evaluator_name} evaluating Response {response_idx}")
            
            # Check if this is a self-evaluation
            is_self_evaluation = (evaluator_idx == response_idx)
            
            criteria_scores = evaluate_response_criteria_blind(
                evaluator_model,
                evaluator_name,
                anonymized_responses[response_idx],
                query,
                scoring_context,
                CRITERIA_WEIGHTS,
                response_index=response_idx,
                evaluator_index=evaluator_idx
            )
            
            if criteria_scores:
                weighted_score = sum(
                    CRITERIA_WEIGHTS[criterion] * score 
                    for criterion, score in criteria_scores.items()
                )
                
                # Log each evaluation individually
                evaluation_entry = {
                    "evaluator": evaluator_name,
                    "response_index": response_idx,
                    "response_model": model_names[response_idx] if response_idx < len(model_names) else f"Response_{response_idx}",
                    "criteria_scores": criteria_scores,
                    "weighted_score": weighted_score,
                    "is_self_evaluation": is_self_evaluation,
                    "evaluation_timestamp": None  # Will be set by logger
                }
                
                all_evaluations.append(evaluation_entry)
                
                # Log this evaluation to result_logger
                try:
                    result_logger.log_evaluation(
                        criteria_scores=criteria_scores,
                        evaluator_model=evaluator_name,
                        response_index=response_idx,
                        response_model=model_names[response_idx] if response_idx < len(model_names) else f"Response_{response_idx}",
                        weighted_score=weighted_score,
                        is_self_evaluation=is_self_evaluation
                    )
                    logger.info(f"Logged evaluation: {evaluator_name} -> Response {response_idx} ({model_names[response_idx] if response_idx < len(model_names) else f'Response_{response_idx}'})")
                except Exception as e:
                    logger.error(f"Failed to log evaluation: {str(e)}")
                
                logger.info(f"Evaluation {evaluator_name} -> Response {response_idx} "
                           f"({model_names[response_idx] if response_idx < len(model_names) else f'Response_{response_idx}'}) "
                           f"{'(SELF)' if is_self_evaluation else ''}: {weighted_score:.3f}")
            else:
                logger.error(f"Failed evaluation: {evaluator_name} -> Response {response_idx}")
    
    # Calculate final scores for each response
    for response_idx in range(N):
        response_evaluations = [e for e in all_evaluations if e["response_index"] == response_idx]
        if response_evaluations:
            # Calculate weighted average (higher weight for non-self evaluations)
            weighted_scores = []
            weights = []
            
            for eval_data in response_evaluations:
                score = eval_data["weighted_score"]
                weight = 0.7 if not eval_data["is_self_evaluation"] else 0.3  # Lower weight for self-evaluations
                weighted_scores.append(score * weight)
                weights.append(weight)
            
            if sum(weights) > 0:
                avg_score = sum(weighted_scores) / sum(weights)
            else:
                avg_score = np.mean([e["weighted_score"] for e in response_evaluations])
            
            scores[response_idx] = avg_score
            
            evaluators = [e["evaluator"] for e in response_evaluations]
            logger.info(f"Response {response_idx} ({model_names[response_idx] if response_idx < len(model_names) else f'Response_{response_idx}'}) "
                       f"score: {avg_score:.3f} from {len(response_evaluations)} evaluations "
                       f"(evaluators: {', '.join(evaluators)})")
        else:
            scores[response_idx] = 0.5
            logger.warning(f"Response {response_idx} got no evaluations")
    
    # Log all evaluations summary
    logger.info(f"Total evaluations: {len(all_evaluations)} (Matrix: {M}×{N} = {M*N})")
    logger.info(f"Final scores: {list(scores)}")
    
    # Log the complete evaluation matrix
    logger.info("\n" + "="*80)
    logger.info("COMPLETE PEER REVIEW EVALUATION MATRIX")
    logger.info("="*80)
    for eval_data in all_evaluations:
        # Compute model name safely outside f-string
        if eval_data['response_index'] < len(model_names):
            resp_model = model_names[eval_data['response_index']]
        else:
            resp_model = f"Response_{eval_data['response_index']}"

        logger.info(f"{evaluator_name} -> Response {response_idx} ({resp_model}) "
           f"{'(SELF)' if eval_data['is_self_evaluation'] else ''}")
    
    return scores

def evaluate_response_criteria_blind(evaluator, evaluator_name, response, query, context, criteria_weights, response_index, evaluator_index):
    """Have an LLM evaluate a response on all criteria - COMPLETELY BLIND"""
    
    prompt = f"""
    You are an expert evaluator of educational content. Evaluate the following response.
    
    IMPORTANT: This is a BLIND evaluation. You do NOT know which model created this.
    
    QUERY: "{query}"
    
    CONTEXT: {context[:800] if len(context) > 800 else context}
    
    RESPONSE: {response}
    
    Score each criterion 0.0-1.0:
    1. ACCURACY: Factual correctness, alignment with query
    2. DEPTH: Comprehensive coverage, thoroughness  
    3. CITATIONS: Proper source attribution, referencing
    4. CLARITY: Readability, structure, organization
    
    Return ONLY JSON:
    {{
        "accuracy": 0.0,
        "depth": 0.0, 
        "citations": 0.0,
        "clarity": 0.0,
        "comments": "brief comments on strengths/weaknesses"
    }}
    """
    
    try:
        completion_method = get_evaluator_method(evaluator, evaluator_name)
        evaluation_text = completion_method(prompt)
        
        if not evaluation_text or "Error" in evaluation_text:
            logger.error(f"{evaluator_name} evaluation failed for Response {response_index}")
            return get_default_scores(criteria_weights, response_index, evaluator_name)
        
        evaluation_text = evaluation_text.strip()
        evaluation_text = re.sub(r'```json\s*', '', evaluation_text)
        evaluation_text = re.sub(r'```\s*', '', evaluation_text)
        
        json_match = re.search(r'\{.*\}', evaluation_text, re.DOTALL)
        
        if json_match:
            try:
                result = json.loads(json_match.group(0))
                scores = {}
                for criterion in criteria_weights.keys():
                    if criterion in result:
                        try:
                            score = float(result[criterion])
                            score = max(0.0, min(1.0, score))
                            scores[criterion] = score
                        except:
                            scores[criterion] = 0.5
                    else:
                        scores[criterion] = 0.5
                return scores
            except Exception as e:
                logger.error(f"JSON parsing error for {evaluator_name} evaluation: {str(e)}")
                return get_default_scores(criteria_weights, response_index, evaluator_name)
        else:
            logger.error(f"No JSON found in {evaluator_name} evaluation response")
            return get_default_scores(criteria_weights, response_index, evaluator_name)
            
    except Exception as e:
        logger.error(f"Evaluation error: {evaluator_name} -> Response {response_index}: {str(e)}")
        return get_default_scores(criteria_weights, response_index, evaluator_name)

def get_evaluator_model(index):
    """Get appropriate LLM for evaluation based on index"""
    evaluators = [openai_client, gemini_client, perplexity_client]
    return evaluators[index % len(evaluators)]

def get_evaluator_method(evaluator, evaluator_name):
    """Get the correct completion method for each evaluator"""
    if evaluator_name == "OpenAI":
        return evaluator.chat_completion
    elif evaluator_name == "Gemini":
        return evaluator.generate_text
    elif evaluator_name == "Perplexity":
        return evaluator.perplexity_completion
    else:
        return evaluator.chat_completion

def get_default_scores(criteria_weights, response_index, evaluator_name):
    """Return default scores when evaluation fails"""
    scores = {criterion: 0.5 for criterion in criteria_weights.keys()}
    logger.warning(f"Using default scores for Response {response_index} from {evaluator_name}")
    return scores