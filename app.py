import streamlit as st
import requests
import base64
import time
from datetime import datetime
from typing import List, Dict
from supabase import create_client, Client

# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="DACTA SG Proposal Architect",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# SECRETS — ALL LOADED FROM STREAMLIT CLOUD
# ============================================================

MAKE_WEBHOOK_URL   = st.secrets["MAKE_WEBHOOK_URL"]
SUPABASE_URL       = st.secrets["SUPABASE_URL"]
SUPABASE_ANON_KEY  = st.secrets["SUPABASE_ANON_KEY"]

# ============================================================
# SUPABASE CLIENT
# ============================================================

@st.cache_resource
def init_supabase() -> Client:
    """Initialize Supabase client — cached for performance"""
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

supabase: Client = init_supabase()

# ============================================================
# CUSTOM CSS — CYBERSECURITY AESTHETIC
# ============================================================

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');

    * { font-family: 'Inter', sans-serif; }

    .stApp {
        background: linear-gradient(135deg, #0a1929 0%, #1a2332 100%);
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1b2a 0%, #1b263b 100%);
        border-right: 2px solid #00d4ff;
    }

    h1, h2, h3 {
        color: #00d4ff !important;
        font-weight: 700;
        letter-spacing: -0.5px;
    }

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

    .stMultiSelect > div > div {
        background-color: #1e3a52;
        border: 1px solid #2d5f7f;
        border-radius: 8px;
    }

    [data-testid="stFileUploader"] {
        background-color: #1e3a52;
        border: 2px dashed #2d5f7f;
        border-radius: 8px;
        padding: 20px;
    }

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

    label { color: #a8c5e0 !important; font-weight: 500; }
    hr { border-color: #2d5f7f; opacity: 0.5; }

    .status-badge {
        display: inline-block;
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        margin: 4px 2px;
    }
    .badge-ready      { background-color: #1e4d2b; color: #00ff88; border: 1px solid #00ff88; }
    .badge-processing { background-color: #4d3e1e; color: #ffaa00; border: 1px solid #ffaa00; }
    .badge-error      { background-color: #4d1e1e; color: #ff6b6b; border: 1px solid #ff6b6b; }
    .badge-info       { background-color: #1e3a52; color: #00d4ff; border: 1px solid #00d4ff; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def encode_file_to_base64(uploaded_file) -> str | None:
    """Encode an uploaded file to a base64 string"""
    try:
        return base64.b64encode(uploaded_file.getvalue()).decode("utf-8")
    except Exception as e:
        st.error(f"❌ Error encoding {uploaded_file.name}: {str(e)}")
        return None


def validate_inputs(
    client_name: str,
    service_types: List[str],
    rfp_file
) -> tuple[bool, str]:
    """Validate all required form inputs before submission"""

    if not client_name or not client_name.strip():
        return False, "Please enter a client name."

    if not service_types:
        return False, "Please select at least one service type."

    if rfp_file is None:
        return False, "Please upload an RFP document."

    allowed = [".pdf", ".docx", ".doc"]
    ext = "." + rfp_file.name.rsplit(".", 1)[-1].lower()
    if ext not in allowed:
        return False, f"Invalid file type '{ext}'. Allowed: {', '.join(allowed)}"

    size_mb = rfp_file.size / (1024 * 1024)
    if size_mb > 10:
        return False, f"RFP file is {size_mb:.1f}MB — maximum allowed is 10MB."

    return True, ""


def log_submission_to_supabase(payload: Dict) -> tuple[bool, str]:
    """
    Insert initial proposal record into Supabase when submission begins.
    Returns (success, record_id_or_error_message)
    """
    try:
        data = {
            "submission_id":    payload["metadata"]["submission_id"],
            "client_name":      payload["client_name"],
            "service_types":    payload["service_types"],
            "status":           "processing",
            "rfp_filename":     payload["rfp_document"]["filename"],
            "tone":             payload["options"]["tone"],
            "include_pricing":  payload["options"]["include_pricing"],
            "include_timeline": payload["options"]["include_timeline"],
            "additional_notes": payload["options"]["additional_notes"],
        }

        response = (
            supabase.table("proposals")
            .insert(data)
            .execute()
        )

        if response.data:
            record_id = response.data[0]["id"]
            return True, record_id
        else:
            return False, "Supabase returned no data on insert."

    except Exception as e:
        return False, f"Supabase insert error: {str(e)}"


def log_reference_docs_to_supabase(
    proposal_id: str,
    reference_files: list
) -> None:
    """
    Insert reference document records linked to the proposal.
    Fails silently — reference docs are optional.
    """
    if not reference_files:
        return

    try:
        rows = [
            {
                "proposal_id": proposal_id,
                "filename":    f.name,
                "file_size":   f.size,
            }
            for f in reference_files
        ]
        supabase.table("reference_docs").insert(rows).execute()

    except Exception as e:
        # Non-critical — log as warning, don't block submission
        st.warning(f"⚠️ Reference docs logged with issue: {str(e)}")


def update_supabase_status(
    submission_id: str,
    status: str,
    extra_fields: Dict = None
) -> None:
    """Update proposal status in Supabase after webhook response"""
    try:
        update_data = {"status": status}
        if extra_fields:
            update_data.update(extra_fields)

        supabase.table("proposals") \
            .update(update_data) \
            .eq("submission_id", submission_id) \
            .execute()

    except Exception as e:
        st.warning(f"⚠️ Could not update Supabase status: {str(e)}")


def send_to_make(payload: Dict) -> tuple[bool, str, Dict]:
    """
    Send payload to Make.com webhook.
    Returns (success, message, response_data)
    """
    try:
        response = requests.post(
            MAKE_WEBHOOK_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60
        )

        if response.status_code == 200:
            try:
                response_data = response.json()
            except Exception:
                response_data = {}
            return True, "Proposal generation initiated successfully.", response_data

        elif response.status_code == 404:
            return False, "Webhook endpoint not found. Verify the URL in Streamlit secrets.", {}
        elif response.status_code == 429:
            return False, "Rate limit reached on Make.com. Please wait a moment and retry.", {}
        elif response.status_code == 500:
            return False, "Make.com server error. Check your scenario for configuration issues.", {}
        else:
            return False, f"Unexpected response (HTTP {response.status_code}): {response.text[:300]}", {}

    except requests.exceptions.Timeout:
        return False, "Request timed out after 60 seconds. Make.com may be unreachable.", {}
    except requests.exceptions.ConnectionError:
        return False, "Connection failed. Check your internet connection.", {}
    except requests.exceptions.RequestException as e:
        return False, f"Request error: {str(e)}", {}
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", {}


# ============================================================
# SESSION STATE
# ============================================================

if "submission_count" not in st.session_state:
    st.session_state.submission_count = 0

if "last_submission_id" not in st.session_state:
    st.session_state.last_submission_id = None

# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.markdown("""
        <div style='text-align:center; padding: 24px 0 16px 0;'>
            <div style='font-size:52px;'>🛡️</div>
            <h3 style='color:#00d4ff; margin:10px 0 4px 0;'>DACTA SG</h3>
            <p style='color:#a8c5e0; font-size:12px; margin:0;'>Proposal Architect</p>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # System status — derived from secrets, no user input needed
    st.markdown("### 🟢 System Status")

    checks = {
        "Webhook":  bool(MAKE_WEBHOOK_URL),
        "Database": bool(SUPABASE_URL and SUPABASE_ANON_KEY),
    }

    for label, ok in checks.items():
        badge = "badge-ready" if ok else "badge-error"
        icon  = "✓" if ok else "✗"
        st.markdown(
            f'<span class="status-badge {badge}">{icon} {label}</span>',
            unsafe_allow_html=True
        )

    st.markdown("---")

    # AI pipeline display
    st.markdown("### 🤖 AI Pipeline")
    pipeline = [
        ("🔍", "Gemini 1.5 Pro",    "Requirements Extraction"),
        ("🧠", "DeepSeek",          "Gap Analysis"),
        ("🌐", "Perplexity",        "Market Research"),
        ("✍️", "Claude 3.5 Sonnet", "Proposal Drafting"),
    ]
    for icon, name, role in pipeline:
        st.markdown(
            f"{icon} **{name}**  \n"
            f"<span style='color:#6b8ca8; font-size:12px;'>{role}</span>",
            unsafe_allow_html=True
        )

    st.markdown("---")

    with st.expander("📊 Session Stats"):
        st.markdown(f"""
        **Submissions this session:** {st.session_state.submission_count}  
        **Last ID:** `{st.session_state.last_submission_id or 'None'}`  
        **Date:** {datetime.now().strftime('%d %b %Y')}
        """)

    with st.expander("❓ Help"):
        st.markdown("""
        **Steps:**
        1. Enter client name
        2. Select services
        3. Upload RFP document
        4. Add reference files *(optional)*
        5. Configure options
        6. Click **Generate Proposal**

        **Supported formats:**
        - RFP: PDF, DOCX (max 10MB)
        - References: PDF, DOCX, TXT
        """)

# ============================================================
# MAIN DASHBOARD
# ============================================================

st.markdown("""
    <div style='text-align:center; padding:24px 0 8px 0;'>
        <h1>🛡️ DACTA SG Proposal Architect</h1>
        <p style='color:#a8c5e0; font-size:15px; margin-top:4px;'>
            AI-Powered Proposal Generation — Gemini · DeepSeek · Perplexity · Claude
        </p>
    </div>
""", unsafe_allow_html=True)

st.markdown("---")

# ── SECTION 1: Proposal Details ──────────────────────────────
st.markdown("### 📝 Proposal Details")

col1, col2 = st.columns([2, 1])

with col1:
    client_name = st.text_input(
        "Client Name *",
        placeholder="e.g., Singapore Power, DBS Bank, MINDEF",
        help="Full name of the client organization"
    )

    service_types = st.multiselect(
        "Service Type(s) *",
        options=[
            "Security Operations",
            "Cybersecurity Engineering",
            "Consulting"
        ],
        default=[],
        help="Select all services to include in this proposal"
    )

    if service_types:
        badges = "".join(
            f'<span class="status-badge badge-info">{s}</span>'
            for s in service_types
        )
        st.markdown(badges, unsafe_allow_html=True)

with col2:
    st.markdown("### ✅ Readiness")
    checks = {
        "Client Name": bool(client_name),
        "Services":    bool(service_types),
    }
    for label, ok in checks.items():
        color = "#00ff88" if ok else "#ff6b6b"
        mark  = "✓" if ok else "✗"
        st.markdown(
            f"**{label}:** <span style='color:{color};'>{mark}</span>",
            unsafe_allow_html=True
        )

st.markdown("---")

# ── SECTION 2: Document Upload ───────────────────────────────
st.markdown("### 📤 Document Upload")

up_col1, up_col2 = st.columns(2)

with up_col1:
    rfp_file = st.file_uploader(
        "RFP Document *",
        type=["pdf", "docx", "doc"],
        help="Request for Proposal — PDF or DOCX, max 10MB",
        key="rfp_uploader"
    )
    if rfp_file:
        st.success(f"✓ {rfp_file.name} ({rfp_file.size / 1024:.1f} KB)")

with up_col2:
    reference_files = st.file_uploader(
        "Reference Materials (Optional)",
        type=["pdf", "docx", "doc", "txt"],
        accept_multiple_files=True,
        help="Partner specs, past proposals, compliance docs",
        key="reference_uploader"
    )
    if reference_files:
        st.success(f"✓ {len(reference_files)} reference file(s) attached")
        with st.expander("View files"):
            for f in reference_files:
                st.markdown(f"- `{f.name}` ({f.size / 1024:.1f} KB)")

st.markdown("---")

# ── SECTION 3: Advanced Options ──────────────────────────────
with st.expander("⚙️ Proposal Options"):
    opt_col1, opt_col2 = st.columns(2)

    with opt_col1:
        include_pricing  = st.checkbox("Include Pricing Section",   value=True)
        include_timeline = st.checkbox("Include Project Timeline",  value=True)

    with opt_col2:
        tone_preference = st.selectbox(
            "Proposal Tone",
            options=["Professional", "Technical", "Executive-Friendly"],
            index=0
        )

    additional_notes = st.text_area(
        "Additional Instructions for the AI",
        placeholder="e.g., emphasize OT/ICS experience, reference MAS TRM compliance, avoid mentioning competitors by name...",
        height=100
    )

st.markdown("---")

# ── SECTION 4: Generate ──────────────────────────────────────
st.markdown("### 🚀 Generate Proposal")

_, btn_col, _ = st.columns([1, 2, 1])

with btn_col:
    generate_button = st.button(
        "🛡️ Generate Proposal",
        use_container_width=True,
        type="primary"
    )

# ============================================================
# SUBMISSION HANDLER
# ============================================================

if generate_button:

    is_valid, error_msg = validate_inputs(client_name, service_types, rfp_file)

    if not is_valid:
        st.error(f"❌ {error_msg}")

    else:
        submission_id = f"DACTA-{int(time.time())}"

        # ── Step 1: Encode Files ──────────────────────────────
        with st.status("⚙️ Processing submission...", expanded=True) as status_box:

            st.write("📎 Encoding RFP document...")
            rfp_base64 = encode_file_to_base64(rfp_file)

            if rfp_base64 is None:
                status_box.update(label="❌ File encoding failed", state="error")
                st.stop()

            # Encode reference files
            reference_data = []
            if reference_files:
                st.write(f"📎 Encoding {len(reference_files)} reference file(s)...")
                for ref in reference_files:
                    ref_b64 = encode_file_to_base64(ref)
                    if ref_b64:
                        reference_data.append({
                            "filename": ref.name,
                            "content":  ref_b64,
                            "size":     ref.size
                        })

            # ── Step 2: Build Payload ─────────────────────────
            payload = {
                "client_name":   client_name.strip(),
                "service_types": service_types,
                "rfp_document": {
                    "filename": rfp_file.name,
                    "content":  rfp_base64,
                    "size":     rfp_file.size,
                    "type":     rfp_file.type
                },
                "reference_documents": reference_data,
                "options": {
                    "include_pricing":  include_pricing,
                    "include_timeline": include_timeline,
                    "tone":             tone_preference,
                    "additional_notes": additional_notes or ""
                },
                "metadata": {
                    "submission_id": submission_id,
                    "timestamp":     datetime.now().isoformat(),
                    "version":       "1.0.0"
                }
            }

            # ── Step 3: Log to Supabase ───────────────────────
            st.write("🗄️ Logging submission to Supabase...")
            sb_ok, sb_result = log_submission_to_supabase(payload)

            if sb_ok:
                st.write(f"✓ Supabase record created → `{sb_result}`")
                # Log reference docs linked to proposal ID
                log_reference_docs_to_supabase(sb_result, reference_files)
            else:
                # Non-critical — warn but don't block
                st.warning(f"⚠️ Supabase logging issue: {sb_result}")

            # ── Step 4: Send to Make.com ──────────────────────
            st.write("🔗 Sending to Make.com workflow...")
            success, message, response_data = send_to_make(payload)

            if success:
                # Update Supabase status to reflect webhook receipt
                update_supabase_status(
                    submission_id,
                    status="draft_ready" if response_data else "processing"
                )
                status_box.update(
                    label="✅ Proposal generation triggered successfully!",
                    state="complete"
                )

            else:
                # Mark as failed in Supabase
                update_supabase_status(submission_id, status="failed")
                status_box.update(
                    label="❌ Submission failed — see details below",
                    state="error"
                )

        # ── Post-submission UI ────────────────────────────────
        if success:
            st.success("✅ Your proposal request has been submitted!")
            st.balloons()

            st.session_state.submission_count += 1
            st.session_state.last_submission_id = submission_id

            st.info(f"""
            **Submission Confirmed**

            | Field | Value |
            |---|---|
            | **Submission ID** | `{submission_id}` |
            | **Client** | {client_name} |
            | **Services** | {', '.join(service_types)} |
            | **RFP File** | {rfp_file.name} |
            | **Timestamp** | {datetime.now().strftime('%d %b %Y %H:%M SGT')} |

            **What happens next:**
            1. ✅ Payload received by Make.com
            2. ⏳ Gemini extracts RFP requirements
            3. ⏳ DeepSeek performs gap analysis
            4. ⏳ Perplexity researches market data
            5. ⏳ Claude drafts the final proposal
            6. 📁 Output saved to Supabase
            7. 📧 You'll be notified when the draft is ready *(~3–5 minutes)*
            """)

        else:
            st.error("❌ Failed to trigger the Make.com workflow.")
            st.error(f"**Reason:** {message}")

            with st.expander("🔧 Troubleshooting Guide"):
                st.markdown("""
                **1. Webhook URL Invalid**
                - Go to Streamlit Cloud → Settings → Secrets
                - Verify `MAKE_WEBHOOK_URL` is correct and has no trailing spaces

                **2. Make.com Scenario Inactive**
                - Log into Make.com
                - Ensure your scenario is **turned ON** (toggle in bottom-left)
                - Check the scenario has no errors in the last execution log

                **3. Connection Timeout**
                - The request timed out after 60 seconds
                - Check Make.com's status page for outages

                **4. Supabase Issues**
                - Verify `SUPABASE_URL` and `SUPABASE_ANON_KEY` in secrets
                - Confirm the `proposals` table exists and RLS is configured

                **Still stuck?** Share the Submission ID with your admin:
                `{}`
                """.format(submission_id))

# ============================================================
# FOOTER
# ============================================================

st.markdown("---")
st.markdown("""
    <div style='text-align:center; padding:16px; color:#6b8ca8;'>
        <p style='font-size:12px; margin:0;'>
            © 2025 DACTA SG · Proposal Architect v1.0.0<br>
            Gemini · DeepSeek · Perplexity · Claude
        </p>
    </div>
""", unsafe_allow_html=True)
