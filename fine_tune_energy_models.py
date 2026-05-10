#!/usr/bin/env python3
"""
Energy Model Fine-Tuning Script
Fine-tunes language models on energy domain conversations for academic novelty
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.llm.energy_fine_tuner import fine_tune_energy_model, get_energy_fine_tuner
from src.llm.energy_fine_tuner import generate_fine_tuned_response

def main():
    """Main fine-tuning workflow"""
    
    print("=== Energy Domain Model Fine-Tuning ===")
    print("This creates domain-specific models for academic novelty\n")
    
    # Step 1: Fine-tune the model
    print("1. Fine-tuning model on energy domain conversations...")
    try:
        model_path = fine_tune_energy_model(epochs=2, batch_size=2)  # Reduced for demo
        print(f"   Fine-tuned model saved to: {model_path}")
    except Exception as e:
        print(f"   Fine-tuning failed: {e}")
        return
    
    # Step 2: Test the fine-tuned model
    print("\n2. Testing fine-tuned model responses...")
    tuner = get_energy_fine_tuner()
    
    test_cases = [
        ("analyst", "Energy consumption spike detected"),
        ("planner", "Energy waste identified"),
        ("recommender", "How to reduce energy consumption"),
        ("critic", "Proposed energy solution"),
        ("synthesizer", "Multiple energy recommendations")
    ]
    
    for role, prompt in test_cases:
        try:
            response = generate_fine_tuned_response(role, prompt)
            print(f"   {role.title()}: {response[:100]}...")
        except Exception as e:
            print(f"   {role.title()}: Error - {e}")
    
    # Step 3: Evaluate model quality
    print("\n3. Evaluating model quality...")
    try:
        quality_results = tuner.evaluate_model_quality()
        for role, metrics in quality_results.items():
            if "error" not in metrics:
                print(f"   {role.title()}: Length={metrics['response_length']}, Energy terms={metrics['contains_energy_terms']}")
    except Exception as e:
        print(f"   Quality evaluation failed: {e}")
    
    print("\n=== Fine-Tuning Complete ===")
    print("Academic contributions:")
    print("  - Domain-specific language model fine-tuning")
    print("  - Energy conversation dataset creation")
    print("  - Multi-agent role-based training")
    print("  - Hybrid ML + fine-tuned LLM system")

if __name__ == "__main__":
    main()
