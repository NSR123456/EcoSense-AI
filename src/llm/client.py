import os
import time
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()

_llm = None

def get_llm():
    global _llm
    if _llm is None:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print("GOOGLE_API_KEY not found in environment.")
            return None
        
        _llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=api_key,
            temperature=0.2,
            max_output_tokens=1024
        )
        print("Gemini 1.5 Flash client initialized.")
    return _llm

def generate(prompt: str, max_length: int = 128) -> str:
    """Backward compatibility alias for generate_with_gemini."""
    return generate_with_gemini(prompt, safety_delay=0) # No delay for UI-triggered calls to keep it snappy

def generate_with_gemini(prompt: str, safety_delay: int = 4) -> str:
    """Generate content using Gemini 1.5 Flash with safety delay."""
    llm = get_llm()
    if llm is None:
        print("Gemini Client Error: LLM not initialized.")
        return ""
    
    try:
        # Respect RPM limits (15 RPM -> ~4 seconds delay)
        print(f"Gemini Client: Invoking model (delay={safety_delay}s)...")
        time.sleep(safety_delay)
        response = llm.invoke(prompt)
        content = response.content.strip()
        if not content:
            print("Gemini Client WARNING: Received empty content from model.")
        return content
    except Exception as e:
        print(f"Gemini Client EXCEPTION: {e}")
        return ""
