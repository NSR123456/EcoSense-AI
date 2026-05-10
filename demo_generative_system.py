#!/usr/bin/env python3
"""
Demo script for the Generative Multi-Agent Energy System
Shows all three modes: ML-only, Generative-only, and Hybrid
"""

import time
from datetime import datetime
from src.agents.hybrid_agent_system import get_hybrid_team, run_hybrid_analysis

def demo_generative_system():
    """Demonstrate the complete generative multi-agent system"""
    
    print("=== EcoSense Generative Multi-Agent System Demo ===\n")
    
    # Initialize the hybrid team
    print("1. Initializing Hybrid Agent Team...")
    team = get_hybrid_team()
    status = team.get_system_status()
    
    print("   System Status:")
    print(f"   - ML Trainer: {'Available' if status['ml_trainer']['available'] else 'Unavailable'}")
    print(f"   - Generative Team: {'Available' if status['generative_team']['available'] else 'Unavailable'}")
    print(f"   - Current Mode: {status['current_mode']}")
    print()
    
    # Demo anomaly data
    building_id = "Building_A"
    consumption_kwh = 275.8
    baseline = 200.0
    deviation_pct = 37.9
    anomaly_context = "No scheduled event found on campus calendar for 2024-01-15"
    
    print(f"2. Analyzing Energy Anomaly for {building_id}")
    print(f"   - Current Consumption: {consumption_kwh} kWh")
    print(f"   - Baseline: {baseline} kWh")
    print(f"   - Deviation: {deviation_pct}%")
    print()
    
    # Test all three modes
    modes = ["ml_only", "generative_only", "hybrid"]
    
    for mode in modes:
        print(f"3.{modes.index(mode) + 1} Testing {mode.replace('_', ' ').title()} Mode...")
        
        try:
            start_time = time.time()
            
            if mode == "ml_only":
                result = team.analyze_anomaly(
                    building_id, consumption_kwh, baseline, deviation_pct, 
                    anomaly_context, mode
                )
            else:
                result = run_hybrid_analysis(
                    building_id, consumption_kwh, baseline, deviation_pct, 
                    anomaly_context, mode
                )
            
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"   - Status: Success")
            print(f"   - Duration: {duration:.2f} seconds")
            
            if result and len(result) > 0:
                if mode == "ml_only":
                    # ML result format
                    msg = result[0]
                    print(f"   - Agent: {msg.get('agent', 'Unknown')}")
                    print(f"   - Type: {msg.get('type', 'Unknown')}")
                    print(f"   - Recommendation: {msg.get('content', 'No recommendation')}")
                else:
                    # Generative result format
                    print(f"   - Messages Generated: {len(result)}")
                    
                    # Show final synthesizer message
                    final_msg = result[-1] if result else None
                    if final_msg:
                        print(f"   - Final Agent: {final_msg.get('agent', 'Unknown')}")
                        print(f"   - Final Recommendation: {final_msg.get('content', 'No recommendation')[:100]}...")
                    
                    # Show conversation flow
                    print("   - Conversation Flow:")
                    for i, msg in enumerate(result[:3]):  # Show first 3 messages
                        print(f"     {i+1}. {msg.get('agent', 'Unknown')}: {msg.get('content', '')[:50]}...")
            else:
                print("   - No results generated")
            
        except Exception as e:
            print(f"   - Status: Error - {e}")
        
        print()
    
    # Test chat functionality
    print("4. Testing Chat Interface...")
    try:
        user_questions = [
            "How can I reduce energy consumption in Building_A?",
            "What are the main causes of energy waste?",
            "Suggest some energy efficiency measures."
        ]
        
        for question in user_questions:
            print(f"   Q: {question}")
            response = team.chat_with_user(question, building_id)
            print(f"   A: {response[:100]}...")
            print()
    
    except Exception as e:
        print(f"   Chat Error: {e}")
    
    # Test proactive suggestions
    print("5. Testing Proactive Suggestions...")
    try:
        energy_profile = {
            "building_id": building_id,
            "avg_consumption": consumption_kwh,
            "baseline": baseline,
            "efficiency_score": 0.75
        }
        
        suggestions = team.get_proactive_suggestions(building_id, energy_profile)
        print("   Suggestions:")
        for i, suggestion in enumerate(suggestions, 1):
            print(f"   {i}. {suggestion}")
    
    except Exception as e:
        print(f"   Suggestions Error: {e}")
    
    print("\n=== Demo Complete ===")
    print("System Features:")
    print("  - Trained ML: Fast, reliable energy anomaly classification")
    print("  - Generative Chat: Conversational AI for user queries")
    print("  - Multi-Agent Collaboration: 5 specialized agents discuss solutions")
    print("  - Hybrid Mode: Best of both worlds - ML speed + generative conversation")
    print("  - Proactive Suggestions: Context-aware energy recommendations")

if __name__ == "__main__":
    demo_generative_system()
