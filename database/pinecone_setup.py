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
        
        logger.info(f"Creating index: {index_name} with dimension {Config.PINECONE_DIMENSION}")
        pc.create_index(
            name=index_name,
            dimension=Config.PINECONE_DIMENSION,  # Use from config
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
        batch_size = 10 
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i+batch_size]
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
    sanitized = {}
    for key, value in metadata.items():
        if isinstance(value, (str, int, float, bool)):
            sanitized[key] = value
        elif isinstance(value, list):
            sanitized[key] = [str(item) for item in value]
        else:
            sanitized[key] = str(value)
    return sanitized
def list_namespaces():
    """List all namespaces in the index"""
    try:
        pc_index = initialize_pinecone()
        stats = pc_index.describe_index_stats()
        namespaces = list(stats.get('namespaces', {}).keys())
        return namespaces
    except Exception as e:
        logger.error(f"Error listing namespaces: {str(e)}")
        return []

def clear_namespace(namespace):
    """Clear all vectors from a namespace"""
    try:
        pc_index = initialize_pinecone()
        pc_index.delete(delete_all=True, namespace=namespace)
        logger.info(f"Cleared namespace: {namespace}")
        return True
    except Exception as e:
        logger.error(f"Error clearing namespace {namespace}: {str(e)}")
        return False

def get_namespace_stats(namespace):
    """Get statistics for a specific namespace"""
    try:
        pc_index = initialize_pinecone()
        stats = pc_index.describe_index_stats()
        namespace_stats = stats.get('namespaces', {}).get(namespace, {})
        return namespace_stats
    except Exception as e:
        logger.error(f"Error getting stats for {namespace}: {str(e)}")
        return {}