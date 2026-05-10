import torch
from src.llm.energy_fine_tuner import get_energy_fine_tuner

tuner = get_energy_fine_tuner()
tuner.load_fine_tuned_model()
inputs = tuner.tokenizer.encode('<synthesizer> summarize last week energy pattern </synthesizer>', return_tensors='pt')
with torch.no_grad():
    outputs = tuner.model.generate(inputs, max_length=100)

print('RAW DECODED:', repr(tuner.tokenizer.decode(outputs[0], skip_special_tokens=False)))
print('CLEANED:', repr(tuner.tokenizer.decode(outputs[0], skip_special_tokens=True)))
