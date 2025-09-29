import streamlit as st
import time
import requests
import json
from PIL import Image

# Set up the page
st.set_page_config(
    page_title="Medical Research Assistant",
    page_icon="🔬",
    layout="wide"
)

# Custom CSS styling
st.markdown("""
<style>
    /* API Documentation styling */
    .api-doc {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    .endpoint {
        color: #2e86c1;
        font-weight: bold;
    }
    /* Main search styling */
    .main-search {
        font-size: 20px !important;
        padding: 15px !important;
        margin-top: 2rem !important;
    }
    /* Talan sidebar styling */
    .talan-header {
        padding: 1.5rem;
        background: linear-gradient(135deg, #2e86c1, #1b4f72);
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
    }
    .talan-logo {
        max-width: 180px;
        margin-bottom: 1rem;
    }
    .sidebar-link {
        color: #2e86c1 !important;
        text-decoration: none;
        font-weight: 500;
    }
    .sidebar-link:hover {
        text-decoration: underline;
    }
    .sidebar-section {
        margin-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# API Configuration (Update these with your endpoints)
SUMMARIZE_API = "http://localhost:5001/summarize"
QA_API = "http://localhost:5000/ask"
PDF_PROCESSING_API = "http://localhost:5000/load_pdf"

# Initialize session states
if "messages" not in st.session_state:
    st.session_state.messages = []
if "analysis_data" not in st.session_state:
    st.session_state.analysis_data = None
if "show_qa" not in st.session_state:
    st.session_state.show_qa = False
if "selected_url" not in st.session_state:
    st.session_state.selected_url = None
if "search_query" not in st.session_state:
    st.session_state.search_query = ""
if "pdf_processed" not in st.session_state:
    st.session_state.pdf_processed = False

# --------------------------------------------
# API Documentation Section in Sidebar
# --------------------------------------------
with st.sidebar:
    # Talan Logo
    try:
        talan_logo = Image.open("talan_tunisie_logo-removebg-preview.png")
        st.image("talan_tunisie_logo-removebg-preview.png", use_column_width=True)
    except FileNotFoundError:
        st.warning("Talan logo image not found")

    # Talan Header
    st.markdown("""
    <div class='talan-header'>
        <h2>TALAN</h2>
        <h4>Positive Innovation</h4>
    </div>
    """, unsafe_allow_html=True)

    # About Section
    st.markdown("""
    ### About Talan
    **Talan Consulting** - Global leader in technology innovation:
    - 🚀 Digital Transformation Experts
    - 🤖 AI & Advanced Analytics
    - 🌍 Sustainable Tech Solutions
    - 🔒 Cybersecurity Specialists
    
    **2023 Achievements:**
    - 📈 €600M Annual Revenue
    - 🌐 5,000+ Professionals
    - 🏆 22 Industry Awards
    
    [🌐 Official Website](https://www.talan.com)
    """)

    # Researcher Section
    st.markdown("""
    ### Research Collaboration
    Partner with Talan Innovation Lab:
    - 🔍 Cutting-edge Tools Access
    - 🤝 Collaborative Projects
    - 📚 Research Grants
    - 📊 Big Data Infrastructure
    
    ✉️ [Contact Research Team](mailto:research@talan.com)
    """)

    st.markdown("---")
    with st.expander("API Documentation 📚"):
        st.markdown("### API Endpoints Guide")
        
        # Summarization API Docs
        st.markdown("### 📝 Summarization API")
        st.markdown("""
        **Endpoint:** `POST /summarize`  
        **Description:** Get summary and relevant papers for a medical term  
        **Parameters:**  
        ```json
        {
            "query": "diabetes treatment"
        }
        ```
        **Example Request:**
        ```python
        import requests
        response = requests.post("http://api-domain.com/summarize", 
            json={"query": "diabetes treatment"})
        ```
        """)
        
        # Q&A API Docs
        st.markdown("### 💬 Q&A API")
        st.markdown("""
        **Endpoint:** `POST /ask`  
        **Description:** Ask questions about a specific paper  
        **Parameters:**  
        ```json
        {
            "pdf_url": "http://example.com/paper.pdf",
            "question": "What are the side effects?"
        }
        ```
        **Example Request:**
        ```python
        response = requests.post("http://api-domain.com/ask", 
            json={
                "pdf_url": "http://example.com/paper.pdf",
                "question": "What are the side effects?"
            })
        ```
        """)
        
        # PDF Processing Docs
        st.markdown("### 📄 PDF Processing API")
        st.markdown("""
        **Endpoint:** `POST /load_pdf`  
        **Description:** Process PDF for Q&A system  
        **Parameters:**  
        ```json
        {
            "pdf_url": "http://example.com/paper.pdf"
        }
        ```
        **Example Request:**
        ```python
        response = requests.post("http://api-domain.com/load_pdf", 
            json={"pdf_url": "http://example.com/paper.pdf"})
        ```
        """)

# --------------------------------------------
# API Integration Functions
# --------------------------------------------
def call_summarize_api(query):
    """Call the summarization API"""
    try:
        response = requests.post(
            SUMMARIZE_API,
            json={"query": query},
            timeout=300
        )
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        st.error(f"API Error: {str(e)}")
        return None

def call_ask_api(pdf_url, question):
    """Call the Q&A API"""
    try:
        response = requests.post(
            QA_API,
            json={
           
                "question": question
            },
            timeout=300
        )
        if response.status_code == 200:
            # Log the API response for debugging
            st.write("API Response:", response.json())
            return response.json()
        else:
            st.error(f"API Error: Status Code {response.status_code}")
            st.write("API Response:", response.text)  # Log the response for debugging
            return None
    except Exception as e:
        st.error(f"API Error: {str(e)}")
        return None

def call_pdf_processing_api(pdf_url):
    """Call the PDF processing API"""
    try:
        response = requests.post(
            PDF_PROCESSING_API,
            json={"pdf_url": pdf_url},
            timeout=300
        )
        if response.status_code == 200:
            return True
        return False
    except Exception as e:
        st.error(f"API Error: {str(e)}")
        return False

# --------------------------------------------
# Main Content Area
# --------------------------------------------
if not st.session_state.analysis_data:
    # Landing Page
    st.title("Medical Research Intelligence Platform")
    st.markdown("""
    **AI-Powered Insights for Healthcare Professionals**  
    Start by searching any medical term below
    """)
    
    # Main Search Bar
    search_query = st.text_input(
        "🔍 Search medical topics (e.g., 'Diabetes Treatment', 'Cancer Immunotherapy')",
        key="landing_search",
        label_visibility="collapsed",
        placeholder="Enter medical term or concept..."
    )
    
    if search_query:
        st.session_state.search_query = search_query
        with st.spinner(f"Analyzing research for '{search_query}'..."):
            # Call Summarization API
            api_response = call_summarize_api(search_query)
            
            if api_response:
                relevant_urls = api_response.get("relevant_urls", [])
                titles = api_response.get("title", [])
            
                # Ensure both lists have the same length
                if len(relevant_urls) != len(titles):
                    st.error("Mismatch between the number of URLs and titles in the API response.")
                    relevant_urls = []  # Reset to avoid errors
                    titles = []
            
                st.session_state.analysis_data = {
                    "topic": search_query,
                    "summary": api_response.get("summarization", ""),
                    "urls": {
                        f"{titles[i]}": {  # Use the title from the titles list
                            "url": relevant_urls[i],  # Use the URL from the relevant_urls list
                            "details": f"Relevant paper from API (Score:0.89 )"
                        }
                        for i in range(len(relevant_urls))  # Iterate over the length of the lists
                    },
                    "qa": {}
                }
            else:
                st.error("Failed to get analysis from API")
            st.rerun()

else:
    # Analysis Page (unless in Q&A)
    if not st.session_state.show_qa:
        # Persistent Search Bar
        new_search = st.text_input(
            "🔍 Search new term or refine query",
            value=st.session_state.search_query,
            key="analysis_search",
            label_visibility="collapsed"
        )
        
        if new_search != st.session_state.search_query:
            st.session_state.search_query = new_search
            st.session_state.analysis_data = None
            st.rerun()
        
        # Analysis Content
        st.header(f"Analysis for '{st.session_state.analysis_data['topic']}'")
        
        # Summary Section
        st.subheader("Executive Summary")
        st.write(st.session_state.analysis_data["summary"])
        
        # Research Papers
        st.subheader("Key Research Papers")
        for name, data in st.session_state.analysis_data["urls"].items():
            with st.expander(f"📄 {name}"):
                st.write(data["details"])
                if st.button(f"Ask Questions about {name}", key=f"btn_{name}"):
                    # Call the PDF processing API
                    pdf_url = data["url"]
                    if call_pdf_processing_api(pdf_url):
                        st.session_state.selected_url = pdf_url
                        st.session_state.show_qa = True
                        st.session_state.pdf_processed = True
                        st.rerun()
                    else:
                        st.error("Failed to process the PDF. Please try again.")

# --------------------------------------------
# Q&A Interface
# --------------------------------------------
# Q&A Interface
if st.session_state.show_qa:
    # Q&A Page
    st.header(f"Research Q&A: {st.session_state.analysis_data['topic']}")
    st.caption(f"Analyzing: {st.session_state.selected_url}")
    
    # Back Navigation
    if st.button("← Back to Analysis"):
        st.session_state.show_qa = False
        st.session_state.messages = []
        st.rerun()
    
    # Chat Interface
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ask a question about this research..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Call Q&A API
        paper_url = st.session_state.selected_url
        qa_response = call_ask_api(paper_url, prompt)
        
        if qa_response:
            # Check if the response contains the "answer" field
            if "answer" in qa_response:
                ai_response = qa_response["answer"]
            else:
                ai_response = "The API response does not contain an answer."
        else:
            ai_response = "Could not retrieve answer from API."
        
        st.session_state.messages.append({"role": "assistant", "content": ai_response})
        st.rerun()