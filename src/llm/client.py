import os
import time
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()

_llm = None
_llm_model = None

SUPPORTED_GOOGLE_MODELS = [
    "gemini-1.5",
    "gemini-1.5-pro",
    "gemini-1.0",
    "gemini-1.0-pro"
]


def get_llm(model_name: str | None = None):
    global _llm, _llm_model
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("GOOGLE_API_KEY not found in environment.")
        return None

    selected_model = model_name or os.getenv("GOOGLE_GEMINI_MODEL") or SUPPORTED_GOOGLE_MODELS[0]
    if _llm is not None and _llm_model == selected_model:
        return _llm

    try:
        _llm = ChatGoogleGenerativeAI(
            model=selected_model,
            google_api_key=api_key,
            temperature=0.2,
            max_output_tokens=1024
        )
        _llm_model = selected_model
        print(f"Gemini client initialized with model: {selected_model}")
        return _llm
    except Exception as e:
        print(f"Gemini Client initialization failed for model {selected_model}: {e}")
        return None


def generate(prompt: str, max_length: int = 128) -> str:
    """Backward compatibility alias for generate_with_gemini."""
    return generate_with_gemini(prompt, safety_delay=0)


def generate_with_gemini(prompt: str, safety_delay: int = 4) -> str:
    """Generate content using Gemini with model fallback."""
    model_choices = []
    env_model = os.getenv("GOOGLE_GEMINI_MODEL")
    if env_model:
        model_choices.append(env_model)
    model_choices.extend(SUPPORTED_GOOGLE_MODELS)

    seen = []
    for model_name in model_choices:
        if not model_name or model_name in seen:
            continue
        seen.append(model_name)

        llm = get_llm(model_name)
        if llm is None:
            continue

        try:
            print(f"Gemini Client: Invoking model {model_name} (delay={safety_delay}s)...")
            time.sleep(safety_delay)
            response = llm.invoke(prompt)
            content = response.content.strip()
            if not content:
                print("Gemini Client WARNING: Received empty content from model.")
            return content
        except Exception as e:
            err_text = str(e).lower()
            print(f"Gemini Client EXCEPTION for {model_name}: {e}")
            if "not found" in err_text or "unsupported" in err_text or "404" in err_text:
                print(f"Gemini Client: model {model_name} not available, trying next supported model.")
                continue
            return ""

    print("Gemini Client Error: No supported Gemini model was available.")
    return ""
