"""
Ollama-based LLM Client for Energy Domain
Uses local Ollama models for reasoning and summarization
"""

import os
import torch
from transformers import pipeline
from .energy_fine_tuner import get_energy_fine_tuner
from dotenv import load_dotenv

load_dotenv()

# Global model instances
_text_generator = None
_fine_tuned_available = False

# Supported base models (fallback if fine-tuned model not available)
SUPPORTED_BASE_MODELS = [
    "distilgpt2",  # Fast, lightweight
    "microsoft/DialoGPT-small",  # Conversational
    "gpt2",  # Standard GPT-2
]


def get_text_generator():
    """Get or create text generation pipeline"""
    global _text_generator, _fine_tuned_available

    if _text_generator is not None:
        return _text_generator

    # Try to load fine-tuned energy model first
    fine_tuner = get_energy_fine_tuner()
    if fine_tuner.load_fine_tuned_model():
        print("Using fine-tuned energy model for generation")
        _fine_tuned_available = True

        # Create pipeline with fine-tuned model
        _text_generator = pipeline(
            "text-generation",
            model=fine_tuner.model,
            tokenizer=fine_tuner.tokenizer,
            device=0 if torch.cuda.is_available() else -1,
            max_new_tokens=150,
            temperature=0.4,
            do_sample=True,
            top_p=0.9,
            repetition_penalty=1.2,
            pad_token_id=fine_tuner.tokenizer.eos_token_id
        )
        return _text_generator

    # Fallback to base model
    print("Fine-tuned model not available, using base model")
    model_name = os.getenv("HUGGINGFACE_BASE_MODEL") or SUPPORTED_BASE_MODELS[0]

    try:
        _text_generator = pipeline(
            "text-generation",
            model=model_name,
            device=0 if torch.cuda.is_available() else -1,
            max_new_tokens=150,
            temperature=0.4,
            do_sample=True,
            top_p=0.9,
            repetition_penalty=1.2
        )
        print(f"Loaded base model: {model_name}")
        return _text_generator
    except Exception as e:
        print(f"Failed to load model {model_name}: {e}")
        return None


def generate(prompt: str, max_length: int = 150) -> str:
    """Generate text using local Ollama instance (Llama 3.2 1B)"""
    import ollama
            
    # For reasoning queries, we just pass the full prompt directly to Llama 3.2
    # It has a 128k context window and can handle system instructions perfectly
    try:
        response = ollama.generate(
            model='llama3.2:1b',
            prompt=prompt,
            options={
                'temperature': 0.3,
                'num_predict': max_length
            }
        )
        return response['response'].strip()
    except Exception as e:
        print(f"Ollama connection error: {e}")
        
        # Fallback to the hardcoded responses if Ollama isn't running yet
        # Extract just the user's question for the tiny local model
        clean_prompt = prompt
        if "Operator question:" in prompt:
            parts = prompt.split("Operator question:")
            if len(parts) > 1:
                clean_prompt = parts[1].split("Answer:")[0].strip()
                
        from src.llm.energy_fine_tuner import generate_fine_tuned_response
        return generate_fine_tuned_response("synthesizer", clean_prompt)


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
        "device": "cuda" if torch.cuda.is_available() else "cpu",
        "model_type": "energy_fine_tuned" if _fine_tuned_available else "base_huggingface"
    }

    if hasattr(generator, 'model') and hasattr(generator.model, 'name_or_path'):
        info["model_name"] = generator.model.name_or_path

    return info
