"""
Hybrid Agent System - Combines Trained ML with Generative Chat
Uses trained ML for fast classification and generative agents for rich conversation
"""

from typing import List, Dict, Any, Optional
import json
from datetime import datetime
from src.llm.energy_recommendation_trainer import generate_trained_recommendation
from src.agents.generative_agent_system import get_generative_team, run_generative_analysis

class HybridAgentTeam:
    """Hybrid system combining trained ML with generative agents"""
    
    def __init__(self):
        self.ml_trainer = None
        self.generative_team = None
        self.use_generative = True  # Toggle between ML-only and hybrid modes
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize both ML and generative components"""
        try:
            # Initialize ML trainer
            from src.llm.energy_recommendation_trainer import get_trainer
            self.ml_trainer = get_trainer()
            print("ML trainer initialized successfully")
        except Exception as e:
            print(f"ML trainer initialization failed: {e}")
        
        try:
            # Initialize generative team
            self.generative_team = get_generative_team()
            print("Generative team initialized successfully")
        except Exception as e:
            print(f"Generative team initialization failed: {e}")
            self.use_generative = False
    
    def analyze_anomaly(self, building_id: str, consumption_kwh: float, 
                        baseline: float, deviation_pct: float, 
                        anomaly_context: str = "", 
                        mode: str = "hybrid") -> List[Dict]:
        """
        Analyze anomaly using hybrid approach
        
        Args:
            mode: "ml_only", "generative_only", or "hybrid"
        """
        
        print(f"Starting {mode} analysis for {building_id} anomaly...")
        
        if mode == "ml_only":
            return self._ml_analysis(building_id, consumption_kwh, baseline, deviation_pct, anomaly_context)
        elif mode == "generative_only":
            return self._generative_analysis(building_id, consumption_kwh, baseline, deviation_pct, anomaly_context)
        else:  # hybrid
            return self._hybrid_analysis(building_id, consumption_kwh, baseline, deviation_pct, anomaly_context)
    
    def _ml_analysis(self, building_id: str, consumption_kwh: float, 
                     baseline: float, deviation_pct: float, 
                     anomaly_context: str) -> List[Dict]:
        """Fast ML-based analysis"""
        if not self.ml_trainer:
            return self._fallback_analysis(building_id, anomaly_context)
        
        try:
            # Get ML recommendation
            ml_result = generate_trained_recommendation(
                building_id, consumption_kwh, baseline, deviation_pct, anomaly_context
            )
            
            # Convert to agent message format
            return [{
                "agent": "ML Recommender",
                "role": "recommender",
                "content": f"ML Analysis: {ml_result.get('type', 'Unknown')} detected. {ml_result.get('recommendation', 'Monitor energy usage.')}",
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "type": "ml_analysis",
                "confidence": ml_result.get('confidence', 0.85)
            }]
            
        except Exception as e:
            print(f"ML analysis failed: {e}")
            return self._fallback_analysis(building_id, anomaly_context)
    
    def _generative_analysis(self, building_id: str, consumption_kwh: float, 
                            baseline: float, deviation_pct: float, 
                            anomaly_context: str) -> List[Dict]:
        """Rich generative analysis"""
        if not self.generative_team:
            return self._fallback_analysis(building_id, anomaly_context)
        
        try:
            return run_generative_analysis(
                building_id, consumption_kwh, baseline, deviation_pct, anomaly_context
            )
        except Exception as e:
            print(f"Generative analysis failed: {e}")
            return self._fallback_analysis(building_id, anomaly_context)
    
    def _hybrid_analysis(self, building_id: str, consumption_kwh: float, 
                        baseline: float, deviation_pct: float, 
                        anomaly_context: str) -> List[Dict]:
        """Best of both worlds - ML speed + generative conversation"""
        
        messages = []
        
        # Step 1: Fast ML classification
        if self.ml_trainer:
            try:
                ml_result = generate_trained_recommendation(
                    building_id, consumption_kwh, baseline, deviation_pct, anomaly_context
                )
                
                messages.append({
                    "agent": "ML Classifier",
                    "role": "analyst",
                    "content": f"ML Classification: {ml_result.get('type', 'Unknown')} anomaly detected with {deviation_pct:.1f}% deviation from baseline.",
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "type": "ml_classification",
                    "confidence": ml_result.get('confidence', 0.85)
                })
                
                # Step 2: Use ML result to inform generative discussion
                if self.generative_team:
                    enhanced_context = f"""
                    {anomaly_context}
                    
                    ML Analysis Results:
                    - Anomaly Type: {ml_result.get('type', 'Unknown')}
                    - Recommendation: {ml_result.get('recommendation', 'Monitor energy usage.')}
                    - Confidence: {ml_result.get('confidence', 0.85)}
                    """
                    
                    generative_messages = run_generative_analysis(
                        building_id, consumption_kwh, baseline, deviation_pct, enhanced_context
                    )
                    
                    # Add generative messages
                    messages.extend(generative_messages)
                
            except Exception as e:
                print(f"Hybrid ML step failed: {e}")
                # Fall back to generative only
                if self.generative_team:
                    messages.extend(self._generative_analysis(
                        building_id, consumption_kwh, baseline, deviation_pct, anomaly_context
                    ))
        
        return messages
    
    def _fallback_analysis(self, building_id: str, anomaly_context: str) -> List[Dict]:
        """Fallback when both systems fail"""
        return [{
            "agent": "System",
            "role": "analyst", 
            "content": f"Energy anomaly detected for {building_id}. {anomaly_context} Please investigate the consumption patterns.",
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "type": "fallback",
            "confidence": 0.5
        }]
    
    def chat_with_user(self, user_message: str, building_context: str = "") -> str:
        """Chat interface using generative agents"""
        if not self.generative_team:
            return "Chat system unavailable. Please check system configuration."
        
        try:
            return self.generative_team.chat_with_user(user_message, building_context)
        except Exception as e:
            print(f"Chat failed: {e}")
            return "I'm having trouble processing your request. Please try again."
    
    def get_proactive_suggestions(self, building_id: str, energy_profile: Dict) -> List[str]:
        """Get proactive suggestions using hybrid approach"""
        suggestions = []
        
        # ML-based suggestions (fast, rule-based)
        if self.ml_trainer:
            try:
                # Create a mock anomaly for suggestion generation
                ml_result = generate_trained_recommendation(
                    building_id, energy_profile.get('avg_consumption', 100), 
                    energy_profile.get('baseline', 80), 15.0, "Proactive analysis request"
                )
                suggestions.append(ml_result.get('recommendation', 'Monitor energy usage'))
            except Exception as e:
                print(f"ML suggestions failed: {e}")
        
        # Generative suggestions (rich, contextual)
        if self.generative_team and len(suggestions) < 3:
            try:
                gen_suggestions = self.generative_team.get_suggestions(building_id, energy_profile)
                suggestions.extend(gen_suggestions)
            except Exception as e:
                print(f"Generative suggestions failed: {e}")
        
        # Ensure we have at least 3 suggestions
        while len(suggestions) < 3:
            default_suggestions = [
                "Conduct regular energy audits",
                "Implement smart building controls",
                "Train staff on energy conservation"
            ]
            suggestions.append(default_suggestions[len(suggestions)])
        
        return suggestions[:3]
    
    def get_system_status(self) -> Dict:
        """Get status of both systems"""
        return {
            "ml_trainer": {
                "available": self.ml_trainer is not None,
                "type": "RandomForest + TF-IDF"
            },
            "generative_team": {
                "available": self.generative_team is not None,
                "type": "Hugging Face DialoGPT",
                "agents": ["analyst", "planner", "recommender", "critic", "synthesizer"] if self.generative_team else []
            },
            "current_mode": "hybrid" if self.use_generative and self.ml_trainer else "fallback"
        }

# Global hybrid team instance
_hybrid_team = None

def get_hybrid_team():
    """Get or create hybrid agent team instance"""
    global _hybrid_team
    if _hybrid_team is None:
        _hybrid_team = HybridAgentTeam()
    return _hybrid_team

def run_hybrid_analysis(building_id: str, consumption_kwh: float, 
                       baseline: float, deviation_pct: float, 
                       anomaly_context: str = "", mode: str = "hybrid") -> List[Dict]:
    """Main interface for hybrid analysis"""
    team = get_hybrid_team()
    return team.analyze_anomaly(
        building_id, consumption_kwh, baseline, deviation_pct, anomaly_context, mode
    )

def chat_with_energy_assistant(user_message: str, building_context: str = "") -> str:
    """Main interface for user chat"""
    team = get_hybrid_team()
    return team.chat_with_user(user_message, building_context)

def get_energy_suggestions(building_id: str, energy_profile: Dict) -> List[str]:
    """Main interface for proactive suggestions"""
    team = get_hybrid_team()
    return team.get_proactive_suggestions(building_id, energy_profile)
