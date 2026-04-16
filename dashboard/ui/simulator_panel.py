import streamlit as st
import pandas as pd
import time
from src.tools.simulation_tools import simulate_energy_actions
from src.services.storage_manager import StorageManager
from dashboard.ui.charts import (
    render_simulator_metrics_comparison,
    render_simulator_savings_chart,
    render_consumption_before_after,
    render_scenario_impact_bars
)

def render_simulator_panel(metrics: dict, insights: list, resp: dict = None, building_id: str = None):
    """
    Simple, interactive energy simulator using native Streamlit widgets.
    No 3D visualization - just direct, testable controls.
    """
    st.header("⚡ Energy Simulator - Interactive Controls")
    st.write("Adjust device settings below and watch energy calculations update in real-time!")
    
    # Initialize Storage Manager
    sm = StorageManager()
    
    # Define baseline devices
    default_load_states = {
        "Basement": {
            "Pumps": {"active": True, "kwh": 5.5, "hours": 24},
            "Lights": {"active": True, "kwh": 1.8, "hours": 24},
            "Ventilation": {"active": True, "kwh": 3.2, "hours": 24}
        },
        "Lobby": {
            "HVAC": {"active": True, "kwh": 8.5, "hours": 24},
            "Lights": {"active": True, "kwh": 4.5, "hours": 24},
            "Security TV": {"active": True, "kwh": 1.5, "hours": 24}
        },
        "Office Floors": {
            "AC": {"active": True, "kwh": 25.0, "hours": 24},
            "Lights": {"active": True, "kwh": 12.5, "hours": 24},
            "Computers": {"active": True, "kwh": 18.0, "hours": 24},
            "Fans": {"active": True, "kwh": 6.0, "hours": 24}
        },
        "Rooftop": {
            "Chiller": {"active": True, "kwh": 35.0, "hours": 24},
            "Solar": {"active": True, "kwh": -15.0, "hours": 12},
            "Maintenance": {"active": True, "kwh": 2.5, "hours": 24}
        }
    }
    
    # Initialize session state
    if "simulator_db_initialized" not in st.session_state:
        sm.initialize_defaults(default_load_states)
        st.session_state.simulator_db_initialized = True
    
    # Get current state from database
    current_db_states = sm.get_all_loads()
    st.session_state.load_states = current_db_states
    
    # --- 1. INTERACTIVE DEVICE CONTROLS ---
    st.subheader("🎛️ Device Configuration")
    st.write("Toggle devices on/off and adjust operating hours")
    
    # Build interactive control for each device
    devices_changed = False
    
    for floor in sorted(current_db_states.keys()):
        with st.expander(f"🏢 **{floor}**", expanded=True):
            loads = current_db_states[floor]
            
            # Create columns for this floor
            col_names, col_active, col_hours = st.columns([3, 1.5, 2])
            
            with col_names:
                st.write("**Device**")
            with col_active:
                st.write("**Status**")
            with col_hours:
                st.write("**Hours/Day**")
            
            st.divider()
            
            for device_name, device_data in sorted(loads.items()):
                col1, col2, col3 = st.columns([3, 1.5, 2])
                
                with col1:
                    st.write(f"💡 {device_name}")
                    st.caption(f"{device_data['kwh']} kWh base")
                
                with col2:
                    # Toggle for active/inactive
                    current_active = device_data.get("active", True)
                    new_active = st.checkbox(
                        label="Active",
                        value=current_active,
                        key=f"{floor}_{device_name}_active",
                        label_visibility="collapsed"
                    )
                    
                    if new_active != current_active:
                        devices_changed = True
                        sm.update_load(floor, device_name, new_active, device_data["hours"])
                
                with col3:
                    # Slider for hours
                    current_hours = device_data.get("hours", 24)
                    new_hours = st.slider(
                        label="Hours",
                        min_value=0,
                        max_value=24,
                        value=int(current_hours),
                        step=1,
                        key=f"{floor}_{device_name}_hours",
                        label_visibility="collapsed"
                    )
                    
                    if new_hours != current_hours:
                        devices_changed = True
                        sm.update_load(floor, device_name, new_active, new_hours)
    
    # Refresh DB state if changes were made
    if devices_changed:
        current_db_states = sm.get_all_loads()
        st.rerun()
    
    # --- 2. BASELINE CALCULATIONS ---
    st.divider()
    st.subheader("📊 Energy Impact Calculation")
    
    # Baseline power (Static Defaults)
    baseline_power = 0
    for floor, loads in default_load_states.items():
        for name, data in loads.items():
            baseline_power += abs(data["kwh"]) * data["hours"]
    
    # Current configuration power (From Database)
    current_config_power = 0
    for floor, loads in current_db_states.items():
        for name, data in loads.items():
            if data.get("active", False):
                p_val = data.get("kwh", 0)
                h_val = int(data.get("hours", 0))
                if p_val < 0:  # Solar (offset)
                    current_config_power -= abs(p_val) * h_val
                else:
                    current_config_power += p_val * h_val
    
    # Calculate Savings
    savings_kwh = baseline_power - current_config_power
    savings_pct = (savings_kwh / baseline_power * 100) if baseline_power > 0 else 0
    
    # Display Key Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Baseline Daily", f"{baseline_power:.1f} kWh", label_visibility="collapsed")
        st.caption("Baseline Usage")
    
    with col2:
        st.metric("Current Daily", f"{current_config_power:.1f} kWh", label_visibility="collapsed")
        st.caption("Your Config")
    
    with col3:
        st.metric("Daily Savings", f"{savings_kwh:.1f} kWh", delta=f"{savings_pct:.1f}%", label_visibility="collapsed")
        st.caption("Reduction")
    
    with col4:
        monthly_savings = savings_kwh * 30
        cost_savings = monthly_savings * 0.12
        st.metric("Monthly Savings", f"${cost_savings:.2f}", delta=f"{monthly_savings:.0f} kWh", label_visibility="collapsed")
        st.caption("Cost Reduction")
    
    # --- 3. RUN SIMULATION ---
    # Map to simulation parameters
    reduce_peak_pct = savings_pct * 3.5
    reduce_base_load_pct = savings_pct * 2.5
    reduce_variability_pct = savings_pct * 2.0
    efficiency_upgrade_pct = 15
    
    scenario = {
        "reduce_peak_pct": reduce_peak_pct,
        "reduce_base_load_pct": reduce_base_load_pct,
        "reduce_variability_pct": reduce_variability_pct,
        "efficiency_upgrade_pct": efficiency_upgrade_pct,
    }
    
    sim = simulate_energy_actions(metrics, insights, scenario)
    
    # --- 4. DISPLAY DYNAMIC CHARTS ---
    st.divider()
    st.header("📈 Real-Time Energy Impact Analysis")
    
    if sim and (sim.get("estimated_savings_daily_kwh", 0) > 0 or sim.get("estimated_savings_pct", 0) != 0):
        # Chart 1: Savings Overview
        st.subheader("💡 Projected Savings")
        render_simulator_savings_chart(sim, key=f"sim_savings_{int(time.time())}")
        
        # Chart 2: 24-Hour Profile
        st.subheader("📈 Consumption Profile: Current vs. Optimized")
        render_consumption_before_after(sim, key=f"consumption_{int(time.time())}")
        
        # Chart 3: Detailed Metrics
        st.subheader("📋 Detailed Energy Metrics")
        render_simulator_metrics_comparison(sim, key=f"metrics_{int(time.time())}")
        
        # Chart 4: Strategy Breakdown
        st.subheader("🎯 Optimization Strategy Breakdown")
        render_scenario_impact_bars(sim, key=f"strategy_{int(time.time())}")
        
        # Smart Recommendations
        st.divider()
        st.subheader("💡 Smart Recommendations")
        
        col1, col2 = st.columns(2)
        
        with col1:
            actual_savings_pct = sim.get("estimated_savings_pct", 0)
            if actual_savings_pct > 25:
                st.success(f"🔥 **Aggressive Optimization** - You're saving {actual_savings_pct:.1f}%! Excellent configuration.")
            elif actual_savings_pct > 15:
                st.info(f"✅ **Solid Optimization** - {actual_savings_pct:.1f}% savings achieved. Consider fine-tuning HVAC.")
            elif actual_savings_pct > 5:
                st.warning(f"⚠️ **Moderate Savings** - Only {actual_savings_pct:.1f}% reduction. Try disabling more loads.")
            else:
                st.info("📌 **Minor Changes** - Adjust more settings to see significant impact.")
        
        with col2:
            monthly_potential = sim.get('estimated_savings_monthly_kwh', 0) * 0.12
            st.metric("Monthly Potential", f"${monthly_potential:.2f}")
    else:
        st.info("👉 Adjust device settings above to see real-time impact on energy calculations!")
    
    # --- 5. DEBUG PANEL ---
    with st.expander("🔧 DEBUG: Database State & Sync Verification", expanded=False):
        st.write("**Current Database State:**")
        
        # Show all devices and their current status
        debug_data = []
        for floor, loads in current_db_states.items():
            for name, data in loads.items():
                status = "? On" if data['active'] else "? Off"
                debug_data.append({
                    "Floor": floor,
                    "Device": name,
                    "Status": status,
                    "kWh": data['kwh'],
                    "Hours": data['hours'],
                    "Total": data['kwh'] * data['hours']
                })
        
        df_debug = pd.DataFrame(debug_data)
        st.dataframe(df_debug, use_container_width=True, hide_index=True)
        
        st.write("**Calculation Breakdown:**")
        st.write(f"- Baseline Energy: {baseline_power:.2f} kWh/day")
        st.write(f"- Current Energy: {current_config_power:.2f} kWh/day")
        st.write(f"- Daily Savings: {savings_kwh:.2f} kWh ({savings_pct:.2f}%)")
        st.write(f"- Monthly Savings: {savings_kwh * 30:.2f} kWh")
        st.write(f"- Cost Savings: ${savings_kwh * 30 * 0.12:.2f}")
        
        st.write("**Simulation Parameters:**")
        st.json(scenario)
    
    return sim
