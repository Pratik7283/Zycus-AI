"""
Streamlit UI Demo for Zycus AI Project
A user-friendly interface for non-technical TAMs to use Task 1 and Task 2 functionality.
"""

import streamlit as st
from pathlib import Path
import sys
import json

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from task1.service import triage_ticket
from task2.service import generate_account_brief

# Page configuration
st.set_page_config(
    page_title="Zycus AI Support Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        font-weight: 600;
        color: #2c3e50;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
    }
    .info-box {
        background-color: #e8f4f8;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
        margin: 1rem 0;
    }
    .success-box {
        background-color: #d4edda;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #28a745;
        margin: 1rem 0;
    }
    .warning-box {
        background-color: #fff3cd;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #ffc107;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Main header
st.markdown('<div class="main-header">🤖 Zycus AI Support Assistant</div>', unsafe_allow_html=True)

st.markdown("""
This tool helps Technical Account Managers (TAMs) with two key tasks:
- **Ticket Triage**: Automatically classify and prioritize support tickets
- **Account Briefs**: Generate comprehensive account health summaries for QBR meetings
""")

# Sidebar for navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Select Tool", ["Ticket Triage", "Account Brief", "About"])

# Ticket Triage Page
if page == "Ticket Triage":
    st.markdown('<div class="sub-header">📋 Ticket Triage</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="info-box">
    <strong>What this does:</strong> Automatically classifies support tickets by product area, 
    issue category, and urgency. It also matches tickets to knowledge base articles and suggests 
    appropriate response teams.
    </div>
    """, unsafe_allow_html=True)
    
    # Input form
    with st.form("ticket_form"):
        col1, col2 = st.columns(2)
        with col1:
            subject = st.text_input("Ticket Subject", placeholder="e.g., Cannot export report")
        with col2:
            body = st.text_area("Ticket Body", placeholder="Describe the issue in detail...", height=150)
        
        submit_button = st.form_submit_button("Analyze Ticket", type="primary")
    
    if submit_button:
        if not subject and not body:
            st.error("Please provide either a subject or body for the ticket.")
        else:
            with st.spinner("Analyzing ticket..."):
                try:
                    # Call triage service
                    result = triage_ticket({"subject": subject, "body": body})
                    
                    # Display results
                    st.markdown('<div class="success-box"><strong>✅ Analysis Complete</strong></div>', unsafe_allow_html=True)
                    
                    # Classification results
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Product Area", result.product_area)
                    with col2:
                        st.metric("Issue Category", result.issue_category)
                    with col3:
                        st.metric("Urgency Tier", result.urgency_tier)
                    
                    # Recommended team
                    st.info(f"🎯 **Recommended Team:** {result.recommended_team}")
                    
                    # Knowledge base match
                    if result.known_issue_match:
                        st.success(f"📚 **Knowledge Base Match:** {result.matched_kb_doc}")
                        with st.expander("View Matched Article Excerpt"):
                            st.write(result.matched_kb_excerpt)
                    else:
                        st.warning("⚠️ No strong knowledge base match found")
                    
                    # Draft response
                    st.subheader("📝 Suggested Response")
                    st.write(result.draft_first_response)
                    
                    # Reasoning
                    with st.expander("View Analysis Reasoning"):
                        for reason in result.reasoning:
                            st.write(f"• {reason}")
                    
                    # Confidence
                    st.caption(f"Confidence Score: {result.confidence:.0%}")
                    
                except Exception as e:
                    st.error(f"Error analyzing ticket: {str(e)}")

# Account Brief Page
elif page == "Account Brief":
    st.markdown('<div class="sub-header">📊 Account Brief Generator</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="info-box">
    <strong>What this does:</strong> Generates comprehensive account health summaries for QBR meetings, 
    including executive summaries, risk analysis, and talking points based on recent ticket activity.
    </div>
    """, unsafe_allow_html=True)
    
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
        
        submit_button = st.form_submit_button("Generate Account Brief", type="primary")
    
    if submit_button:
        with st.spinner("Generating account brief..."):
            try:
                # Call account brief service
                result = generate_account_brief({"account_id": selected_account})
                
                # Display results
                st.markdown('<div class="success-box"><strong>✅ Account Brief Generated</strong></div>', unsafe_allow_html=True)
                
                # Account overview
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Company", result.company)
                with col2:
                    st.metric("TAM", result.tam)
                with col3:
                    st.metric("Health Status", result.health_status)
                with col4:
                    st.metric("Usage Trend", result.usage_trend)
                
                # Executive summary
                st.subheader("📋 Executive Summary")
                st.write(result.executive_summary)
                
                # Open risks and flagged issues
                st.subheader("⚠️ Open Risks & Flagged Issues")
                if result.open_risks_and_flagged_issues:
                    for i, risk in enumerate(result.open_risks_and_flagged_issues, 1):
                        st.write(f"{i}. {risk}")
                else:
                    st.info("No major risks identified")
                
                # Talking points
                st.subheader("💬 Recommended Talking Points for QBR")
                if result.recommended_talking_points:
                    for i, point in enumerate(result.recommended_talking_points, 1):
                        st.write(f"{i}. {point}")
                else:
                    st.warning("No talking points generated")
                
                # Flagged tickets
                if result.flagged_tickets:
                    st.subheader("🚩 Flagged Tickets")
                    for ticket in result.flagged_tickets:
                        with st.expander(f"Ticket: {ticket.ticket_id} ({ticket.urgency})"):
                            st.write(f"**Status:** {ticket.status}")
                            st.write(f"**Created:** {ticket.created_at}")
                            st.write(f"**Reason:** {ticket.reason}")
                            st.write(f"**Quote:** {ticket.quote}")
                
                # Data window
                st.caption(f"Data based on last {result.data_window_days} days of activity")
                
            except Exception as e:
                st.error(f"Error generating account brief: {str(e)}")

# About Page
elif page == "About":
    st.markdown('<div class="sub-header">ℹ️ About This Tool</div>', unsafe_allow_html=True)
    
    st.markdown("""
    ## Overview
    
    This is a demonstration UI for the Zycus AI Project, which implements intelligent support automation using:
    
    - **LLM Classification**: Using Groq's Llama 3.1 model for intelligent text analysis
    - **RAG Pipeline**: Semantic search with sentence-transformers for knowledge base matching
    - **Prompt Chaining**: Multi-step LLM workflows for complex reasoning tasks
    
    ## Features
    
    ### Ticket Triage (Task 1)
    - Automatic classification of support tickets
    - Product area, issue category, and urgency detection
    - Knowledge base article matching
    - Team assignment recommendations
    - Draft response generation
    
    ### Account Briefs (Task 2)
    - Account health analysis
    - Risk detection from ticket patterns
    - Executive summary generation
    - QBR talking point suggestions
    - Flagged ticket identification
    
    ## Technical Details
    
    - **Backend**: FastAPI with Pydantic for data validation
    - **AI Models**: sentence-transformers (all-MiniLM-L6-v2) for embeddings
    - **LLM**: Groq API with Llama 3.1 8B Instant
    - **Frontend**: Streamlit for user-friendly interface
    
    ## Usage Tips
    
    1. **Ticket Triage**: Provide clear, detailed ticket descriptions for better classification
    2. **Account Briefs**: Select accounts from the dropdown to see comprehensive analysis
    3. **Results**: Review the reasoning and confidence scores to understand AI decisions
    
    ## Support
    
    For technical issues or questions, please refer to the project documentation or contact the development team.
    """)

# Footer
st.markdown("---")
st.caption("Zycus AI Project - Technical Account Manager Support Assistant | Built with Streamlit")
