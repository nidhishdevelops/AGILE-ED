# test_simple.py
import os
os.environ['GEMINI_MODEL'] = 'gemini-2.5-pro'

# Test just OpenAI
print("🧪 Testing OpenAI-only system...")

from terminal_app import handle_query, print_response

response = handle_query("What are data types?")
print_response(response)

print("\n✅ Test complete!")
print("If this works, your system is ready!")