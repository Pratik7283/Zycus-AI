"""
Streamlit UI Demo for Zycus AI Project
A user-friendly interface for non-technical TAMs to use Task 1 and Task 2 functionality.
"""

import streamlit as st
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from task1.service import triage_ticket
from task2.service import generate_account_brief

# Page configuration
st.set_page_config(
    page_title="Zycus AI Assistant",
    page_icon="⚡",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS for modern, clean styling
st.markdown("""
<style>
    .stApp {
        background-color: #f8f9fa;
    }
    .main-title {
        font-size: 2rem;
        font-weight: 700;
        color: #1a1a1a;
        margin-bottom: 0.5rem;
    }
    .subtitle {
        font-size: 1rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        margin: 1rem 0;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #666;
        font-weight: 500;
    }
    .metric-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: #1a1a1a;
    }
    div[data-testid="stForm"] {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Simple header
st.markdown('<div class="main-title">⚡ Zycus AI Assistant</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Support automation for Technical Account Managers</div>', unsafe_allow_html=True)

# Simple tab navigation
tab1, tab2, tab3 = st.tabs(["🎫 Ticket Triage", "📊 Account Brief", "ℹ️ About"])

# Ticket Triage Page
with tab1:
    st.markdown('<div class="sub-header">📋 Ticket Triage</div>', unsafe_allow_html=True)
    
    # Input form
    with st.form("ticket_form"):
        subject = st.text_input("Ticket Subject", placeholder="e.g., Cannot export report")
        body = st.text_area("Ticket Body", placeholder="Describe the issue in detail...", height=100)
        
        col1, col2 = st.columns(2)
        with col1:
            submit_button = st.form_submit_button("Analyze Ticket", type="primary")
        with col2:
            clear_button = st.form_submit_button("Clear")
    
    if submit_button:
        if not subject and not body:
            st.error("Please provide either a subject or body for the ticket.")
        else:
            with st.spinner("Analyzing ticket..."):
                try:
                    result = triage_ticket({"subject": subject, "body": body})
                    
                    # Results container
                    st.markdown('<div class="card">', unsafe_allow_html=True)
                    
                    # Classification results with contrast colors
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.markdown(f'<div class="metric-label">Product Area</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="metric-value" style="color: #2563eb;">{result.product_area}</div>', unsafe_allow_html=True)
                    with col2:
                        st.markdown(f'<div class="metric-label">Issue Category</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="metric-value" style="color: #7c3aed;">{result.issue_category}</div>', unsafe_allow_html=True)
                    with col3:
                        st.markdown(f'<div class="metric-label">Urgency Tier</div>', unsafe_allow_html=True)
                        urgency_color = "#dc2626" if result.urgency_tier == "P1" else "#f59e0b" if result.urgency_tier == "P2" else "#059669"
                        st.markdown(f'<div class="metric-value" style="color: {urgency_color};">{result.urgency_tier}</div>', unsafe_allow_html=True)
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # Recommended team with high contrast
                    st.markdown('<div class="card">', unsafe_allow_html=True)
                    st.markdown(f'<div class="metric-label">Recommended Team</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="metric-value" style="color: #0891b2;">🎯 {result.recommended_team}</div>', unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # Knowledge base match
                    if result.known_issue_match:
                        st.markdown('<div class="card" style="border-left: 4px solid #10b981;">', unsafe_allow_html=True)
                        st.markdown(f'**📚 Knowledge Base Match:** {result.matched_kb_doc}')
                        with st.expander("View Article Excerpt"):
                            st.write(result.matched_kb_excerpt)
                        st.markdown('</div>', unsafe_allow_html=True)
                    else:
                        st.info("⚠️ No knowledge base match found")
                    
                    # Draft response
                    st.markdown('<div class="card">', unsafe_allow_html=True)
                    st.markdown('**📝 Suggested Response**')
                    st.write(result.draft_first_response)
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # Confidence score
                    st.caption(f'Confidence: {result.confidence:.0%}')
                    
                except Exception as e:
                    st.error(f"Error: {str(e)}")

# Account Brief Page
with tab2:
    st.markdown('<div class="sub-header">📊 Account Brief</div>', unsafe_allow_html=True)
    
    # Load available accounts
    try:
        from task2.service import load_accounts
        accounts = load_accounts()
        account_options = {acc["account_id"]: f"{acc['company']} ({acc['account_id']})" for acc in accounts}
    except Exception as e:
        st.error(f"Error loading accounts: {str(e)}")
        account_options = {}
    
    # Input form
    with st.form("account_form"):
        selected_account = st.selectbox(
            "Select Account",
            options=list(account_options.keys()),
            format_func=lambda x: account_options.get(x, x),
            index=0 if account_options else None
        )
        
        col1, col2 = st.columns(2)
        with col1:
            submit_button = st.form_submit_button("Generate Brief", type="primary")
        with col2:
            clear_button = st.form_submit_button("Clear")
    
    if submit_button:
        with st.spinner("Generating account brief..."):
            try:
                result = generate_account_brief({"account_id": selected_account})
                
                # Account overview with contrast colors
                st.markdown('<div class="card">', unsafe_allow_html=True)
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.markdown(f'<div class="metric-label">Company</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="metric-value" style="color: #1e40af;">{result.company}</div>', unsafe_allow_html=True)
                with col2:
                    st.markdown(f'<div class="metric-label">TAM</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="metric-value" style="color: #7c3aed;">{result.tam}</div>', unsafe_allow_html=True)
                with col3:
                    st.markdown(f'<div class="metric-label">Health Status</div>', unsafe_allow_html=True)
                    health_color = "#dc2626" if result.health_status == "At Risk" else "#059669" if result.health_status == "Healthy" else "#f59e0b"
                    st.markdown(f'<div class="metric-value" style="color: {health_color};">{result.health_status}</div>', unsafe_allow_html=True)
                with col4:
                    st.markdown(f'<div class="metric-label">Usage Trend</div>', unsafe_allow_html=True)
                    trend_color = "#059669" if result.usage_trend == "Increasing" else "#dc2626" if result.usage_trend == "Declining" else "#6b7280"
                    st.markdown(f'<div class="metric-value" style="color: {trend_color};">{result.usage_trend}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Executive summary
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.markdown('**📋 Executive Summary**')
                st.write(result.executive_summary)
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Open risks with contrast
                if result.open_risks_and_flagged_issues:
                    st.markdown('<div class="card" style="border-left: 4px solid #f59e0b;">', unsafe_allow_html=True)
                    st.markdown('**⚠️ Open Risks & Flagged Issues**')
                    for i, risk in enumerate(result.open_risks_and_flagged_issues, 1):
                        st.write(f"{i}. {risk}")
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.success("✅ No major risks identified")
                
                # Talking points with contrast
                if result.recommended_talking_points:
                    st.markdown('<div class="card" style="border-left: 4px solid #3b82f6;">', unsafe_allow_html=True)
                    st.markdown('**💬 QBR Talking Points**')
                    for i, point in enumerate(result.recommended_talking_points, 1):
                        st.write(f"{i}. {point}")
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.warning("⚠️ No talking points generated")
                
                # Flagged tickets
                if result.flagged_tickets:
                    st.markdown('<div class="card" style="border-left: 4px solid #ef4444;">', unsafe_allow_html=True)
                    st.markdown('**🚩 Flagged Tickets**')
                    for ticket in result.flagged_tickets:
                        with st.expander(f"Ticket: {ticket.ticket_id} ({ticket.urgency})"):
                            st.write(f"**Status:** {ticket.status}")
                            st.write(f"**Created:** {ticket.created_at}")
                            st.write(f"**Reason:** {ticket.reason}")
                            st.write(f"**Quote:** {ticket.quote}")
                    st.markdown('</div>', unsafe_allow_html=True)
                
                st.caption(f'Data based on last {result.data_window_days} days')
                
            except Exception as e:
                st.error(f"Error: {str(e)}")

# About Page
with tab3:
    st.markdown('<div class="sub-header">ℹ️ About</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('**🎯 Overview**')
    st.write('AI-powered support automation for Technical Account Managers')
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('**🚀 Features**')
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('**Ticket Triage**')
        st.write('• Auto-classify tickets')
        st.write('• Match knowledge base')
        st.write('• Assign teams')
        st.write('• Draft responses')
    with col2:
        st.markdown('**Account Briefs**')
        st.write('• Health analysis')
        st.write('• Risk detection')
        st.write('• QBR talking points')
        st.write('• Executive summaries')
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('**⚙️ Technology**')
    st.write('• **LLM**: Groq Llama 3.1 8B')
    st.write('• **RAG**: sentence-transformers')
    st.write('• **Backend**: FastAPI + Pydantic')
    st.write('• **Frontend**: Streamlit')
    st.markdown('</div>', unsafe_allow_html=True)
