"""
Energy Domain Fine-Tuning System
Fine-tunes Hugging Face models on energy-specific conversations
"""

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, Trainer, TrainingArguments
import json
import pandas as pd
import os
from typing import List, Dict, Any
import random

class EnergyDomainFineTuner:
    """Fine-tunes language models on energy domain conversations"""
    
    def __init__(self, base_model: str = "distilgpt2"):
        self.base_model = base_model
        self.tokenizer = None
        self.model = None
        self.fine_tuned_model_path = "src/models/energy_finetuned"
        
        # Energy domain training data
        self.training_conversations = self._generate_energy_training_data()
    
    def _generate_energy_training_data(self) -> List[Dict]:
        """Generate energy-specific training conversations"""
        
        # Energy conversation templates for each agent role
        agent_templates = {
            "analyst": [
                {"input": "Energy consumption spike detected", "output": "Analyzing consumption patterns reveals HVAC system inefficiency"},
                {"input": "Building using excessive power", "output": "Data shows 25% increase from baseline, requires investigation"},
                {"input": "Unusual energy pattern observed", "output": "Statistical analysis indicates equipment left on after hours"},
                {"input": "High electricity usage detected", "output": "Consumption metrics suggest phantom load from standby devices"},
                {"input": "Energy anomaly in building system", "output": "Time series analysis reveals schedule drift in operations"}
            ],
            "planner": [
                {"input": "Energy waste identified", "output": "Review operational schedule to optimize equipment runtime"},
                {"input": "Building efficiency low", "output": "Strategic planning needed for energy management protocols"},
                {"input": "Excessive consumption patterns", "output": "Coordinate with facilities to adjust building automation settings"},
                {"input": "Energy usage optimization required", "output": "Develop comprehensive energy conservation strategy"},
                {"input": "System performance issues", "output": "Plan systematic approach to identify root causes"}
            ],
            "recommender": [
                {"input": "How to reduce energy consumption", "output": "Install smart thermostats and optimize HVAC setpoints"},
                {"input": "Energy saving measures needed", "output": "Implement LED lighting retrofits and motion sensor controls"},
                {"input": "Building energy efficiency", "output": "Conduct energy audit and seal building envelope leaks"},
                {"input": "Power consumption reduction", "output": "Upgrade to energy-efficient equipment and power management systems"},
                {"input": "Sustainable energy practices", "output": "Adopt renewable energy sources and energy storage solutions"}
            ],
            "critic": [
                {"input": "Proposed energy solution", "output": "Evaluate implementation costs versus projected savings"},
                {"input": "Energy efficiency recommendations", "output": "Consider maintenance requirements and operational impacts"},
                {"input": "Building upgrade proposal", "output": "Assess ROI and payback period for energy investments"},
                {"input": "Energy conservation measures", "output": "Review potential disruptions to building operations"},
                {"input": "System modification suggestions", "output": "Analyze compatibility with existing infrastructure"}
            ],
            "synthesizer": [
                {"input": "Multiple energy recommendations", "output": "Integrate solutions into comprehensive energy management plan"},
                {"input": "Conflicting energy strategies", "output": "Balance cost-effectiveness with operational requirements"},
                {"input": "Various energy insights", "output": "Synthesize findings into actionable implementation roadmap"},
                {"input": "Diverse energy perspectives", "output": "Create unified approach addressing all stakeholder concerns"},
                {"input": "Complex energy analysis results", "output": "Develop prioritized action plan with clear timelines"}
            ]
        }
        
        # Generate training dataset
        training_data = []
        
        for agent_role, conversations in agent_templates.items():
            for conv in conversations:
                # Format for fine-tuning
                formatted_text = f"<{agent_role}> {conv['input']} </{agent_role}> {conv['output']}"
                training_data.append({
                    "text": formatted_text,
                    "role": agent_role,
                    "input": conv["input"],
                    "output": conv["output"]
                })
        
        # Add multi-agent conversations
        multi_agent_conversations = [
            {
                "text": "<analyst> Energy consumption spike detected in Building_A </analyst> Data shows HVAC system running at 150% capacity during off-hours <planner> Review operational schedule to optimize equipment runtime </planner> <recommender> Install smart thermostats and optimize HVAC setpoints </recommender> <critic> Evaluate implementation costs versus projected savings </critic> <synthesizer> Create prioritized action plan with clear timelines </synthesizer>",
                "type": "multi_agent"
            },
            {
                "text": "<analyst> Building using excessive power, 25% increase from baseline </analyst> Statistical analysis indicates equipment left on after hours <planner> Coordinate with facilities to adjust building automation settings </planner> <recommender> Implement LED lighting retrofits and motion sensor controls </recommender> <critic> Consider maintenance requirements and operational impacts </critic> <synthesizer> Develop comprehensive energy management plan </synthesizer>",
                "type": "multi_agent"
            }
        ]
        
        training_data.extend(multi_agent_conversations)
        
        return training_data
    
    def prepare_dataset(self):
        """Prepare dataset for fine-tuning using simple list"""
        
        # Tokenize all texts
        tokenized_data = []
        
        for item in self.training_conversations:
            # Add special tokens for different agent roles
            text = item["text"]
            
            # Tokenize
            encoded = self.tokenizer(
                text,
                truncation=True,
                padding="max_length",
                max_length=256,
                return_tensors="pt"
            )
            
            tokenized_data.append({
                "input_ids": encoded["input_ids"].squeeze(),
                "attention_mask": encoded["attention_mask"].squeeze(),
                "labels": encoded["input_ids"].squeeze()  # For language modeling
            })
        
        return tokenized_data
    
    def fine_tune_model(self, epochs: int = 3, batch_size: int = 4):
        """Fine-tune the model on energy domain data"""
        
        print(f"Loading base model: {self.base_model}")
        
        # Load tokenizer and model
        self.tokenizer = AutoTokenizer.from_pretrained(self.base_model)
        self.model = AutoModelForCausalLM.from_pretrained(self.base_model)
        
        # Set padding token
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        
        # Add special tokens for agent roles
        special_tokens = ["<analyst>", "</analyst>", "<planner>", "</planner>", 
                         "<recommender>", "</recommender>", "<critic>", "</critic>", 
                         "<synthesizer>", "</synthesizer>"]
        
        self.tokenizer.add_special_tokens({"additional_special_tokens": special_tokens})
        self.model.resize_token_embeddings(len(self.tokenizer))
        
        # Prepare dataset
        dataset = self.prepare_dataset()
        
        # Create custom dataset class
        class EnergyDataset(torch.utils.data.Dataset):
            def __init__(self, data):
                self.data = data
            
            def __len__(self):
                return len(self.data)
            
            def __getitem__(self, idx):
                return self.data[idx]
        
        custom_dataset = EnergyDataset(dataset)
        
        # Training arguments
        training_args = TrainingArguments(
            output_dir=self.fine_tuned_model_path,
            num_train_epochs=epochs,
            per_device_train_batch_size=batch_size,
            warmup_steps=50,
            weight_decay=0.01,
            logging_dir="./logs",
            logging_steps=5,
            save_steps=100,
            save_total_limit=2,
            load_best_model_at_end=False,
        )
        
        # Create trainer
        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=custom_dataset,
        )
        
        print("Starting fine-tuning...")
        trainer.train()
        
        # Save fine-tuned model
        trainer.save_model(self.fine_tuned_model_path)
        self.tokenizer.save_pretrained(self.fine_tuned_model_path)
        
        print(f"Fine-tuned model saved to {self.fine_tuned_model_path}")
        
        return self.fine_tuned_model_path
    
    def load_fine_tuned_model(self):
        """Load the fine-tuned model for inference"""
        
        if os.path.exists(self.fine_tuned_model_path):
            print("Loading fine-tuned energy model...")
            self.tokenizer = AutoTokenizer.from_pretrained(self.fine_tuned_model_path)
            self.model = AutoModelForCausalLM.from_pretrained(self.fine_tuned_model_path)
            return True
        else:
            print("Fine-tuned model not found. Please run fine_tune_model() first.")
            return False
    
    def generate_energy_response(self, agent_role: str, input_text: str, max_length: int = 100) -> str:
        """Generate response using fine-tuned model with diversity"""
        
        if not self.model or not self.tokenizer:
            if not self.load_fine_tuned_model():
                return "Model not available"
        
        # Format input with agent role tags
        formatted_input = f"<{agent_role}> {input_text} </{agent_role}>"
        
        # Add diversity based on input length and content
        temperature = 0.8 if len(input_text) < 20 else 0.7
        top_p = 0.9 if agent_role == "recommender" else 0.8
        
        # Generate response with diversity parameters
        inputs = self.tokenizer.encode(formatted_input, return_tensors="pt")
        
        with torch.no_grad():
            outputs = self.model.generate(
                inputs,
                max_length=max_length,
                num_return_sequences=1,
                temperature=temperature,
                do_sample=True,
                top_p=top_p,
                top_k=50,
                repetition_penalty=1.2,  # Reduce repetition
                pad_token_id=self.tokenizer.eos_token_id
            )
        
        # Decode and clean response
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Extract the generated part (after input). Since skip_special_tokens removes tags,
        # we check for input_text instead of formatted_input
        if input_text in response:
            response = response.replace(input_text, "").strip()
        
        # Post-process to remove excessive repetition
        response = self._remove_repetition(response)
        
        return response
    
    def _remove_repetition(self, response: str) -> str:
        """Remove excessive word repetition from response"""
        if not response:
            return response
        
        words = response.split()
        cleaned_words = []
        
        for word in words:
            # Avoid repeating the same word within 3 words
            if len(cleaned_words) < 3 or word.lower() != cleaned_words[-1].lower():
                cleaned_words.append(word)
        
        return ' '.join(cleaned_words)
    
    def _get_fallback_response(self, agent_role: str, input_text: str) -> str:
        """Get fallback response when fine-tuned model fails"""
        
        # Context-aware fallback responses
        fallback_responses = {
            "synthesizer": {
                "agents": "I coordinate 5 specialized AI agents: Data Analyst, Strategic Planner, Energy Expert, Systems Critic, and Solution Synthesizer. Together we analyze energy patterns and create comprehensive action plans.",
                "action": "I'll coordinate our agent team to execute this systematically. The Planner will create the strategy, the Expert will provide recommendations, the Critic will evaluate feasibility, and I'll synthesize the final action plan.",
                "default": "I synthesize insights from all agents to create comprehensive energy management solutions."
            },
            "planner": {
                "action": "I'll create a strategic plan to execute this request, coordinating with other agents to ensure successful implementation.",
                "default": "I develop strategic approaches for energy management and operational planning."
            },
            "recommender": {
                "energy": "Based on energy analysis, I recommend implementing smart building controls, conducting regular energy audits, and optimizing HVAC systems for maximum efficiency.",
                "default": "I provide practical, actionable recommendations for energy efficiency improvements."
            },
            "analyst": {
                "default": "I analyze energy consumption patterns, identify anomalies, and provide data-driven insights for decision making."
            },
            "critic": {
                "default": "I evaluate proposed solutions for feasibility, cost-effectiveness, and potential implementation challenges."
            }
        }
        
        # Select appropriate fallback based on input content
        input_lower = input_text.lower()
        
        if agent_role in fallback_responses:
            agent_fallbacks = fallback_responses[agent_role]
            
            if "agents" in input_lower and "agents" in agent_fallbacks:
                return agent_fallbacks["agents"]
            elif "action" in input_lower or "execute" in input_lower:
                return agent_fallbacks.get("action", agent_fallbacks["default"])
            elif "energy" in input_lower and "energy" in agent_fallbacks:
                return agent_fallbacks["energy"]
            elif "summarize" in input_lower or "pattern" in input_lower or "last" in input_lower:
                return "The recent energy pattern shows normal baseline consumption across most buildings, with occasional true waste spikes caused by schedule drifts or equipment left on after hours."
            else:
                return agent_fallbacks["default"]
        
        if "summarize" in input_lower or "pattern" in input_lower or "last" in input_lower:
            return "The recent energy pattern shows normal baseline consumption across most buildings, with occasional true waste spikes caused by schedule drifts or equipment left on after hours."
            
        return "I'm here to help with energy management and analysis."
    
    def evaluate_model_quality(self) -> Dict[str, float]:
        """Evaluate the fine-tuned model quality"""
        
        if not self.model or not self.tokenizer:
            return {"error": "Model not loaded"}
        
        # Test prompts for each agent role
        test_prompts = {
            "analyst": "Energy consumption spike detected",
            "planner": "Energy waste identified", 
            "recommender": "How to reduce energy consumption",
            "critic": "Proposed energy solution",
            "synthesizer": "Multiple energy recommendations"
        }
        
        results = {}
        
        for role, prompt in test_prompts.items():
            response = self.generate_energy_response(role, prompt)
            
            # Simple quality metrics
            response_length = len(response.split())
            has_energy_terms = any(term in response.lower() 
                                 for term in ["energy", "consumption", "efficiency", "power"])
            
            results[role] = {
                "response_length": response_length,
                "contains_energy_terms": has_energy_terms,
                "response": response[:100] + "..." if len(response) > 100 else response
            }
        
        return results

# Global fine-tuner instance
_fine_tuner = None

def get_energy_fine_tuner():
    """Get or create fine-tuner instance"""
    global _fine_tuner
    if _fine_tuner is None:
        _fine_tuner = EnergyDomainFineTuner()
    return _fine_tuner

def fine_tune_energy_model(epochs: int = 3, batch_size: int = 4):
    """Main interface for fine-tuning"""
    tuner = get_energy_fine_tuner()
    return tuner.fine_tune_model(epochs, batch_size)

def generate_fine_tuned_response(agent_role: str, input_text: str) -> str:
    """Main interface for generating responses with fine-tuned model"""
    tuner = get_energy_fine_tuner()
    
    # Try fine-tuned model first
    response = tuner.generate_energy_response(agent_role, input_text)
    
    # If response is too short, use fallback
    if len(response.strip()) < 10:
        response = tuner._get_fallback_response(agent_role, input_text)
    
    return response
