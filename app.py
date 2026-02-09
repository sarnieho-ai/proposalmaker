import streamlit as st
import requests

# 1. Page Configuration & Branding
st.set_page_config(
    page_title="DACTA SG | Proposal Architect",
    page_icon="🛡️",
    layout="wide"
)

# Custom CSS for a professional look
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #004a99; color: white; }
    </style>
    """, unsafe_allow_html=True)

# 2. Sidebar - Setup & Instructions
with st.sidebar:
    st.image("https://via.placeholder.com/150x50?text=DACTA+SG", width=150) # Replace with your logo URL
    st.title("Settings")
    make_webhook_url = st.text_input("Make.com Webhook URL", type="password", help="Paste your Custom Webhook URL from Make here.")
    st.divider()
    st.info("Upload the client RFP and reference files. The AI will cross-reference your 'Master' proposals in Google Drive.")

# 3. Main Interface
st.title("🛡️ Proposal Architect")
st.markdown("Generate high-impact, competitive tenders for **MDR, MIS, and DFIR** projects.")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Client Details")
    client_name = st.text_input("Client/Organization Name", placeholder="e.g. SG Bank")
    service_type = st.multiselect(
        "Service Scope", 
        ["Managed Detection & Response (MDR)", "Digital Forensics (DFIR)", "Managed Infrastructure (MIS)", "SOCaaS"],
        default=["MDR"]
    )
    urgency = st.select_slider("Proposal Tone/Urgency", options=["Formal", "Consultative", "Aggressive/Competitive"])

with col2:
    st.subheader("Document Upload")
    rfp_file = st.file_uploader("Upload Client RFP / Requirements", type=["pdf", "docx", "txt"])
    ref_files = st.file_uploader("Additional Partner Specs (Optional)", type=["pdf"], accept_multiple_files=True)

# 4. Trigger Logic
st.divider()
if st.button("🚀 Generate Winning Proposal"):
    if not make_webhook_url:
        st.error("Please enter your Make.com Webhook URL in the sidebar.")
    elif not rfp_file or not client_name:
        st.warning("Client Name and RFP file are required to start.")
    else:
        with st.spinner("Analyzing RFP and referencing DACTA archives..."):
            try:
                # Prepare payload for Make.com
                # Note: For large files, you'd usually upload to GDrive first, 
                # but for now, we're sending the metadata to trigger the workflow.
                payload = {
                    "client": client_name,
                    "services": service_type,
                    "tone": urgency,
                    "filename": rfp_file.name
                }
                
                # Sending the trigger to Make.com
                response = requests.post(make_webhook_url, json=payload)
                
                if response.status_code == 200:
                    st.success(f"Successfully triggered! AI is drafting the proposal for {client_name}.")
                    st.balloons()
                    st.info("The finished Word document will be saved to your DACTA_AI_Reference folder in Google Drive.")
                else:
                    st.error(f"Error: {response.status_code} - Could not reach Make.com.")
            except Exception as e:
                st.error(f"An error occurred: {e}")

# 5. Footer
st.markdown("---")

st.caption("Internal Use Only | DACTA SG Cybersecurity Presales")
