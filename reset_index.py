from pinecone import Pinecone
from config import Config
import os

pc = Pinecone(api_key=Config.PINECONE_API_KEY)
index_name = Config.PINECONE_INDEX.lower()

if index_name in pc.list_indexes().names():
    print(f"Deleting index: {index_name}")
    pc.delete_index(index_name)
    print("✅ Index deleted successfully!")
else:
    print(f"Index '{index_name}' not found. Nothing to delete.")