import os
import re
from database import pinecone_setup, document_loader
from llm.openai_client import get_embedding, is_zero_vector
from config import Config
import time
import hashlib
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler('upload.log')]
)
logger = logging.getLogger(__name__)

def upload_documents():
    try:
        pc_index = pinecone_setup.initialize_pinecone()
        processed_files = set()
        total_chunks = 0
        skipped_chunks = 0
        os.makedirs(Config.DATA_DIR, exist_ok=True)
        
        for root, _, files in os.walk(Config.DATA_DIR):
            for file in files:
                if file.lower().endswith(('.pdf', '.pptx', '.docx')):
                    file_path = os.path.join(root, file)
                    logger.info(f"Processing: {file_path}")
                    
                    try:
                        text, rel_path, file_metadata = document_loader.process_file(file_path)
                        if not text.strip():
                            logger.warning(f"Skipping empty file: {file_path}")
                            continue
                            
                        chunks = document_loader.chunk_text(
                            text, 
                            rel_path,
                            chunk_size=Config.CHUNK_SIZE,
                            chunk_overlap=Config.CHUNK_OVERLAP
                        )
                        
                        vectors = []
                        module = document_loader.get_module_from_path(file_path)
                        namespace = f"module{module}"
                        
                        logger.info(f"Created {len(chunks)} chunks")
                        
                        for i, chunk_data in enumerate(chunks):
                            chunk_text = chunk_data["text"]
                            metadata = chunk_data.get("metadata", {})
                            
                            # Ensure metadata values are simple types
                            clean_metadata = {
                                "file_type": os.path.splitext(file)[1],
                                "original_file": os.path.basename(file_path),
                                "module": module,
                                "source": rel_path,
                                "page": metadata.get("page", 1),
                                "slide": metadata.get("slide", 1),
                                "section": metadata.get("section", 1),
                                "text": chunk_text[:500]
                            }
                            
                            embedding = get_embedding(chunk_text)
                            if is_zero_vector(embedding):
                                skipped_chunks += 1
                                logger.warning(f"Skipping zero vector chunk")
                                continue
                            
                            unique_id = hashlib.md5(f"{rel_path}_{i}".encode()).hexdigest()
                            vectors.append({
                                "id": unique_id,
                                "values": embedding,
                                "metadata": clean_metadata
                            })
                        
                        if vectors:
                            success = pinecone_setup.upsert_documents(pc_index, vectors, namespace)
                            if success:
                                total_chunks += len(vectors)
                                processed_files.add(file_path)
                                logger.info(f"Uploaded {len(vectors)} chunks to {namespace}")
                    except Exception as e:
                        logger.error(f"Error processing {file_path}: {str(e)}")
        
        logger.info(f"Upload complete! Processed {len(processed_files)} files")
        logger.info(f"Total chunks: {total_chunks}, Skipped: {skipped_chunks}")
        return True
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        return False

if __name__ == "__main__":
    upload_documents()