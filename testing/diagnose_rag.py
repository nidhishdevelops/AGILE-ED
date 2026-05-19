"""
Diagnose Pinecone index and retrieval performance.
Run this to see what's actually in the index.
"""
from database import pinecone_setup
from llm.openai_client import get_embedding
from config import Config
import numpy as np

def diagnose():
    print("=" * 60)
    print("RAG DIAGNOSTIC TOOL")
    print("=" * 60)
    
    # 1. Index stats
    pc_index = pinecone_setup.initialize_pinecone()
    stats = pc_index.describe_index_stats()
    print(f"\n📊 Index Stats:")
    print(f"   Dimension: {stats.get('dimension')}")
    print(f"   Total vectors: {stats.get('total_vector_count')}")
    print(f"   Namespaces: {list(stats.get('namespaces', {}).keys())}")
    for ns, ns_stats in stats.get('namespaces', {}).items():
        print(f"      {ns}: {ns_stats.get('vector_count')} vectors")
    
    if stats.get('total_vector_count', 0) == 0:
        print("\n⚠️  No vectors found! Run python manual_upload.py first.")
        return
    
    # 2. Test a query
    test_query = "feature engineering"
    print(f"\n🔍 Testing query: '{test_query}'")
    embedding = get_embedding(test_query)
    print(f"   Embedding dimension: {len(embedding)} (expected: {Config.PINECONE_DIMENSION})")
    
    namespaces = ["module1", "module2", "module3", "module4"]
    for ns in namespaces:
        try:
            results = pc_index.query(
                vector=embedding,
                top_k=3,
                include_metadata=True,
                namespace=ns
            )
            matches = results.get('matches', [])
            if matches:
                print(f"\n   Namespace {ns}: {len(matches)} matches")
                for m in matches[:2]:
                    print(f"      Score: {m['score']:.4f} | Source: {m['metadata'].get('original_file', 'unknown')}")
            else:
                print(f"   Namespace {ns}: no matches")
        except Exception as e:
            print(f"   Error in {ns}: {e}")
    
    # 3. Check threshold
    print(f"\n📏 Current CONTENT_THRESHOLD = {Config.CONTENT_THRESHOLD}")
    print("   (Scores below this are filtered out)")

if __name__ == "__main__":
    diagnose()