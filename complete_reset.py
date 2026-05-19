#!/usr/bin/env python3
"""
Complete reset script for Personalized Learning System
"""
import os
import sys
from pinecone import Pinecone
from config import Config
import time

print("🔧 Personalized Learning System - Complete Reset")
print("=" * 50)

# Step 1: Delete Pinecone index
print("\n1. Deleting Pinecone index...")
try:
    pc = Pinecone(api_key=Config.PINECONE_API_KEY)
    index_name = Config.PINECONE_INDEX.lower()
    
    if index_name in pc.list_indexes().names():
        pc.delete_index(index_name)
        print(f"✅ Deleted index: {index_name}")
        # Wait for deletion to complete
        time.sleep(10)
    else:
        print(f"ℹ️ Index '{index_name}' not found.")
except Exception as e:
    print(f"❌ Error deleting index: {e}")

# Step 2: Create fresh index
print("\n2. Creating new index with correct dimension...")
try:
    pc.create_index(
        name=index_name,
        dimension=Config.PINECONE_DIMENSION,
        metric="cosine",
        spec=ServerlessSpec(cloud='aws', region='us-east-1')
    )
    print(f"✅ Created index: {index_name} (dimension: {Config.PINECONE_DIMENSION})")
    print("⏳ Waiting 30 seconds for index to be ready...")
    time.sleep(30)
except Exception as e:
    print(f"❌ Error creating index: {e}")

# Step 3: Upload documents
print("\n3. Uploading documents...")
try:
    from manual_upload import upload_documents
    success = upload_documents()
    if success:
        print("✅ Documents uploaded successfully!")
    else:
        print("❌ Document upload failed.")
except Exception as e:
    print(f"❌ Error uploading documents: {e}")

# Step 4: Test the system
print("\n4. Testing system...")
try:
    from terminal_app import handle_query
    test_query = "What are data types?"
    print(f"Testing query: '{test_query}'")
    response = handle_query(test_query)
    
    if response["status"] == "success":
        print(f"✅ System working! Found topic: {response['topic']}")
    else:
        print(f"⚠️ System response: {response['message']}")
except Exception as e:
    print(f"❌ Test failed: {e}")

print("\n" + "=" * 50)
print("Reset complete! Run: python app.py")