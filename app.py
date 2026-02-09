import streamlit as st
import requests
import json
import base64
from datetime import datetime
from typing import List, Dict, Optional
import time

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="DACTA SG Proposal Architect",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# CUSTOM CSS - CYBERSECURITY AESTHETIC
# ============================================================================

st.markdown("""
<style>
    /* Import professional font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    
    /* Global styling */
    * {
        font-family: 'Inter', sans-serif;
    }
    
    /* Main background - Dark blue gradient */
    .stApp {
        background: linear-gradient(135deg, #0a1929 0%, #1a2332 100%);
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1b2a 0%, #1b263b 100%);
        border-right: 2px solid #00d4ff;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #00d4ff !important;
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    
    /* Input fields */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        background-color: #1e3a52;
        border: 1px solid #2d5f7f;
        color: #e0e7ff;
        border-radius: 8px;
    }
    
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #00d4ff;
        box-shadow: 0 0 10px rgba(0, 212, 255, 0.3);
    }
    
    /* Multiselect */
    .stMultiSelect > div > div {
        background-color: #1e3a52;
        border: 1px solid #2d5f7f;
        border-radius: 8px;
    }
    
    /* File uploader */
    [data-testid="stFileUploader"] {
        background-color: #1e3a52;
        border: 2px dashed #2d5f7f;
        border-radius: 8px;
        padding: 20px;
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(90deg, #00d4ff 0%, #0096c7 100%);
        color: #ffffff;
        font-weight: 600;
        border: none;
        border-radius: 8px;
        padding: 12px 24px;
        box-shadow: 0 4px 15px rgba(0, 212, 255, 0.3);
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        background: linear-gradient(90deg, #00b8e6 0%, #007ea7 100%);
        box-shadow: 0 6px 20px rgba(0, 212, 255, 0.5);
        transform: translateY(-2px);
    }
    
    /* Success/Error messages */
    .stSuccess {
        background-color: #1e4d2b;
        border-left: 4px solid #00ff88;
        color: #00ff88;
        padding: 15px;
        border-radius: 8px;
    }
    
    .stError {
        background-color: #4d1e1e;
        border-left: 4px solid #ff4444;
        color: #ff6b6b;
        padding: 15px;
        border-radius: 8px;
    }
    
    .stWarning {
        background-color: #4d3e1e;
        border-left: 4px solid #ffaa00;
        color: #ffc266;
        padding: 15px;
        border-radius: 8px;
    }
    
    /* Info boxes */
    .stInfo {
        background-color: #1e3a52;
        border-left: 4px solid #00d4ff;
        color: #00d4ff;
        padding: 15px;
        border-radius: 8px;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background-color: #1e3a52;
        border-radius: 8px;
        color: #00d4ff;
        font-weight: 600;
    }
    
    /* Labels */
    label {
        color: #a8c5e0 !important;
        font-weight: 500;
    }
    
    /* Divider */
    hr {
        border-color: #2d5f7f;
        opacity: 0.5;
    }
    
    /* Custom badge */
    .status-badge {
        display: inline-block;
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        margin: 5px 0;
    }
    
    .badge-ready {
        background-color: #1e4d2b;
        color: #00ff88;
        border: 1px solid #00ff88;
    }
    
    .badge-processing {
        background-color: #4d3e1e;
        color: #ffaa00;
        border: 1px solid #ffaa00;
    }
    
    .badge-error {
        background-color: #4d1e1e;
        color: #ff6b6b;
        border: 1px solid #ff6b6b;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def encode_file_to_base64(uploaded_file) -> str:
    """Encode uploaded file to base64 string"""
    try:
        bytes_data = uploaded_file.getvalue()
        return base64.b64encode(bytes_data).decode('utf-8')
    except Exception as e:
        st.error(f"❌ Error encoding file {uploaded_file.name}: {str(e)}")
        return None


def validate_webhook_url(url: str) -> bool:
    """Validate webhook URL format"""
    if not url:
        return False
    if not url.startswith(('http://', 'https://')):
        return False
    if 'make.com' not in url.lower() and 'webhook' not in url.lower():
        st.warning("⚠️ URL doesn't appear to be a Make.com webhook. Please verify.")
    return True


def send_to_make(webhook_url: str, payload: Dict) -> tuple[bool, str]:
    """
    Send payload to Make.com webhook with error handling
    
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        # Validate webhook URL
        if not validate_webhook_url(webhook_url):
            return False, "Invalid webhook URL format"
        
        # Send POST request with timeout
        response = requests.post(
            webhook_url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30  # 30 second timeout
        )
        
        # Check response status
        if response.status_code == 200:
            return True, "Proposal generation initiated successfully!"
        elif response.status_code == 404:
            return False, "Webhook endpoint not found. Please verify the URL."
        elif response.status_code == 500:
            return False, "Make.com server error. Please try again later."
        else:
            return False, f"Unexpected response (Status {response.status_code}): {response.text[:200]}"
    
    except requests.exceptions.Timeout:
        return False, "Request timed out. The webhook may be unreachable."
    except requests.exceptions.ConnectionError:
        return False, "Connection failed. Please check your internet connection and webhook URL."
    except requests.exceptions.RequestException as e:
        return False, f"Request error: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


def validate_inputs(client_name: str, service_types: List[str], 
                    rfp_file, webhook_url: str) -> tuple[bool, str]:
    """
    Validate all required inputs before submission
    
    Returns:
        tuple: (is_valid: bool, error_message: str)
    """
    if not client_name or not client_name.strip():
        return False, "Please enter a client name"
    
    if not service_types or len(service_types) == 0:
        return False, "Please select at least one service type"
    
    if rfp_file is None:
        return False, "Please upload an RFP document"
    
    if not validate_webhook_url(webhook_url):
        return False, "Please enter a valid Make.com webhook URL"
    
    # Validate file type
    allowed_extensions = ['.pdf', '.docx', '.doc']
    file_extension = '.' + rfp_file.name.split('.')[-1].lower()
    if file_extension not in allowed_extensions:
        return False, f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
    
    # Check file size (max 10MB)
    max_size_mb = 10
    file_size_mb = rfp_file.size / (1024 * 1024)
    if file_size_mb > max_size_mb:
        return False, f"RFP file too large ({file_size_mb:.2f}MB). Max size: {max_size_mb}MB"
    
    return True, ""


# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

if 'webhook_url' not in st.session_state:
    st.session_state.webhook_url = ""

if 'submission_count' not in st.session_state:
    st.session_state.submission_count = 0

# ============================================================================
# SIDEBAR - CONFIGURATION
# ============================================================================

with st.sidebar:
    # Logo placeholder
    st.markdown("""
        <div style='text-align: center; padding: 20px 0;'>
            <h1 style='font-size: 48px; margin: 0;'>🛡️</h1>
            <h3 style='color: #00d4ff; margin: 10px 0;'>DACTA SG</h3>
            <p style='color: #a8c5e0; font-size: 12px; margin: 0;'>Proposal Architect</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Webhook URL Configuration
    st.markdown("### ⚙️ Configuration")
    
    webhook_url = st.text_input(
        "Make.com Webhook URL",
        value=st.session_state.webhook_url,
        type="password",
        placeholder="https://hook.make.com/...",
        help="Enter your Make.com webhook URL. This is required to trigger the AI workflow."
    )
    
    # Save to session state
    if webhook_url:
        st.session_state.webhook_url = webhook_url
    
    # Connection status indicator
    if webhook_url and validate_webhook_url(webhook_url):
        st.markdown('<div class="status-badge badge-ready">✓ Webhook Configured</div>', 
                   unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-badge badge-error">✗ Webhook Not Set</div>', 
                   unsafe_allow_html=True)
    
    st.markdown("---")
    
    # System info
    with st.expander("📊 System Information"):
        st.markdown(f"""
        **Version:** 1.0.0  
        **Last Updated:** {datetime.now().strftime('%Y-%m-%d')}  
        **Submissions:** {st.session_state.submission_count}
        
        **AI Engines:**
        - 🔍 Gemini 1.5 Pro (Analysis)
        - 🌐 Perplexity (Research)
        - ✍️ Claude 3.5 Sonnet (Drafting)
        """)
    
    # Help section
    with st.expander("❓ Need Help?"):
        st.markdown("""
        **Setup Steps:**
        1. Configure your Make.com webhook URL above
        2. Upload the RFP document
        3. Select service types
        4. Add reference materials (optional)
        5. Click "Generate Proposal"
        
        **Supported Files:**
        - RFP: PDF, DOCX (Max 10MB)
        - Reference: PDF, DOCX, TXT
        """)

# ============================================================================
# MAIN DASHBOARD
# ============================================================================

# Header
st.markdown("""
    <div style='text-align: center; padding: 20px 0;'>
        <h1>🛡️ DACTA SG Proposal Architect</h1>
        <p style='color: #a8c5e0; font-size: 16px;'>
            AI-Powered Proposal Generation System
        </p>
    </div>
""", unsafe_allow_html=True)

st.markdown("---")

# Create two columns for better layout
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("### 📝 Proposal Details")
    
    # Client Name
    client_name = st.text_input(
        "Client Name *",
        placeholder="e.g., Singapore Power, DBS Bank, MINDEF",
        help="Enter the full name of the client organization"
    )
    
    # Service Type Multi-Select - UPDATED OPTIONS
    service_types = st.multiselect(
        "Service Type(s) *",
        options=["Security Operations", "Cybersecurity Engineering", "Consulting"],
        default=[],
        help="Select one or more security services to include in the proposal"
    )
    
    # Display selected services as badges
    if service_types:
        st.markdown("**Selected Services:**")
        badges_html = ""
        for service in service_types:
            badges_html += f'<span class="status-badge badge-ready">{service}</span> '
        st.markdown(badges_html, unsafe_allow_html=True)

with col2:
    st.markdown("### 📊 Quick Stats")
    
    # Status indicators
    indicators = {
        "Client": "✓" if client_name else "✗",
        "Services": "✓" if service_types else "✗",
        "Webhook": "✓" if st.session_state.webhook_url else "✗"
    }
    
    for item, status in indicators.items():
        color = "#00ff88" if status == "✓" else "#ff6b6b"
        st.markdown(f"**{item}:** <span style='color: {color};'>{status}</span>", 
                   unsafe_allow_html=True)

st.markdown("---")

# File Upload Section
st.markdown("### 📤 Document Upload")

upload_col1, upload_col2 = st.columns(2)

with upload_col1:
    # RFP Upload (Required)
    rfp_file = st.file_uploader(
        "RFP Document *",
        type=['pdf', 'docx', 'doc'],
        help="Upload the Request for Proposal document (PDF or DOCX, max 10MB)",
        key="rfp_uploader"
    )
    
    if rfp_file:
        file_size = rfp_file.size / 1024  # KB
        st.success(f"✓ Uploaded: {rfp_file.name} ({file_size:.1f} KB)")

with upload_col2:
    # Reference Documents Upload (Optional)
    reference_files = st.file_uploader(
        "Reference Materials (Optional)",
        type=['pdf', 'docx', 'doc', 'txt'],
        accept_multiple_files=True,
        help="Upload partner specs, past proposals, or other reference documents",
        key="reference_uploader"
    )
    
    if reference_files:
        st.success(f"✓ {len(reference_files)} file(s) uploaded")
        with st.expander("View uploaded references"):
            for ref_file in reference_files:
                st.markdown(f"- {ref_file.name}")

st.markdown("---")

# Additional Options
with st.expander("⚙️ Advanced Options"):
    include_pricing = st.checkbox("Include Pricing Section", value=True)
    include_timeline = st.checkbox("Include Project Timeline", value=True)
    tone_preference = st.selectbox(
        "Proposal Tone",
        options=["Professional", "Technical", "Executive-Friendly"],
        index=0
    )
    
    additional_notes = st.text_area(
        "Additional Instructions",
        placeholder="Any specific requirements or notes for the AI...",
        height=100
    )

st.markdown("---")

# Generate Button
st.markdown("### 🚀 Generate Proposal")

generate_col1, generate_col2, generate_col3 = st.columns([1, 2, 1])

with generate_col2:
    generate_button = st.button(
        "🛡️ Generate Proposal",
        use_container_width=True,
        type="primary"
    )

# Handle submission
if generate_button:
    # Validate inputs
    is_valid, error_message = validate_inputs(
        client_name, 
        service_types, 
        rfp_file, 
        st.session_state.webhook_url
    )
    
    if not is_valid:
        st.error(f"❌ {error_message}")
    else:
        # Show processing status
        with st.spinner("🔄 Preparing payload and connecting to Make.com..."):
            # Encode RFP file
            rfp_base64 = encode_file_to_base64(rfp_file)
            
            if rfp_base64 is None:
                st.error("❌ Failed to encode RFP file. Please try again.")
            else:
                # Encode reference files (if any)
                reference_data = []
                if reference_files:
                    for ref_file in reference_files:
                        ref_base64 = encode_file_to_base64(ref_file)
                        if ref_base64:
                            reference_data.append({
                                "filename": ref_file.name,
                                "content": ref_base64,
                                "size": ref_file.size
                            })
                
                # Construct payload
                payload = {
                    "client_name": client_name.strip(),
                    "service_types": service_types,
                    "rfp_document": {
                        "filename": rfp_file.name,
                        "content": rfp_base64,
                        "size": rfp_file.size,
                        "type": rfp_file.type
                    },
                    "reference_documents": reference_data,
                    "options": {
                        "include_pricing": include_pricing,
                        "include_timeline": include_timeline,
                        "tone": tone_preference,
                        "additional_notes": additional_notes
                    },
                    "metadata": {
                        "timestamp": datetime.now().isoformat(),
                        "submission_id": f"DACTA-{int(time.time())}",
                        "version": "1.0.0"
                    }
                }
                
                # Send to Make.com
                success, message = send_to_make(st.session_state.webhook_url, payload)
                
                if success:
                    st.success(f"✅ {message}")
                    st.balloons()
                    
                    # Update submission count
                    st.session_state.submission_count += 1
                    
                    # Show next steps
                    st.info("""
                    **Next Steps:**
                    1. ✓ Payload sent to Make.com
                    2. ⏳ AI workflow processing (3-5 minutes)
                    3. 📧 You'll receive the proposal via email
                    4. 📁 Document saved to Google Drive
                    
                    **Submission ID:** `{}`
                    """.format(payload["metadata"]["submission_id"]))
                    
                else:
                    st.error(f"❌ Failed to send proposal request")
                    st.error(f"**Error Details:** {message}")
                    
                    # Show troubleshooting tips
                    with st.expander("🔧 Troubleshooting"):
                        st.markdown("""
                        **Common Issues:**
                        
                        1. **Invalid Webhook URL**
                           - Verify the URL is copied correctly from Make.com
                           - Ensure the webhook scenario is active
                        
                        2. **Connection Timeout**
                           - Check your internet connection
                           - Try again in a few moments
                        
                        3. **Make.com Server Error**
                           - The Make.com scenario may have an error
                           - Check your Make.com dashboard for logs
                        
                        **Need Help?**
                        Contact your system administrator or DACTA IT support.
                        """)

# Footer
st.markdown("---")
st.markdown("""
    <div style='text-align: center; padding: 20px; color: #6b8ca8;'>
        <p style='font-size: 12px;'>
            © 2025 DACTA SG | Proposal Architect v1.0.0<br>
            Powered by AI: Gemini + Perplexity + Claude
        </p>
    </div>
""", unsafe_allow_html=True)
