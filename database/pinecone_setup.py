from pinecone import Pinecone, ServerlessSpec
from config import Config
import time
import logging
import json

logger = logging.getLogger(__name__)

def initialize_pinecone():
    try:
        pc = Pinecone(api_key=Config.PINECONE_API_KEY)
        index_name = Config.PINECONE_INDEX.lower()
        if index_name in pc.list_indexes().names():
            logger.info(f"Using index: {index_name}")
            return pc.Index(index_name)
        
        logger.info(f"Creating index: {index_name}")
        pc.create_index(
            name=index_name,
            dimension=1536,
            metric="cosine",
            spec=ServerlessSpec(cloud='aws', region='us-east-1')
        )
        time.sleep(30)
        return pc.Index(index_name)
    except Exception as e:
        logger.error(f"Pinecone init failed: {str(e)}")
        raise

def upsert_documents(index, documents, namespace):
    try:
        # Reduce batch size significantly for safety
        batch_size = 10  # Very conservative batch size
        
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i+batch_size]
            
            # Sanitize metadata before upsert
            sanitized_batch = []
            for doc in batch:
                sanitized_metadata = sanitize_metadata(doc.get('metadata', {}))
                sanitized_doc = {
                    "id": doc["id"],
                    "values": doc["values"],
                    "metadata": sanitized_metadata
                }
                sanitized_batch.append(sanitized_doc)
            
            index.upsert(vectors=sanitized_batch, namespace=namespace)
            logger.info(f"Upserted batch {i//batch_size+1} with {len(sanitized_batch)} vectors")
        return True
    except Exception as e:
        logger.error(f"Upsert failed: {str(e)}")
        return False

def sanitize_metadata(metadata):
    """Ensure all metadata values are Pinecone-compatible types"""
    sanitized = {}
    for key, value in metadata.items():
        if isinstance(value, (str, int, float, bool)):
            sanitized[key] = value
        elif isinstance(value, list):
            # Convert list elements to strings if needed
            sanitized[key] = [str(item) for item in value]
        else:
            # Convert any other type to string
            sanitized[key] = str(value)
    return sanitized