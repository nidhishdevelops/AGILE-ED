from database import pinecone_setup
from llm import openai_client, gemini_client, perplexity_client, response_ranker
from config import Config
import logging
import re
import concurrent.futures

logger = logging.getLogger(__name__)

def retrieve_and_generate(module, topic, style):
    if module == 0:
        return {
            "response": "TOPIC_NOT_FOUND",
            "sources": [],
            "llm_source": "System",
        }
    
    pc_index = pinecone_setup.initialize_pinecone()
    namespace = f"module{module}"
    query_embedding = openai_client.get_embedding(topic)
    
    try:
        results = pc_index.query(
            vector=query_embedding,
            top_k=15,
            include_metadata=True,
            namespace=namespace,
            min_score=Config.CONTENT_THRESHOLD
        )
    except Exception as e:
        logger.error(f"Pinecone error: {str(e)}")
        return {"response": "Error retrieving information", "sources": [], "llm_source": "Error"}

    context = ""
    sources = []
    valid_matches = [m for m in results.get('matches', []) if m['score'] >= Config.CONTENT_THRESHOLD]
    
    if not valid_matches:
        logger.warning(f"No relevant content for '{topic}' in module {module}")
        return {"response": "TOPIC_NOT_FOUND", "sources": [], "llm_source": "System"}
    
    for i, match in enumerate(valid_matches[:10]):
        metadata = match.get('metadata', {})
        text_content = metadata.get('text', '')
        if not text_content.strip():
            continue
            
        location = extract_location(metadata)
        source_str = f"[Source {i+1}]"
        context += f"{source_str}: {text_content}\n\n"
        
        sources.append({
            "source": metadata.get('source', 'Unknown'),
            "location": location,
            "text": text_content[:200] + "..." if len(text_content) > 200 else text_content,
            "file_type": metadata.get('file_type', ''),
            "original_file": metadata.get('original_file', 'Unknown'),
            "source_ref": source_str
        })
    
    style_instructions = {
        "detailed": "Provide an exhaustive theoretical explanation (3000-5000 words) with mathematical foundations, historical context, and conceptual frameworks. Include formulas in LaTeX with explanations.",
        "practical": "Focus on implementation with complete runnable Python code examples, real-world applications, and best practices.",
        "experimental": "Include hands-on activities, experimental designs, and case studies",
        "conceptual": "Explain fundamental principles, relationships, and mental models"
    }
    style_instruction = style_instructions.get(style, style_instructions["detailed"])
    
    prompt = f"""
    Generate comprehensive learning content about: {topic}
    Learning Style: {style_instruction}
    
    Context:
    {context[:6000] + '...' if len(context) > 6000 else context}
    
    Structure in markdown:
    
    ## Comprehensive Explanation
    - Theoretical foundations Detailed explanation
    - Mathematical formulations (LaTeX with explanations) and detailed explanations
    - Key principles and concepts in detailed manner
    
    ## Practical Implementation
    - Step-by-step implementation guide
    - Complete runnable Python code
    - Best practices and pitfalls
    
    ## Experimental Learning
    - Hands-on activities
    - Validation methods
    - Case studies
    
    ## Recent Advancements (2023-Present)
    Summary of latest research and articles related to the topic
    
    ## Research Papers
    3-5 seminal papers with summaries and valid URLs
    
    ### Source Citations
    Cite sources using markers like [Source 1]
    Include specific locations (page numbers, slide numbers)
    """
    
    # Run LLMs in parallel
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_openai = executor.submit(openai_client.chat_completion, prompt)
        future_gemini = executor.submit(gemini_client.generate_text, prompt)
        future_perplexity = executor.submit(perplexity_client.perplexity_completion, prompt)
        
        openai_resp = future_openai.result()
        gemini_resp = future_gemini.result()
        perplexity_resp = future_perplexity.result()
    
    selected_response = response_ranker.select_best_response(
        query=topic,
        responses=[openai_resp, gemini_resp, perplexity_resp],
        context=context
    )
    
    return {
        "response": selected_response['content'],
        "sources": sources,
        "llm_source": selected_response['model'],
    }

def extract_location(metadata):
    location_parts = []
    if metadata.get('page'):
        location_parts.append(f"Page {metadata['page']}")
    if metadata.get('slide'):
        location_parts.append(f"Slide {metadata['slide']}")
    if metadata.get('section'):
        location_parts.append(f"Section {metadata['section']}")
    if metadata.get('slide_title'):
        location_parts.append(f"'{metadata['slide_title']}'")
    return " - ".join(location_parts) if location_parts else "Location unknown"