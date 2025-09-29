from flask import Flask, request, jsonify
import ollama
import re
from concurrent.futures import ThreadPoolExecutor
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_community.embeddings import OllamaEmbeddings
from chromadb.config import Settings
from chromadb import Client
from langchain.vectorstores import Chroma
import requests
import tempfile
import os
import json



app = Flask(__name__)

client = Client(Settings())
embedding_function = OllamaEmbeddings(model="deepseek-r1")
retriever = None  # Will be initialized after PDF processing

@app.route("/load_pdf", methods=["POST"])
def load_pdf():
    global retriever
    print("loading pdf")
    pdf_url = request.json.get("pdf_url")
    if not pdf_url:
        return jsonify({"error": "PDF URL is required"}), 400
    
    # Download the PDF
    response = requests.get(pdf_url)
    if response.status_code != 200:
        return jsonify({"error": "Failed to download PDF"}), 400
    
    # Save it to a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
        temp_pdf.write(response.content)
        temp_pdf_path = temp_pdf.name
    
    # Load and process the PDF
    loader = PyMuPDFLoader(temp_pdf_path)
    documents = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_documents(documents)
    
    # Generate embeddings
    def generate_embedding(chunk):
        return embedding_function.embed_query(chunk.page_content)
    
    with ThreadPoolExecutor() as executor:
        embeddings = list(executor.map(generate_embedding, chunks))
    
    # # Create/reset the collection
    collection_name = "foundations_of_llms"
    try:
        client.delete_collection(name=collection_name)  # Ensure fresh collection
    except Exception as e:
        print(f"Error deleting collection: {e}")
    # collection = client.create_collection(name=collection_name)
    collection = client.create_collection(name="foundations_of_llms")
    for idx, chunk in enumerate(chunks):
        collection.add(
            documents=[chunk.page_content],
            metadatas=[{'id': idx}],
            embeddings=[embeddings[idx]],
            ids=[str(idx)]
        )
    
    # Initialize retriever
    retriever = Chroma(collection_name=collection_name, client=client, embedding_function=embedding_function).as_retriever()
    
    # Clean up temp file
    os.remove(temp_pdf_path)
    print("PDF loaded and processed successfully")
    
    return jsonify({"message": "PDF loaded and processed successfully"})

@app.route("/ask", methods=["POST"])
def ask_question():
    global retriever
    
    if retriever is None:
        return jsonify({"error": "No PDF loaded. Please load a PDF first."}), 400
    
    question = request.json.get("question")
    print(question)
    if not question:
        return jsonify({"error": "Question is required"}), 400
    
    results = retriever.invoke(question)
    context = "\n\n".join([doc.page_content for doc in results])
    
    formatted_prompt = f"Question: {question}\n\nContext: {context}"
    response = ollama.chat(
        model="deepseek-r1",
        messages=[{'role': 'user', 'content': formatted_prompt}]
    )
    print("respondinng")
    response_content = response['message']['content']
    final_answer = re.sub(r'<think>.*?</think>', '', response_content, flags=re.DOTALL).strip()
    
    return jsonify({"answer": final_answer})

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Welcome home! Your API is running."})




if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)




    
    

            

