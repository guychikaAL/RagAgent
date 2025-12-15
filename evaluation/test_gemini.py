"""
Test Gemini API Connection and List Available Models

This script verifies:
1. GOOGLE_API_KEY is loaded from .env
2. Gemini API is accessible
3. Lists available models
4. Tests a simple query
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai

# Load .env from project root
project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env")

print("="*70)
print("🧪 TESTING GEMINI API")
print("="*70)

# Step 1: Check API key
print("\n[1/4] Checking API key...")
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("❌ GOOGLE_API_KEY not found!")
    print("\n💡 Add to .env file:")
    print("   GOOGLE_API_KEY=your_key_here")
    print("\nGet key from: https://aistudio.google.com/app/apikey")
    exit(1)

print(f"✅ API key found: {api_key[:10]}...{api_key[-5:]}")

# Step 2: Configure Gemini
print("\n[2/4] Configuring Gemini...")
try:
    genai.configure(api_key=api_key)
    print("✅ Gemini configured")
except Exception as e:
    print(f"❌ Error configuring Gemini: {e}")
    exit(1)

# Step 3: List available models
print("\n[3/4] Listing available models...")
try:
    models = genai.list_models()
    
    print("\n📋 Available Gemini models:")
    gemini_models = []
    for model in models:
        if "generateContent" in model.supported_generation_methods:
            model_name = model.name.replace("models/", "")
            gemini_models.append(model_name)
            print(f"  ✅ {model_name}")
    
    if not gemini_models:
        print("  ⚠️ No models support generateContent")
    
except Exception as e:
    print(f"❌ Error listing models: {e}")
    exit(1)

# Step 4: Test a simple query
print("\n[4/4] Testing simple query...")

# Try each available model
for model_name in gemini_models[:3]:  # Test first 3 models
    print(f"\n  Testing {model_name}...")
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Say 'Hello World'")
        print(f"  ✅ Response: {response.text}")
        print(f"\n🎉 SUCCESS! Use this model: {model_name}")
        break
    except Exception as e:
        print(f"  ❌ Failed: {e}")

print("\n" + "="*70)
print("✅ GEMINI TEST COMPLETE")
print("="*70)

