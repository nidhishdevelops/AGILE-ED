import re
import logging
import json
from openai import OpenAI
from config import Config
from llm.openai_client import get_embedding
from database import pinecone_setup
import numpy as np

logger = logging.getLogger(__name__)
client = OpenAI(api_key=Config.OPENAI_API_KEY)

def determine_module_and_style(query):
    try:
        topic, style = extract_topic_and_style(query)
        in_domain = is_data_science_topic(topic)
        if not in_domain:
            return {"module": 0, "topic": topic, "style": style, "in_domain": False}
        module = find_topic_module(topic)
        return {"module": module, "topic": topic, "style": style, "in_domain": True}
    except Exception as e:
        logger.error(f"Routing error: {str(e)}")
        return {"module": 0, "topic": query, "style": "detailed", "in_domain": True}

def extract_topic_and_style(query):
    prompt = f"""
    Extract the pure topic and learning style from: "{query}"
    Output JSON: {{"topic": "extracted topic", "style": "detailed|practical|experimental|conceptual"}}
    """
    try:
        response = client.chat.completions.create(
            model=Config.OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        data = json.loads(response.choices[0].message.content)
        return data.get('topic', query), data.get('style', 'detailed')
    except Exception as e:
        logger.error(f"Topic extraction error: {str(e)}")
        topic = re.sub(r'explain|what is|what\'s|how to|show me|I want a', '', query, flags=re.IGNORECASE).strip()
        style = "detailed"
        if "practical" in query.lower() or "implement" in query.lower():
            style = "practical"
        elif "experiment" in query.lower() or "hands-on" in query.lower():
            style = "experimental"
        elif "concept" in query.lower() or "theory" in query.lower():
            style = "conceptual"
        return re.sub(r'[^\w\s]', '', topic).strip(), style

def is_data_science_topic(topic):
    domain_keywords = [
        "data science", "statistics", "machine learning", "AI", "artificial intelligence",
        "data analysis", "data mining", "predictive modeling", "regression", "classification",
        "clustering", "probability", "hypothesis", "algorithm", "neural network", "deep learning",
        "natural language processing", "computer vision", "time series", "data visualization",
        "calculus", "mathematics", "linear algebra", "distributions", "history", "development",
        "theory", "foundation", "evolution", "math", "statistical"
    ]
    if any(keyword in topic.lower() for keyword in domain_keywords):
        return True
    prompt = f"Is '{topic}' within data science or related mathematical domains? Answer ONLY 'true' or 'false'"
    try:
        response = client.chat.completions.create(
            model=Config.OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}]
        )
        return "true" in response.choices[0].message.content.lower()
    except:
        return True

def find_topic_module(topic):
    try:
        pc_index = pinecone_setup.initialize_pinecone()
        query_embedding = get_embedding(topic)
        namespaces = ["module1", "module2", "module3", "module4"]
        best_score = Config.MIN_MODULE_CONFIDENCE
        best_namespace = None
        
        for namespace in namespaces:
            try:
                results = pc_index.query(
                    vector=query_embedding,
                    top_k=3,
                    include_metadata=True,
                    namespace=namespace,
                    min_score=best_score
                )
                if results['matches']:
                    top_match = results['matches'][0]
                    if top_match['score'] > best_score:
                        best_score = top_match['score']
                        best_namespace = namespace
            except Exception as e:
                logger.error(f"Query error in namespace {namespace}: {str(e)}")
                continue
        
        if best_namespace:
            module_num = int(best_namespace.replace("module", ""))
            logger.info(f"Topic '{topic}' found in {best_namespace} with score {best_score}")
            return module_num
        else:
            logger.warning(f"No strong match for '{topic}'")
            return 0
    except Exception as e:
        logger.error(f"Module detection error: {str(e)}")
        return 0