from database import pinecone_setup
from llm import openai_client, gemini_client, perplexity_client, response_ranker
from config import Config
import logging
import re
import concurrent.futures

logger = logging.getLogger(__name__)

# Import the result logger instance
try:
    from utils.result_logger import result_logger
except ImportError:
    # Create a dummy logger if import fails
    class DummyLogger:
        def log_rag_retrieval(self, *args, **kwargs): pass
        def log_llm_response(self, *args, **kwargs): pass
        def log_llm_comparison(self, *args, **kwargs): pass
        def log_all_llm_responses(self, *args, **kwargs): pass
    result_logger = DummyLogger()

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
        namespace=namespace
        )
    # Filter by score manually
        if results.get('matches'):
            results['matches'] = [m for m in results['matches'] if m['score'] >= Config.CONTENT_THRESHOLD]
    except Exception as e:
        logger.error(f"Pinecone error: {str(e)}")
        return {"response": "Error retrieving information", "sources": [], "llm_source": "Error"}
       
        
        # Log RAG retrieval results
        rag_matches = []
        for match in results.get('matches', []):
            rag_matches.append({
                'score': match['score'],
                'source': match.get('metadata', {}).get('original_file', 'unknown'),
                'content_preview': match.get('metadata', {}).get('text', '')[:200]
            })
        
        result_logger.log_rag_retrieval(module, topic, rag_matches)
        
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
        "detailed": """Provide a comprehensive theoretical explanation with:
        1. Mathematical foundations with LaTeX formulas
        2. Historical context and evolution
        3. Conceptual frameworks and mental models
        4. Complete coverage of key concepts
        5. Detailed examples and case studies
        """,
        "practical": """Focus on implementation with:
        1. Complete runnable Python code examples
        2. Step-by-step implementation guides
        3. Real-world applications and use cases
        4. Best practices and optimization techniques
        5. Common pitfalls and solutions
        """,
        "experimental": """Include hands-on activities:
        1. Experimental designs and methodologies
        2. Case studies with data analysis
        3. Validation methods and metrics
        4. Hands-on exercises and activities
        """,
        "conceptual": """Explain fundamental principles:
        1. Core concepts and relationships
        2. Mental models and analogies
        3. Fundamental principles and theories
        4. Conceptual frameworks
        """
    }
    style_instruction = style_instructions.get(style, style_instructions["detailed"])
    
    # Create a more reasonable prompt that won't get rejected
    prompt = f"""
    Generate comprehensive learning content about: {topic}
    
    IMPORTANT: Provide a thorough, detailed explanation suitable for educational purposes.
    
    Learning Style Requirements: {style_instruction}
    
    Context from course materials (use as reference):
    {context[:4000] + '...' if len(context) > 4000 else context}
    
    Please structure your response as follows:
    
    ## 1. Comprehensive Explanation
    - Theoretical foundations
    - Mathematical formulations (use LaTeX for formulas)
    - Key principles and concepts
    - Historical context if relevant
    
    ## 2. Practical Implementation
    - Implementation guidelines
    - Code examples (if applicable)
    - Best practices
    - Common challenges and solutions
    
    ## 3. Applications
    - Real-world use cases
    - Industry applications
    - Case studies
    
    ## 4. Learning Resources
    - Key takeaways
    - Further reading
    - Practice suggestions
    
    Please ensure the response is:
    1. Complete and comprehensive
    2. Well-structured and organized
    3. Educational and informative
    4. Suitable for learners at various levels
    
    Cite sources from the context using markers like [Source 1].
    """
    
    # Separate function for OpenAI with different approach
    def run_openai_with_logging():
        """Special handling for OpenAI to ensure complete responses"""
        # Create a more focused prompt for OpenAI
        openai_prompt = f"""
        As an expert educator, provide a comprehensive explanation of: {topic}
        
        Please cover:
        1. Core concepts and definitions
        2. Theoretical foundations
        3. Practical applications
        4. Examples and case studies
        5. Learning resources and next steps
        
        Ensure your response is thorough and educational. Include:
        - Clear explanations
        - Relevant examples
        - Practical insights
        - Learning guidance
        
        Context references: {context[:2000] if len(context) > 2000 else context}
        
        Your response should be detailed enough for someone to learn the topic effectively.
        """
        
        try:
            response = openai_client.chat_completion(openai_prompt)
            if not response or len(response.strip()) < 100:
                logger.warning(f"OpenAI response too short, trying alternative approach")
                # Try with a simpler prompt
                alt_prompt = f"Explain {topic} comprehensively for educational purposes. Include key concepts, examples, and applications."
                response = openai_client.chat_completion(alt_prompt)
            
            result_logger.log_llm_response("OpenAI", openai_prompt[:500] + "...", response, len(response))
            return ensure_complete_response(response, "OpenAI")
        except Exception as e:
            logger.error(f"OpenAI generation error: {str(e)}")
            return generate_fallback_response(topic, "OpenAI")
    
    def run_gemini_with_logging():
        try:
            response = gemini_client.generate_text(prompt)
            result_logger.log_llm_response("Gemini", prompt[:500] + "...", response, len(response))
            return ensure_complete_response(response, "Gemini")
        except Exception as e:
            logger.error(f"Gemini generation error: {str(e)}")
            return generate_fallback_response(topic, "Gemini")
    
    def run_perplexity_with_logging():
        try:
            response = perplexity_client.perplexity_completion(prompt)
            result_logger.log_llm_response("Perplexity", prompt[:500] + "...", response, len(response))
            return ensure_complete_response(response, "Perplexity")
        except Exception as e:
            logger.error(f"Perplexity generation error: {str(e)}")
            return generate_fallback_response(topic, "Perplexity")
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_openai = executor.submit(run_openai_with_logging)
        future_gemini = executor.submit(run_gemini_with_logging)
        
        openai_resp = future_openai.result()
        gemini_resp = future_gemini.result()
        perplexity_resp = "Error: Perplexity disabled"
    
    # Get all 3 responses for complete peer review matrix
    responses_list = [
        {"model": "OpenAI", "content": openai_resp},
        {"model": "Gemini", "content": gemini_resp},
        {"model": "Perplexity", "content": perplexity_resp}
    ]
    
    # Log ALL responses before peer review
    result_logger.log_all_llm_responses(topic, responses_list)
    
    logger.info(f"Response lengths - OpenAI: {len(openai_resp)} chars, "
               f"Gemini: {len(gemini_resp)} chars, Perplexity: {len(perplexity_resp)} chars")
    
    # Pass all 3 responses to peer review scoring
    selected_response = response_ranker.select_best_response(
        query=topic,
        responses=[openai_resp, gemini_resp, perplexity_resp],
        context=context
    )

    # Log LLM comparison with all 3 models
    result_logger.log_llm_comparison(topic, responses_list, selected_response)
    
    return {
        "response": selected_response['content'],
        "sources": sources,
        "llm_source": selected_response['model'],
        "peer_review_score": selected_response.get('score', 0)
    }

def ensure_complete_response(response, model_name):
    """Ensure response is complete and comprehensive"""
    if not response:
        return generate_fallback_response("the topic", model_name)
    
    response = response.strip()
    
    # Check for rejection messages
    rejection_patterns = [
        r"I'm sorry",
        r"I can't",
        r"I cannot",
        r"apologize",
        r"unable to",
        r"not allowed",
        r"cannot fulfill",
        r"won't generate"
    ]
    
    for pattern in rejection_patterns:
        if re.search(pattern, response, re.IGNORECASE):
            logger.warning(f"{model_name} response appears to be a rejection")
            return generate_fallback_response("the topic", model_name)
    
    # Check if response is too short
    if len(response) < 500:
        logger.warning(f"{model_name} response too short ({len(response)} chars), extending")
        return extend_response(response, model_name)
    
    # Check if response ends abruptly
    if not response.endswith(('.', '!', '?')) and len(response) > 1000:
        # Try to find a natural ending point
        sentences = response.split('.')
        if len(sentences) > 3:
            # Take all but the last incomplete sentence
            response = '.'.join(sentences[:-1]) + '.'
    
    return response

def extend_response(response, model_name):
    """Extend a short response"""
    extension = f"""
    
    ## Additional Information from {model_name}
    
    To provide more comprehensive coverage:
    
    ### Extended Explanation
    The topic requires understanding of both theoretical foundations and practical applications. 
    
    ### Key Concepts
    1. Fundamental principles and definitions
    2. Core methodologies and approaches
    3. Implementation considerations
    4. Performance metrics and evaluation
    
    ### Practical Applications
    - Real-world use cases across different domains
    - Industry-specific implementations
    - Research applications and methodologies
    
    ### Learning Path
    - Foundational knowledge requirements
    - Skill development progression
    - Advanced topics and specializations
    
    ### Resources and References
    - Recommended reading materials
    - Practice exercises and projects
    - Community resources and forums
    
    This extended content ensures learners receive complete educational coverage.
    """
    
    return response + extension

def generate_fallback_response(topic, model_name):
    """Generate a fallback response when model fails"""
    fallback = f"""
    ## Comprehensive Explanation of {topic}
    
    ### Overview
    {topic} is a fundamental concept in data science and machine learning that involves transforming raw data into meaningful features for analysis and modeling.
    
    ### Core Concepts
    1. **Definition and Scope**: Understanding what {topic} entails and its importance in data processing pipelines.
    2. **Theoretical Foundations**: Mathematical and statistical principles underlying {topic}.
    3. **Methodologies**: Different approaches and techniques for effective {topic}.
    4. **Applications**: How {topic} is used in various domains including business, research, and industry.
    
    ### Implementation Guidelines
    - **Step-by-step process** for implementing {topic} in practical scenarios
    - **Best practices** for optimal results
    - **Common challenges** and solutions
    - **Tools and technologies** commonly used
    
    ### Case Studies
    1. **Business Application**: How {topic} improves decision-making in organizational contexts
    2. **Research Application**: Use of {topic} in academic and scientific research
    3. **Industry Application**: Real-world implementations across different sectors
    
    ### Learning Resources
    - **Key textbooks and references**
    - **Online courses and tutorials**
    - **Practice datasets and exercises**
    - **Community forums and discussions**
    
    ### Assessment
    - **Self-evaluation questions** to test understanding
    - **Practical exercises** to apply knowledge
    - **Further exploration** topics for advanced learning
    
    *Note: This is a fallback response generated by the system as {model_name} was unable to provide a complete answer.*
    """
    
    return fallback

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