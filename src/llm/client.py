import os

_model = None
_tokenizer = None
_load_attempted = False


def _load_model():
    global _model, _tokenizer, _load_attempted
    if _load_attempted:
        return
    _load_attempted = True

    try:
        from transformers import T5ForConditionalGeneration, T5Tokenizer
        model_name = os.environ.get("ECOSENSE_LLM", "google/flan-t5-base")
        _tokenizer = T5Tokenizer.from_pretrained(model_name, legacy=True)
        _model = T5ForConditionalGeneration.from_pretrained(model_name)
        print(f"LLM loaded: {model_name}")
    except Exception as e:
        print(f"LLM load failed: {e}")
        _model = None
        _tokenizer = None


def generate(prompt: str, max_length: int = 128) -> str:
    _load_model()
    if _model is None or _tokenizer is None:
        return ""

    try:
        inputs = _tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
        outputs = _model.generate(
            **inputs,
            max_length=max_length,
            num_beams=3,
            early_stopping=True,
            no_repeat_ngram_size=2,
        )
        return _tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
    except Exception as e:
        print(f"LLM generation error: {e}")
        return ""