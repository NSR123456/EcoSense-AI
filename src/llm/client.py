"""
LLM Client for Energy Domain
Supports Ollama model selection and optional Hugging Face fallback.
"""

import os

try:
    import torch
except ImportError:
    torch = None

try:
    from transformers import pipeline
except ImportError:
    pipeline = None

from dotenv import load_dotenv

load_dotenv()

# Global model instances and selection state
_text_generator = None
_fine_tuned_available = False
_CURRENT_LLM_MODEL = None
_CURRENT_LLM_BACKEND = None

SUPPORTED_BASE_MODELS = [
    "distilgpt2",
    "microsoft/DialoGPT-small",
    "gpt2",
]
MODEL_CHOICES = [
    "llama3.2:1b",
    "qwen-7b",
    "mistral-7b",
    "distilgpt2",
    "microsoft/DialoGPT-small",
    "gpt2",
]
OLLAMA_MODELS = {"llama3.2:1b", "qwen-7b", "mistral-7b"}
DEFAULT_MODEL = os.getenv("LLM_MODEL", "llama3.2:1b")
DEFAULT_BACKEND = os.getenv("LLM_BACKEND", "ollama")


def _get_active_model():
    global _CURRENT_LLM_MODEL
    return _CURRENT_LLM_MODEL or os.getenv("LLM_MODEL") or DEFAULT_MODEL


def _get_active_backend(model_name: str | None = None):
    global _CURRENT_LLM_BACKEND
    if _CURRENT_LLM_BACKEND:
        return _CURRENT_LLM_BACKEND
    backend = os.getenv("LLM_BACKEND") or DEFAULT_BACKEND
    model_name = model_name or _get_active_model()
    if backend == "auto":
        if model_name in OLLAMA_MODELS or ":" in model_name:
            return "ollama"
        return "huggingface"
    if backend not in {"ollama", "huggingface"}:
        return "ollama"
    return backend


def set_active_model(model_name: str, backend: str | None = None):
    global _CURRENT_LLM_MODEL, _CURRENT_LLM_BACKEND, _text_generator, _fine_tuned_available
    _CURRENT_LLM_MODEL = model_name
    _CURRENT_LLM_BACKEND = backend or _get_active_backend(model_name)
    _text_generator = None
    _fine_tuned_available = False


def get_active_model() -> dict:
    model_name = _get_active_model()
    return {
        "model": model_name,
        "backend": _get_active_backend(model_name),
    }


def get_text_generator(model_name: str | None = None):
    """Get or create text generation pipeline"""
    global _text_generator, _fine_tuned_available

    if _text_generator is not None:
        return _text_generator

    model_name = model_name or _get_active_model()
    backend = _get_active_backend(model_name)

    if pipeline is None:
        print("Transformers library not installed; cannot create a HuggingFace pipeline.")
        return None

    if backend == "huggingface":
        fine_tuner = None
        try:
            from .energy_fine_tuner import get_energy_fine_tuner
            fine_tuner = get_energy_fine_tuner()
        except Exception:
            fine_tuner = None

        if fine_tuner is not None and fine_tuner.load_fine_tuned_model():
            print("Using fine-tuned energy model for generation")
            _fine_tuned_available = True
            device = 0 if torch is not None and torch.cuda.is_available() else -1
            _text_generator = pipeline(
                "text-generation",
                model=fine_tuner.model,
                tokenizer=fine_tuner.tokenizer,
                device=device,
                max_new_tokens=150,
                temperature=0.4,
                do_sample=True,
                top_p=0.9,
                repetition_penalty=1.2,
                pad_token_id=fine_tuner.tokenizer.eos_token_id,
            )
            return _text_generator

        print("Fine-tuned model not available, using base model")
        model_name = os.getenv("HUGGINGFACE_BASE_MODEL") or model_name or SUPPORTED_BASE_MODELS[0]
    else:
        model_name = model_name or DEFAULT_MODEL

    try:
        device = 0 if torch is not None and torch.cuda.is_available() else -1
        _text_generator = pipeline(
            "text-generation",
            model=model_name,
            device=device,
            max_new_tokens=150,
            temperature=0.4,
            do_sample=True,
            top_p=0.9,
            repetition_penalty=1.2,
        )
        print(f"Loaded model: {model_name} ({backend})")
        return _text_generator
    except Exception as e:
        print(f"Failed to load model {model_name}: {e}")
        return None


def generate(prompt: str, max_length: int = 150) -> str:
    """Generate text using the selected LLM model and provider."""
    model_name = _get_active_model()
    backend = _get_active_backend(model_name)

    if backend == "ollama":
        try:
            import ollama
            response = ollama.generate(
                model=model_name,
                prompt=prompt,
                options={
                    "temperature": 0.3,
                    "num_predict": max_length,
                },
            )
            return response["response"].strip()
        except Exception as e:
            print(f"Ollama connection error for {model_name}: {e}")

    try:
        generator = get_text_generator(model_name if backend == "huggingface" else None)
        if generator is not None:
            outputs = generator(
                prompt,
                max_new_tokens=max_length,
                temperature=0.4,
                do_sample=True,
                top_p=0.9,
                repetition_penalty=1.2,
            )
            return outputs[0]["generated_text"].strip()
    except Exception as e:
        print(f"Text generation fallback failed: {e}")

    clean_prompt = prompt
    if "Operator question:" in prompt:
        parts = prompt.split("Operator question:")
        if len(parts) > 1:
            clean_prompt = parts[1].split("Answer:")[0].strip()

    try:
        from src.llm.energy_fine_tuner import generate_fine_tuned_response
        return generate_fine_tuned_response("synthesizer", clean_prompt)
    except Exception as e:
        print(f"Fallback response generation not available: {e}")
        return clean_prompt


def generate_with_gemini(prompt: str, safety_delay: int = 0) -> str:
    """Backward compatibility - now uses local HuggingFace model"""
    return generate(prompt, max_length=150)


def is_fine_tuned_model_available() -> bool:
    """Check if fine-tuned energy model is available"""
    return _fine_tuned_available


def get_model_info() -> dict:
    """Get information about the currently loaded model"""
    generator = get_text_generator()
    if generator is None:
        return {"status": "no_model", "message": "No model available"}

    info = {
        "status": "fine_tuned" if _fine_tuned_available else "base_model",
        "backend": _get_active_backend(),
        "model": _get_active_model(),
        "device": "cuda" if torch is not None and torch.cuda.is_available() else "cpu",
        "model_type": "energy_fine_tuned" if _fine_tuned_available else "base_huggingface",
    }

    if hasattr(generator, "model") and hasattr(generator.model, "name_or_path"):
        info["loaded_model_name"] = generator.model.name_or_path

    return info
