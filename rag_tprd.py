#Run this in terminal
#cd "C:\Users\Pamela Bayona\Desktop\Work\DSTI\Python"

#WTO API key sk-55e07c5dd0654c5388f20138395a9f30

#pip install python-docx
#pip install openai==0.28

import streamlit as st
import openai
import pdfplumber
from PyPDF2 import PdfReader  # For PDF file extraction
from docx import Document  # For Word file extraction
import requests
from bs4 import BeautifulSoup
import concurrent.futures

# Function to extract text from an uploaded PDF file
def extract_text_from_pdf(uploaded_file):
    text = ""
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
    except Exception:
        reader = PdfReader(uploaded_file)
        for page in reader.pages:
            text += page.extract_text() or ""
    return text.strip()

# Function to extract text from an uploaded Word file
def extract_text_from_docx(uploaded_file):
    doc = Document(uploaded_file)
    text = "\n".join([para.text for para in doc.paragraphs])
    return text.strip()

# Function to extract text from a URL
def extract_text_from_url(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        paragraphs = soup.find_all("p")
        text = "\n".join([para.get_text() for para in paragraphs])
        return text.strip()
    except Exception as e:
        return f"Error retrieving content from URL: {e}"

# Function to retrieve relevant information for answering trade policy questions
def retrieve_relevant_information(topic, sources):
    relevant_snippets = []
    for source in sources:
        if topic.lower() in source["content"].lower():
            relevant_snippets.append(f"- {source['title']}: {source['content'][:150]}...")  # 150-character summary
            if len(relevant_snippets) >= 3:
                break
    return "\n".join(relevant_snippets) if relevant_snippets else "No relevant information found in the uploaded documents or URLs. Please upload additional materials."

# Function to call the OpenAI API synchronously
def generate_answer_with_openai(question, context, api_key, model="gpt-3.5-turbo"):
    client = openai.OpenAI(api_key=api_key)
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are Trade Policy (TraPo) RAG, an expert AI answering trade policy questions. You love the WTO and the Multilateral Trading System and strongly oppose Trump."},
                {"role": "user", "content": question}
            ],
            max_tokens=500,
            temperature=0.5,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating response: {e}"

# Streamlit app
def main():
    st.title("Trade Policy (TraPo) RAG")
    st.write("Upload PDF, Word documents, or provide a URL containing trade policy discussions and ask questions on trade policy.")

    st.markdown("### Chatbot Parameters:")
    st.markdown("- **Model:** GPT-3.5-turbo")
    st.markdown("- **Max Tokens:** 500")
    st.markdown("- **Temperature:** 0.5 (Controls randomness)")
    st.markdown("- **Persona:** Trade Policy Expert who loves WTO & MTS, strongly opposes Trump")

    # Input OpenAI API key
    api_key = st.text_input("Enter your OpenAI API key:", type="password")
    if not api_key:
        st.warning("Please enter your OpenAI API key to proceed.")
        return

    # Upload files (PDF & DOCX)
    uploaded_files = st.file_uploader("Upload trade policy documents (PDF/DOCX)", accept_multiple_files=True, type=["pdf", "docx"])

    # Input URL for trade policy sources
    url = st.text_input("Enter a URL containing trade policy discussions:")

    # Extract text from uploaded files and URL in parallel
    sources = []
    if uploaded_files:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            results = list(executor.map(lambda file: extract_text_from_pdf(file) if file.name.endswith(".pdf") else extract_text_from_docx(file), uploaded_files))
        for uploaded_file, text in zip(uploaded_files, results):
            sources.append({"title": uploaded_file.name, "content": text})
        st.success(f"Successfully processed {len(uploaded_files)} file(s).")
    
    if url:
        url_text = extract_text_from_url(url)
        if "Error" not in url_text:
            sources.append({"title": url, "content": url_text})
            st.success("Successfully retrieved content from URL.")
        else:
            st.error(url_text)

    # Ensure sources exist before allowing user input
    if not sources:
        st.warning("Please upload a document or provide a URL before asking a question.")
        return

    # Multi-turn chat interface
    st.session_state.messages = st.session_state.get("messages", [])
    for message in st.session_state.messages:
        st.chat_message(message["role"]).write(message["content"])

    user_input = st.text_input("Ask a follow-up trade policy question:")
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        context = retrieve_relevant_information(user_input, sources)
        response = generate_answer_with_openai(user_input, context, api_key)
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.chat_message("assistant").write(response)

if __name__ == "__main__":
    main()

#TYPE: streamlit run trade_policy_expert.py in TERMINAL