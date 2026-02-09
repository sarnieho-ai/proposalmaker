# 🛡️ DACTA SG Proposal Architect

Internal presales automation tool designed to generate competitive proposals using **Gemini**, **Claude**, and **Perplexity**.

## 🚀 Quick Start
1. **Clone the repo:** `git clone https://github.com/your-username/dacta-proposal-app.git`
2. **Install dependencies:** `pip install -r requirements.txt`
3. **Run the app:** `streamlit run app.py`

## 🛠️ How it Works
1. **Input:** Upload an RFP/RFI document.
2. **Process:** Streamlit triggers a **Make.com** webhook.
3. **AI Logic:** - **Perplexity** researches latest partner specs.
   - **Gemini** analyzes the RFP vs. DACTA's historical wins in Google Drive.
   - **Claude** drafts the final content into a branded Word template.
4. **Output:** A finalized `.docx` is saved to the DACTA Google Drive.

## 🔑 Configuration
Paste your **Make.com Webhook URL** into the sidebar of the app to enable the AI engine.