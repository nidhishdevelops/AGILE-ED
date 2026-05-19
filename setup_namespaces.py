#!/usr/bin/env python3
"""
Setup Pinecone namespaces for Personalized Learning System
"""
from database import pinecone_setup
from database.document_loader import get_module_from_path
import os
from config import Config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_namespaces():
    """Verify all required namespaces exist and have content"""
    try:
        pc_index = pinecone_setup.initialize_pinecone()
        
        print("🔍 Checking Pinecone namespaces...")
        print("=" * 50)
        
        # Namespaces that should exist
        expected_namespaces = ["module1", "module2", "module3", "module4"]
        
        # Get stats for each namespace
        for namespace in expected_namespaces:
            try:
                stats = pc_index.describe_index_stats()
                namespace_stats = stats.get('namespaces', {}).get(namespace, {})
                
                vector_count = namespace_stats.get('vector_count', 0)
                print(f"📦 {namespace}: {vector_count} vectors")
                
                if vector_count == 0:
                    print(f"   ⚠️  Empty namespace - upload data to /data/{namespace}/")
                elif vector_count < 10:
                    print(f"   ℹ️  Low content - consider adding more materials")
                else:
                    print(f"   ✅ Good content")
                    
            except Exception as e:
                print(f"❌ Error checking {namespace}: {e}")
        
        print("\n📊 Total Index Statistics:")
        total_stats = pc_index.describe_index_stats()
        print(f"   Total Vectors: {total_stats.get('total_vector_count', 0)}")
        print(f"   Namespaces: {len(total_stats.get('namespaces', {}))}")
        print(f"   Dimension: {total_stats.get('dimension', 'Unknown')}")
        
    except Exception as e:
        logger.error(f"Namespace verification failed: {str(e)}")

def check_data_structure():
    """Check if data directories exist"""
    print("\n📁 Checking data directory structure...")
    print("=" * 50)
    
    for i in range(1, 5):
        module_dir = os.path.join(Config.DATA_DIR, f"module{i}")
        if os.path.exists(module_dir):
            files = [f for f in os.listdir(module_dir) 
                    if f.lower().endswith(('.pdf', '.pptx', '.docx'))]
            print(f"📂 module{i}: {len(files)} document(s)")
            for file in files[:3]:  # Show first 3 files
                print(f"   - {file}")
            if len(files) > 3:
                print(f"   ... and {len(files) - 3} more")
        else:
            print(f"❌ module{i}: Directory not found")
            print(f"   Create: mkdir -p {module_dir}")
            print(f"   Add PDF/PPTX/DOCX files to {module_dir}/")

def upload_to_correct_namespace():
    """Upload documents to correct namespaces based on file location"""
    print("\n📤 Uploading documents to correct namespaces...")
    print("=" * 50)
    
    from llm.openai_client import get_embedding
    import hashlib
    
    pc_index = pinecone_setup.initialize_pinecone()
    
    total_uploaded = 0
    skipped_files = 0
    
    # Process each module directory
    for root, _, files in os.walk(Config.DATA_DIR):
        for file in files:
            if file.lower().endswith(('.pdf', '.pptx', '.docx')):
                file_path = os.path.join(root, file)
                
                # Get module number from path
                module = get_module_from_path(file_path)
                namespace = f"module{module}"
                
                print(f"📄 Processing: {file} → {namespace}")
                
                try:
                    # Process the file
                    from database.document_loader import process_file, chunk_text
                    text, rel_path, metadata = process_file(file_path)
                    
                    if not text.strip():
                        print(f"   ⚠️  Empty content, skipping")
                        skipped_files += 1
                        continue
                    
                    # Create chunks
                    chunks = chunk_text(
                        text, 
                        rel_path,
                        chunk_size=Config.CHUNK_SIZE,
                        chunk_overlap=Config.CHUNK_OVERLAP
                    )
                    
                    # Create vectors
                    vectors = []
                    for i, chunk_data in enumerate(chunks):
                        chunk_text = chunk_data["text"]
                        metadata = chunk_data.get("metadata", {})
                        
                        clean_metadata = {
                            "file_type": os.path.splitext(file)[1],
                            "original_file": os.path.basename(file_path),
                            "module": module,
                            "source": rel_path,
                            "page": metadata.get("page", 1),
                            "slide": metadata.get("slide", 1),
                            "section": metadata.get("section", 1)
                        }
                        
                        embedding = get_embedding(chunk_text)
                        unique_id = hashlib.md5(f"{rel_path}_{i}".encode()).hexdigest()
                        
                        vectors.append({
                            "id": unique_id,
                            "values": embedding,
                            "metadata": clean_metadata
                        })
                    
                    # Upload to namespace
                    if vectors:
                        success = pinecone_setup.upsert_documents(pc_index, vectors, namespace)
                        if success:
                            total_uploaded += len(vectors)
                            print(f"   ✅ Uploaded {len(vectors)} chunks to {namespace}")
                        else:
                            print(f"   ❌ Failed to upload to {namespace}")
                    else:
                        print(f"   ⚠️  No vectors created")
                        skipped_files += 1
                        
                except Exception as e:
                    print(f"   ❌ Error: {str(e)}")
                    skipped_files += 1
    
    print(f"\n📊 Upload Summary:")
    print(f"   Total chunks uploaded: {total_uploaded}")
    print(f"   Files skipped: {skipped_files}")

def main():
    print("🚀 Personalized Learning System - Namespace Setup")
    print("=" * 60)
    
    # 1. Check data structure
    check_data_structure()
    
    # 2. Verify namespaces
    verify_namespaces()
    
    # 3. Ask if user wants to upload
    response = input("\nDo you want to upload documents to Pinecone? (yes/no): ")
    if response.lower() in ['yes', 'y']:
        upload_to_correct_namespace()
        print("\n✅ Upload complete!")
        print("\n📋 Next steps:")
        print("1. Run: python app.py")
        print("2. Ask questions like: 'What are data types?'")
        print("3. Test quiz system")
    else:
        print("\n⏭️  Skipping upload. You can upload later with: python manual_upload.py")

if __name__ == "__main__":
    main()