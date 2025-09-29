# Load model and tokenizer
from transformers import AutoTokenizer, AutoModelForCausalLM
from sentence_transformers import SentenceTransformer
import requests
from PyPDF2 import PdfReader
from io import BytesIO
import numpy as np
import torch
from sklearn.metrics.pairwise import cosine_similarity
from transformers import BertTokenizer, BertModel
import json 

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Load BERT model and tokenizer for similarity computation
bert_tokenizer = BertTokenizer.from_pretrained('bert-large-uncased')
bert_model = BertModel.from_pretrained('bert-large-uncased').to(device)


# Load DeepSeek Medical model and tokenizer
tokenizer = AutoTokenizer.from_pretrained("emredeveloper/DeepSeek-R1-Medical-COT")
model = AutoModelForCausalLM.from_pretrained("emredeveloper/DeepSeek-R1-Medical-COT").to(device)

# Load embedding model
embedder = SentenceTransformer('all-MiniLM-L6-v2')

# Extract text from PDF
def extract_text_from_pdf(url):
    response = requests.get(url)
    pdf_file = BytesIO(response.content)
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

# Chunk the text
def chunk_text(text, chunk_size=500):
    chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
    return chunks

# Retrieve relevant chunks
def retrieve_relevant_chunks(query, chunk_embeddings, chunks, top_k=3):
    query_embedding = embedder.encode([query])
    similarities = np.dot(query_embedding, chunk_embeddings.T)
    top_k_indices = np.argsort(similarities[0])[-top_k:]
    relevant_chunks = [chunks[i] for i in top_k_indices]
    return relevant_chunks

# def generate_response(query, relevant_chunks):
#     context = " ".join(relevant_chunks)
#     input_text = f"Context: {context}\n\nQuestion: {query}\n\nAnswer:"
    
#     # Move inputs to the same device as the model
#     inputs = tokenizer(input_text, return_tensors="pt").to(device)
    
#     outputs = model.generate(**inputs, max_length=512)
#     response = tokenizer.decode(outputs[0], skip_special_tokens=True)
#     return response

# Generate response using DeepSeek RAG
def generate_response(query, relevant_chunks):
    context = " ".join(relevant_chunks)
    
    # Truncate the context to fit within the model's max token limit
    inputs = tokenizer(
        f"Context: {context}\n\nQuestion: {query}\n\nAnswer:",
        return_tensors="pt",
        truncation=True,
        max_length=512  # Ensure the input does not exceed the model's max length
    ).to(device)
    
    # Generate response with a reasonable max_new_tokens
    outputs = model.generate(**inputs, max_new_tokens=200)  # Adjust max_new_tokens as needed
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return response 

# # Main function
# def main(pdf_url, query):
#     text = extract_text_from_pdf(pdf_url)
#     chunks = chunk_text(text)
#     chunk_embeddings = embedder.encode(chunks)
#     relevant_chunks = retrieve_relevant_chunks(query, chunk_embeddings, chunks)
#     response = generate_response(query, relevant_chunks)
#     return response

# # Example usage
# pdf_url = "https://breast-cancer-research.biomedcentral.com/counter/pdf/10.1186/s13058-025-01973-3.pdf"
# query = "What does this text talk about "
# response = main(pdf_url, query)
# print(response)
# Benchmarking function
# Compute BERT embeddings for similarity
def get_bert_embedding(text):
    inputs = bert_tokenizer(text, return_tensors='pt', truncation=True, padding=True, max_length=512).to(device)
    outputs = bert_model(**inputs)
    return outputs.last_hidden_state.mean(dim=1).detach().cpu().numpy()

def benchmarking_function():

    json_file = "./arxiv_papers_with_pdf.json"

    data = []
    with open(json_file, "r", encoding="utf-8") as file:
        data = json.load(file)
    print(f"Total papers: {len(data)}")
    
    similarity_scores = []
    
    for i in range(0, 20):
        pdf_url = data[i]['pdf_url']
        
        # Extract text from PDF
        text = extract_text_from_pdf(pdf_url)
        chunks = chunk_text(text)
        chunk_embeddings = embedder.encode(chunks)
        
        # Ask the question
        query = "What does the paper bring new?"
        relevant_chunks = retrieve_relevant_chunks(query, chunk_embeddings, chunks)
        response = generate_response(query, relevant_chunks)
        
        # Compute BERT embeddings for the original text and the response
        original_text_embedding = get_bert_embedding(text)
        answer_embedding = get_bert_embedding(response)
        
        # Compute cosine similarity
        similarity = cosine_similarity(original_text_embedding, answer_embedding)[0][0]
        similarity_scores.append(similarity)
        
        print(f"Paper {i+1} - Similarity Score: {similarity}")
    
    # Calculate the general score for the DeepSeek RAG model
    general_score = np.mean(similarity_scores)
    print(f"General DeepSeek RAG Model Score: {general_score}")
    
    return {"general_score": general_score, "similarity_scores": similarity_scores}

# Run the benchmarking function
benchmarking_function()