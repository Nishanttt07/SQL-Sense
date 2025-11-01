import requests
import sys

def test_gemini_api(api_key):
    """Test if Gemini API key works"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            models = response.json()
            print("✅ API Key is valid!")
            print("Available models:")
            for model in models.get('models', []):
                print(f"  - {model['name']}")
            return True
        else:
            print(f"❌ API Key error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

if __name__ == "__main__":
    from config import GEMINI_API_KEY
    test_gemini_api(GEMINI_API_KEY)