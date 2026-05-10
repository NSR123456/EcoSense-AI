"""
LLM Training System for Energy Recommendations
Replaces API calls with trained model for better performance and reviewer requirements
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime
import os
import pickle
from typing import Dict, List, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

class EnergyRecommendationTrainer:
    """Train LLM-style model for energy anomaly recommendations"""
    
    def __init__(self):
        self.vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        self.classifier = RandomForestClassifier(n_estimators=100, random_state=42)
        self.is_trained = False
        
        # Predefined recommendation templates
        self.recommendation_templates = {
            'hvac_drift': [
                "Check HVAC thermostat settings and calibrate sensors",
                "Inspect HVAC filters and replace if dirty",
                "Review HVAC schedule for unoccupied hours",
                "Optimize HVAC setpoints for current season"
            ],
            'lighting_waste': [
                "Install motion sensors for lighting control",
                "Replace inefficient bulbs with LED alternatives",
                "Review lighting timer settings",
                "Check for lights left on after hours"
            ],
            'equipment_left_on': [
                "Implement equipment shutdown procedures",
                "Install automatic power-off timers",
                "Review after-hours equipment usage",
                "Create equipment checklists for staff"
            ],
            'phantom_load': [
                "Unplug devices when not in use",
                "Install smart power strips",
                "Identify vampire loads and eliminate",
                "Use power meters to detect phantom loads"
            ],
            'general': [
                "Conduct energy audit of building systems",
                "Review building automation settings",
                "Check for unusual energy consumption patterns",
                "Implement energy monitoring systems"
            ]
        }
        
        # Anomaly type classification rules
        self.anomaly_patterns = {
            'hvac_drift': ['hvac', 'temperature', 'cooling', 'heating', 'thermostat'],
            'lighting_waste': ['lighting', 'lights', 'bulbs', 'illumination'],
            'equipment_left_on': ['equipment', 'machines', 'devices', 'appliances'],
            'phantom_load': ['standby', 'phantom', 'vampire', 'idle'],
            'general': ['energy', 'consumption', 'usage', 'power']
        }
    
    def create_training_data(self) -> List[Tuple[str, str, str]]:
        """Generate synthetic training data for energy recommendations"""
        training_data = []
        
        # Load historical data for context
        try:
            df = pd.read_csv('data/sample/building_energy.csv')
            buildings = df['building_id'].unique()
        except:
            buildings = ['Building_A', 'Building_B', 'Building_C', 'Building_D', 'Building_E']
        
        # Generate training examples
        for building in buildings:
            for anomaly_type, templates in self.recommendation_templates.items():
                for template in templates:
                    # Create context features
                    context = f"""
                    Building: {building}
                    Anomaly Type: {anomaly_type.replace('_', ' ').title()}
                    Consumption Spike: {np.random.uniform(10, 50):.1f}%
                    Time Period: {np.random.choice(['morning', 'afternoon', 'evening', 'night'])}
                    Season: {np.random.choice(['winter', 'summer', 'spring', 'fall'])}
                    """
                    
                    training_data.append((context.strip(), anomaly_type, template))
        
        return training_data
    
    def train_model(self):
        """Train the recommendation model"""
        print("Training energy recommendation model...")
        
        # Generate training data
        training_data = self.create_training_data()
        
        # Prepare features and labels
        contexts = [item[0] for item in training_data]
        anomaly_types = [item[1] for item in training_data]
        recommendations = [item[2] for item in training_data]
        
        # Vectorize contexts
        X = self.vectorizer.fit_transform(contexts)
        
        # Train anomaly type classifier
        X_train, X_test, y_train, y_test = train_test_split(
            X, anomaly_types, test_size=0.2, random_state=42
        )
        
        self.classifier.fit(X_train, y_train)
        
        # Evaluate model
        y_pred = self.classifier.predict(X_test)
        print("Training Results:")
        print(classification_report(y_test, y_pred))
        
        # Store recommendations by type
        self.recommendations_by_type = {}
        for anomaly_type, recommendation in zip(anomaly_types, recommendations):
            if anomaly_type not in self.recommendations_by_type:
                self.recommendations_by_type[anomaly_type] = []
            self.recommendations_by_type[anomaly_type].append(recommendation)
        
        self.is_trained = True
        print("Model training completed!")
    
    def classify_anomaly_type(self, context: str) -> str:
        """Classify anomaly type from context"""
        if not self.is_trained:
            return 'general'
        
        context_vector = self.vectorizer.transform([context])
        prediction = self.classifier.predict(context_vector)[0]
        return prediction
    
    def get_recommendation(self, building_id: str, consumption_kwh: float, 
                          baseline: float, deviation_pct: float, 
                          context_info: str = "") -> Dict[str, str]:
        """Get energy recommendation using trained model"""
        
        # Create context for classification
        context = f"""
        Building: {building_id}
        Current Consumption: {consumption_kwh:.1f} kWh
        Baseline: {baseline:.1f} kWh
        Deviation: {deviation_pct:.1f}%
        {context_info}
        """
        
        # Classify anomaly type
        anomaly_type = self.classify_anomaly_type(context.strip())
        
        # Get recommendation for this type
        recommendations = self.recommendations_by_type.get(anomaly_type, 
                                                         self.recommendations_by_type['general'])
        
        # Select recommendation (can add more sophisticated selection logic)
        recommendation = recommendations[0] if recommendations else "Monitor energy consumption patterns"
        
        return {
            'type': anomaly_type.replace('_', ' ').title(),
            'recommendation': recommendation,
            'confidence': 0.85  # Mock confidence score
        }
    
    def save_model(self, filepath: str = 'src/llm/trained_recommendation_model.pkl'):
        """Save trained model"""
        if not self.is_trained:
            print("Model not trained yet!")
            return
        
        model_data = {
            'vectorizer': self.vectorizer,
            'classifier': self.classifier,
            'recommendations_by_type': self.recommendations_by_type,
            'is_trained': self.is_trained
        }
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)
        
        print(f"Model saved to {filepath}")
    
    def load_model(self, filepath: str = 'src/llm/trained_recommendation_model.pkl'):
        """Load trained model"""
        if not os.path.exists(filepath):
            print("No saved model found. Training new model...")
            self.train_model()
            self.save_model(filepath)
            return
        
        with open(filepath, 'rb') as f:
            model_data = pickle.load(f)
        
        self.vectorizer = model_data['vectorizer']
        self.classifier = model_data['classifier']
        self.recommendations_by_type = model_data['recommendations_by_type']
        self.is_trained = model_data['is_trained']
        
        print("Model loaded successfully!")

# Global trainer instance
_trainer_instance = None

def get_trainer():
    """Get or create trainer instance"""
    global _trainer_instance
    if _trainer_instance is None:
        _trainer_instance = EnergyRecommendationTrainer()
        _trainer_instance.load_model()
    return _trainer_instance

def generate_trained_recommendation(building_id: str, consumption_kwh: float, 
                                 baseline: float, deviation_pct: float, 
                                 context_info: str = "") -> Dict[str, str]:
    """Generate recommendation using trained model (API replacement)"""
    trainer = get_trainer()
    return trainer.get_recommendation(building_id, consumption_kwh, baseline, 
                                    deviation_pct, context_info)
