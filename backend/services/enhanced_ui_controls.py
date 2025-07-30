"""
Enhanced Trading UI - Quick Controls Extension
Additional controls for dynamic configuration
"""

import streamlit as st
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def render_enhanced_controls():
    """Render enhanced quick controls with real-time configuration."""
    st.markdown("## ⚙️ Enhanced Quick Controls")
    
    # Create two columns for better organization
    control_col1, control_col2 = st.columns(2)
    
    with control_col1:
        st.markdown("### 🎯 Trading Parameters")
        
        # Dynamic confidence threshold
        confidence_threshold = st.slider(
            "🎯 Min Confidence", 
            5.0, 10.0, 
            float(getattr(st.session_state, 'confidence_threshold', 6.0)), 
            0.5,
            help="Minimum confidence score required for trade signals"
        )
        st.session_state.confidence_threshold = confidence_threshold
        
        # Position size multiplier
        position_multiplier = st.slider(
            "📊 Position Size Multiplier", 
            0.5, 2.0, 
            float(getattr(st.session_state, 'position_multiplier', 1.0)), 
            0.1,
            help="Multiply base position size (25% base)"
        )
        st.session_state.position_multiplier = position_multiplier
        
        # Auto-execute threshold
        auto_execute_threshold = st.slider(
            "🤖 Auto-Execute Above", 
            8.0, 10.0, 
            float(getattr(st.session_state, 'auto_execute_threshold', 9.5)), 
            0.5,
            help="Automatically execute trades above this confidence"
        )
        st.session_state.auto_execute_threshold = auto_execute_threshold
        
        # Paper vs Live toggle
        paper_trading = st.toggle(
            "📝 Paper Trading Mode", 
            value=getattr(st.session_state, 'paper_trading', True),
            help="Enable/disable paper trading (CAUTION: Disabling uses real money!)"
        )
        st.session_state.paper_trading = paper_trading
        
    with control_col2:
        st.markdown("### 📈 Technical Settings")
        
        # Williams %R oversold level
        williams_r_oversold = st.slider(
            "📊 Williams %R Oversold", 
            -90, -70, 
            int(getattr(st.session_state, 'williams_r_oversold', -80)), 
            5,
            help="Williams %R oversold threshold (more negative = more oversold)"
        )
        st.session_state.williams_r_oversold = williams_r_oversold
        
        # Volume spike requirement
        volume_multiplier = st.slider(
            "📈 Volume Spike Required", 
            1.5, 5.0, 
            float(getattr(st.session_state, 'volume_multiplier', 3.0)), 
            0.5,
            help="Minimum volume multiple vs average"
        )
        st.session_state.volume_multiplier = volume_multiplier
        
        # Momentum multiplier minimum
        momentum_min = st.slider(
            "⚡ Momentum Multiplier Min", 
            0, 10, 
            int(getattr(st.session_state, 'momentum_min', 5)), 
            1,
            help="Minimum momentum multiplier score (0-10 scale)"
        )
        st.session_state.momentum_min = momentum_min
        
        # Max daily risk
        max_daily_risk = st.slider(
            "📉 Max Daily Loss %", 
            5, 25, 
            int(getattr(st.session_state, 'max_daily_risk', 15)), 
            1,
            help="Maximum daily portfolio loss percentage"
        )
        st.session_state.max_daily_risk = max_daily_risk
    
    # Control buttons
    button_col1, button_col2, button_col3 = st.columns(3)
    
    with button_col1:
        if st.button("💾 Save Settings", type="primary"):
            # Update live configuration
            update_live_config()
            st.success("Settings saved and applied!")
            
    with button_col2:
        if st.button("🔄 Force Refresh", type="secondary"):
            st.experimental_rerun()
            
    with button_col3:
        if st.button("🔧 Reset to Defaults", type="secondary"):
            reset_to_defaults()
            st.experimental_rerun()


def update_live_config():
    """Update live configuration with UI settings."""
    try:
        # Import dynamic config service
        from services.dynamic_config_service import dynamic_config
        
        # Update configuration through dynamic service
        success = dynamic_config.update_from_ui_session(st.session_state)
        
        if success:
            # Apply to static config immediately
            dynamic_config.apply_to_static_config()
            logger.info("Live configuration updated from UI and applied to system")
        else:
            st.error("Failed to update configuration")
            
    except Exception as e:
        logger.error(f"Error updating live config: {e}")
        st.error(f"Error saving settings: {e}")


def reset_to_defaults():
    """Reset all settings to default values."""
    st.session_state.confidence_threshold = 6.0
    st.session_state.position_multiplier = 1.0
    st.session_state.auto_execute_threshold = 9.5
    st.session_state.paper_trading = True
    st.session_state.williams_r_oversold = -80
    st.session_state.volume_multiplier = 3.0
    st.session_state.momentum_min = 5
    st.session_state.max_daily_risk = 15
    st.success("Settings reset to defaults!")


def show_current_settings():
    """Show current configuration settings."""
    try:
        from services.dynamic_config_service import dynamic_config
        
        st.markdown("### ⚙️ Current Active Settings")
        
        confidence_settings = dynamic_config.get_section('confidence_settings')
        technical_settings = dynamic_config.get_section('technical_settings')
        position_settings = dynamic_config.get_section('position_settings')
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Confidence:**")
            st.write(f"• Min Confidence: {confidence_settings.get('min_confidence_score', 6.0)}")
            st.write(f"• Auto-Execute: {confidence_settings.get('auto_execute_threshold', 9.5)}")
            
            st.write("**Position Sizing:**")
            st.write(f"• Base Size: {position_settings.get('base_position_size_percent', 0.25)*100:.0f}%")
            st.write(f"• Multiplier: {position_settings.get('position_size_multiplier', 1.0):.1f}x")
            
        with col2:
            st.write("**Technical:**")
            st.write(f"• Williams %R: {technical_settings.get('williams_r_oversold', -80)}")
            st.write(f"• Volume Spike: {technical_settings.get('volume_spike_multiplier', 3.0):.1f}x")
            st.write(f"• Momentum Min: {technical_settings.get('momentum_multiplier_min', 5)}")
        
    except Exception as e:
        logger.error(f"Error showing current settings: {e}")
        st.warning("Could not load current settings")
