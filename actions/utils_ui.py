import streamlit as st

def card(title, content, icon=None):
    """
    Renders a glassmorphism card with title and content.
    """
    icon_html = f"<span style='font-size: 24px; margin-right: 10px;'>{icon}</span>" if icon else ""
    st.markdown(f"""
    <div style="
        background: rgba(30, 41, 59, 0.7);
        padding: 1.5rem;
        border-radius: 1rem;
        border: 1px solid rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(12px);
        margin-bottom: 1rem;
    ">
        <div style="display: flex; align-items: center; margin-bottom: 0.5rem;">
            {icon_html}
            <h3 style="margin: 0; font-size: 1.25rem;">{title}</h3>
        </div>
        <div>
            {content}
        </div>
    </div>
    """, unsafe_allow_html=True)

def metric_card(label, value, delta=None, icon=None):
    """
    A premium metric card.
    """
    delta_color = "green" if delta and not delta.startswith("-") else "red"
    delta_html = f"<span style='color: {delta_color}; font-size: 0.875rem;'>{delta}</span>" if delta else ""
    
    icon_html = f"<div style='font-size: 1.5rem;'>{icon if icon else ''}</div>" if icon else ""
    
    st.markdown(f"""
    <div class="glass-metric-card">
        <div style='display: flex; align-items: center; gap: 10px; margin-bottom: 8px;'>
            {icon_html}
            <div style='font-size: 0.75rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; line-height: 1.1;'>{label}</div>
        </div>
        <div style="font-size: 1.6rem; font-weight: 700; color: #f8fafc; margin-top: auto;">{value}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)
