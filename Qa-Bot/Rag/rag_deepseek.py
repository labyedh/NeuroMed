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
    # client.delete_collection(name=collection_name)  # Ensure fresh collection
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
    
    return jsonify({"message": "PDF loaded and processed successfully"})

@app.route("/ask", methods=["POST"])
def ask_question():
    global retriever
    
    if retriever is None:
        return jsonify({"error": "No PDF loaded. Please load a PDF first."}), 400
    
    question = request.json.get("question")
    if not question:
        return jsonify({"error": "Question is required"}), 400
    
    results = retriever.invoke(question)
    context = "\n\n".join([doc.page_content for doc in results])
    
    formatted_prompt = f"Question: {question}\n\nContext: {context}"
    response = ollama.chat(
        model="deepseek-r1",
        messages=[{'role': 'user', 'content': formatted_prompt}]
    )
    
    response_content = response['message']['content']
    final_answer = re.sub(r'<think>.*?</think>', '', response_content, flags=re.DOTALL).strip()
    
    return jsonify({"answer": final_answer})

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Welcome home! Your API is running."})




# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=5000)


from sklearn.metrics.pairwise import cosine_similarity
from transformers import BertTokenizer, BertModel
import numpy as np
from transformers import AutoTokenizer, AutoModelForMaskedLM
def benchmarking_function():
    json_file = "./arxiv_papers_with_pdf.json"

    data = []
    with open(json_file, "r", encoding="utf-8") as file:
        data = json.load(file)
    print(len(data))
    
    # Load BERT model and tokenizer for similarity computation
    tokenizer = BertTokenizer.from_pretrained('bert-large-uncased')
    model = BertModel.from_pretrained('bert-large-uncased')
    print("modeeel")
    # tokenizer = AutoTokenizer.from_pretrained("answerdotai/ModernBERT-large")
    # model = AutoModelForMaskedLM.from_pretrained("answerdotai/ModernBERT-large")
    similarity_scores = []
    
    for i in range(0, 20):
        pdf_url = data[i]['pdf_url']
        
        # Load and process the PDF
        response = requests.get(pdf_url)
        if response.status_code != 200:
            print(f"Failed to download PDF {i}")
            continue
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
            temp_pdf.write(response.content)
            temp_pdf_path = temp_pdf.name
        
        loader = PyMuPDFLoader(temp_pdf_path)
        documents = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = text_splitter.split_documents(documents)
        
        # Generate embeddings for the chunks
        def generate_embedding(chunk):
            return embedding_function.embed_query(chunk.page_content)
        
        with ThreadPoolExecutor() as executor:
            embeddings = list(executor.map(generate_embedding, chunks))
        
        # Create/reset the collection
        collection_name = f"paper_{i}"
        # client.delete_collection(name=collection_name)  # Ensure fresh collection
        collection = client.create_collection(name=collection_name)
        for idx, chunk in enumerate(chunks):
            collection.add(
                documents=[chunk.page_content],
                metadatas=[{'id': idx}],
                embeddings=[embeddings[idx]],
                ids=[str(idx)]
            )
        
        # Initialize retriever
        retriever = Chroma(collection_name=collection_name, client=client, embedding_function=embedding_function).as_retriever()
        
        # Ask the question
        question = "What does the paper bring new?"
        results = retriever.invoke(question)
        context = "\n\n".join([doc.page_content for doc in results])
        
        formatted_prompt = f"Question: {question}\n\nContext: {context}"
        response = ollama.chat(
            model="deepseek-r1",
            messages=[{'role': 'user', 'content': formatted_prompt}]
        )
        
        response_content = response['message']['content']
        final_answer = re.sub(r'<think>.*?</think>', '', response_content, flags=re.DOTALL).strip()
        
        # Compute BERT embeddings for the final answer and the original text
        def get_bert_embedding(text):
            inputs = tokenizer(text, return_tensors='pt', truncation=True, padding=True, max_length=512)
            outputs = model(**inputs)
            return outputs.last_hidden_state.mean(dim=1).detach().numpy()
        
        original_text_embedding = get_bert_embedding(context)
        answer_embedding = get_bert_embedding(final_answer)
        
        # Compute cosine similarity
        similarity = cosine_similarity(original_text_embedding, answer_embedding)[0][0]
        similarity_scores.append(similarity)
        
        # Clean up temp file
        os.remove(temp_pdf_path)
    
    # Calculate the general score for the RAG model
    general_score = np.mean(similarity_scores)
    print(f"General RAG Model Score: {general_score}")
    
    return jsonify({"general_score": general_score, "similarity_scores": similarity_scores})

# Run the benchmarking function
benchmarking_function()

    
    

            

