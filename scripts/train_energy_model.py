#!/usr/bin/env python3
"""
Energy Model Training Script
Fine-tunes HuggingFace models on energy domain data
"""

import os
import sys
import argparse
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from llm.energy_fine_tuner import fine_tune_energy_model, get_energy_fine_tuner
from llm.client import get_model_info

def main():
    parser = argparse.ArgumentParser(description="Fine-tune LLM on energy domain data")
    parser.add_argument("--epochs", type=int, default=3, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=4, help="Training batch size")
    parser.add_argument("--base-model", type=str, default="distilgpt2",
                       choices=["distilgpt2", "gpt2", "microsoft/DialoGPT-small"],
                       help="Base model to fine-tune")
    parser.add_argument("--evaluate", action="store_true", help="Evaluate model after training")

    args = parser.parse_args()

    print("🚀 Starting Energy Model Fine-Tuning")
    print(f"Base Model: {args.base_model}")
    print(f"Epochs: {args.epochs}")
    print(f"Batch Size: {args.batch_size}")
    print("-" * 50)

    try:
        # Fine-tune the model
        print("📚 Fine-tuning model on energy domain conversations...")
        model_path = fine_tune_energy_model(
            epochs=args.epochs,
            batch_size=args.batch_size
        )

        print(f"✅ Fine-tuning completed! Model saved to: {model_path}")

        # Evaluate if requested
        if args.evaluate:
            print("\n📊 Evaluating model quality...")
            tuner = get_energy_fine_tuner()
            evaluation = tuner.evaluate_model_quality()

            print("Evaluation Results:")
            for role, metrics in evaluation.items():
                print(f"  {role.title()}:")
                print(f"    Response Length: {metrics['response_length']}")
                print(f"    Contains Energy Terms: {metrics['contains_energy_terms']}")
                print(f"    Sample Response: {metrics['response']}")
                print()

        # Show model info
        print("🔍 Model Information:")
        model_info = get_model_info()
        for key, value in model_info.items():
            print(f"  {key}: {value}")

        print("\n🎉 Training completed successfully!")
        print("You can now use the fine-tuned model in your energy workflows.")

    except Exception as e:
        print(f"❌ Training failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()