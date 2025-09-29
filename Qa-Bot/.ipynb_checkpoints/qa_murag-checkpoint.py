import fitz  # PyMuPDF
import requests
from io import BytesIO
import os
import pdfplumber
import pandas as pd
from PIL import Image
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import CharacterTextSplitter
from unstructured.partition.pdf import partition_pdf
from transformers import pipeline, BlipProcessor, BlipForConditionalGeneration
from langchain_community.llms import Ollama
import torch
import base64
import uuid
import io
import re
import os
from langchain.retrievers.multi_vector import MultiVectorRetriever
from langchain.storage import InMemoryStore
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from IPython.display import HTML, display


def extract_text_from_pdf(pdf_data):

    """Extracts text from a PDF file and splits it into a list of phrases."""
    doc = fitz.open(stream=pdf_data, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text("text") + "\n"
    doc.close()
    phrases = text.split('. ')  # Split text into phrases
    return phrases
 
def extract_tables_from_pdf(pdf_data):

    """Extracts tables from a PDF file and converts them into structured DataFrames."""
    tables_list = []
    with pdfplumber.open(pdf_data) as pdf:
        for page in pdf.pages:
            table = page.extract_table(
                table_settings={
                    "vertical_strategy": "lines",  # Use lines to better detect columns
                    "horizontal_strategy": "lines", 
                    "snap_tolerance": 3,  # Adjust based on table alignment
                }
            )
            if table:
                df = pd.DataFrame(table[1:], columns=table[0])  # Convert table to DataFrame
                df.dropna(how="all", inplace=True)  # Remove empty rows
                tables_list.append(df)
    return tables_list
 
def extract_images_from_pdf(pdf_data, output_folder="./Qa-Bot/Extracted_Images"):

    """Extracts images from a PDF file and saves them as image files."""
    doc = fitz.open(stream=pdf_data, filetype="pdf")
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
 
    image_count = 0
 
    for page_num in range(len(doc)):
        page = doc[page_num]
        image_list = page.get_images(full=True)
 
        for img_index, img in enumerate(image_list):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]
            image = Image.open(BytesIO(image_bytes))
            image_filename = os.path.join(output_folder, f"image_{page_num+1}_{img_index+1}.{image_ext}")
            path=os.path.join(output_folder,image_filename)
            image.save(image_filename)
            print(f"Image saved: {image_filename}")
            image_count += 1
    doc.close()
    print(f"Extraction complete: {image_count} images extracted.")
 
def chunk_text(text, chunk_size=500, overlap=50):
    """Split text into smaller chunks with optional overlap."""
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
    return chunks
 
def extract_pdf_elements(pdf_url): 
    pdf_url = "https://breast-cancer-research.biomedcentral.com/counter/pdf/10.1186/s13058-025-01973-3.pdf"
    response = requests.get(pdf_url)
    extracted_text = []
    if response.status_code == 200:
        pdf_data = BytesIO(response.content)
    
        extracted_text = extract_text_from_pdf(pdf_data)
        print("Extracted Phrases:\n", extracted_text)
      #  extracted_images=extract_images_from_pdf(BytesIO(response.content))
        tables = extract_tables_from_pdf(BytesIO(response.content))
        print("Extracted Tables:")
        for i, table in enumerate(tables):
            print(f"Table {i+1}:")
            print(table, "\n")
        chunked_text = []
        for text in extracted_text:
            chunks = chunk_text(text, chunk_size=500, overlap=50)
            chunked_text.extend(chunks)
     
        extracted_text = chunked_text
        return {
            "text": extracted_text,
          #  "images":extracted_images,
            "tables": tables
        }
    else:
        print(f"Failed to download PDF. Status code: {response.status_code}")


# Initialize image captioning model
processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
if torch.cuda.is_available():
    model = model.to("cuda")
    print("cuda available")

def generate_text_summaries(texts, tables, summarize_texts=False):
    """
    Summarize text elements using Llama via Ollama
    """
    prompt_template = """Summarize the following text concisely for retrieval purposes:
    
    {text}
    
    Summary:"""
    
    def summarize_text(text):
        prompt = prompt_template.format(text=text)
        return llm.invoke(prompt)
    
    text_summaries = []
    table_summaries = []
    
    if texts and summarize_texts:
        text_summaries = [summarize_text(text) for text in texts]
    elif texts:
        text_summaries = texts
        
    if tables:
        table_summaries = [summarize_text(table) for table in tables]
        
    return text_summaries, table_summaries

def image_summarize(image):
    """Generate image caption using BLIP"""
    if isinstance(image, str):  # If base64 string
        image = Image.open(io.BytesIO(base64.b64decode(image)))
    inputs = processor(image, return_tensors="pt")
    if torch.cuda.is_available():
        inputs = inputs.to("cuda")
    out = model.generate(**inputs)
    return processor.decode(out[0], skip_special_tokens=True)

def generate_img_summaries(path):
    """
    Generate summaries and base64 encoded strings for images
    """
    img_base64_list = []
    image_summaries = []
    
    for img_file in sorted(os.listdir(path)):
            img_path = os.path.join(path, img_file)
            # Load and encode image
            with open(img_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode("utf-8")
                img_base64_list.append(base64_image)
            
            # Generate summary using BLIP
            image = Image.open(img_path)
            image_summaries.append(image_summarize(image))
    
    return img_base64_list, image_summaries
########################
# def create_multi_vector_retriever(
#     vectorstore, text_summaries, texts, table_summaries, tables, image_summaries, images
# ):
#     """
#     Create retriever that indexes summaries, but returns raw images or texts
#     """
#     store = InMemoryStore() 
#     id_key = "doc_id"
    
#     retriever = MultiVectorRetriever(
#         vectorstore=vectorstore,
#         docstore=store,
#         id_key=id_key,
#     )
    
#     def add_documents(retriever, doc_summaries, doc_contents):
#         doc_ids = [str(uuid.uuid4()) for _ in doc_contents]
#         summary_docs = [
#             Document(page_content=s, metadata={id_key: doc_ids[i]})
#             for i, s in enumerate(doc_summaries)
#         ]
#         retriever.vectorstore.add_documents(summary_docs)
#         retriever.docstore.mset(list(zip(doc_ids, doc_contents)))
    
#     if text_summaries:
#         add_documents(retriever, text_summaries, texts)
#     if table_summaries:
#         add_documents(retriever, table_summaries, tables)
#     if image_summaries:
#         add_documents(retriever, image_summaries, images)
    
#     return retriever
import base64

def validate_base64(b64_string):
    try:
        # Attempt to decode the base64 string
        base64.b64decode(b64_string, validate=True)
        return True
    except Exception as e:
        print(f"Invalid base64 string: {e}")
        return False

def fix_base64_padding(b64_string):
    # Add padding if necessary
    padding = len(b64_string) % 4
    if padding:
        b64_string += "=" * (4 - padding)
    return b64_string

# def create_multi_vector_retriever(
#     vectorstore, text_summaries, texts, table_summaries, tables, image_summaries, images
# ):
#     """
#     Create retriever that indexes summaries, but returns raw images or texts
#     """
#     store = InMemoryStore() 
#     id_key = "doc_id"
    
#     retriever = MultiVectorRetriever(
#         vectorstore=vectorstore,
#         docstore=store,
#         id_key=id_key,
#     )
    
#     def add_documents(retriever, doc_summaries, doc_contents):
#         doc_ids = [str(uuid.uuid4()) for _ in doc_contents]
#         summary_docs = [
#             Document(page_content=s, metadata={id_key: doc_ids[i]})
#             for i, s in enumerate(doc_summaries)
#         ]
#         retriever.vectorstore.add_documents(summary_docs)
#         retriever.docstore.mset(list(zip(doc_ids, doc_contents)))
    
#     if text_summaries:
#         add_documents(retriever, text_summaries, texts)
#     if table_summaries:
#         add_documents(retriever, table_summaries, tables)
#     if image_summaries:
#         # Validate and fix base64 strings before adding them
#         valid_images = []
#         for img in images:
#             if validate_base64(img):
#                 valid_images.append(img)
#             else:
#                 fixed_img = fix_base64_padding(img)
#                 if validate_base64(fixed_img):
#                     valid_images.append(fixed_img)
#         add_documents(retriever, image_summaries, valid_images)
    
#     return retriever

def looks_like_base64(sb):
    return re.match("^[A-Za-z0-9+/]+[=]{0,2}$", sb) is not None

# def multi_modal_rag_chain(retriever):
#     """
#     Multi-modal RAG chain using Llama
#     """
#     def process_query(query_and_docs):
#         query, docs = query_and_docs
#         print("Query:", query)
#         print("Docs:", docs)
#         # Split into images and texts
#         image_docs = []
#         text_docs = []
#         for doc in docs:
#             if isinstance(doc, str) and looks_like_base64(doc) :
#                 image_docs.append(doc)
#             else:
#                 text_docs.append(str(doc))  # Convert any non-string docs to string
        
#         # Generate prompt
#         prompt = f"""You are medical expert who answers researchers queries.
#         Based on the following information, please answer this question: {query}
        
#         Text and Tables:
#         {' '.join(text_docs)}
        
#         Image Descriptions:
#         {' '.join([image_summarize(img) for img in image_docs]) if image_docs else 'No images available'}
        
#         Analysis:"""
        
#         # Generate response using Llama
#         response = llm.invoke(prompt)  # Ollama returns string directly
#         return response.strip()
    
#     chain = (
#         {
#             "context": retriever,
#             "question": RunnablePassthrough(),
#         }
#         | RunnableLambda(process_query)
#     )
    
#     return chain
def process_query(query_and_docs):
    query, docs = query_and_docs["question"], query_and_docs["context"]
    
    # Split into images and texts
    image_docs = []
    text_docs = []
    
    for doc in docs:
        if isinstance(doc, Document):  # Handle Document objects
            content = doc.page_content
        else:
            content = str(doc)
            
        if looks_like_base64(content):
            try:
                # Validate base64 string
                base64.b64decode(content)
                image_docs.append(content)
            except:
                print(f"Skipping invalid base64 content")
        else:
            text_docs.append(content)
    
    # Generate prompt
    prompt = f"""You are medical expert who answers researchers queries.
    Based on the following information, please answer this question: {query}
    
    Text and Tables:
    {' '.join(text_docs)}
    
    Image Descriptions:
    {' '.join([image_summarize(img) for img in image_docs]) if image_docs else 'No images available'}
    
    Analysis:"""
    
    return prompt

def multi_modal_rag_chain(retriever, llm):
    """
    Multi-modal RAG chain using provided LLM
    """
    def get_response(prompt):
        return llm.invoke(prompt).strip()
    
    chain = (
        {
            "context": retriever,
            "question": RunnablePassthrough()
        }
        | RunnableLambda(process_query)
        | RunnableLambda(get_response)
    )
    
    return chain

def create_multi_vector_retriever(
    vectorstore, text_summaries, texts, table_summaries, tables, image_summaries, images
):
    """
    Create retriever that indexes summaries, but returns raw content
    """
    store = InMemoryStore()
    id_key = "doc_id"
    
    retriever = MultiVectorRetriever(
        vectorstore=vectorstore,
        docstore=store,
        id_key=id_key,
    )
    
    def add_documents(retriever, summaries, contents):
        if not summaries or not contents:
            return
            
        doc_ids = [str(uuid.uuid4()) for _ in contents]
        summary_docs = [
            Document(page_content=s, metadata={id_key: doc_ids[i]})
            for i, s in enumerate(summaries)
        ]
        
        # Add documents to vectorstore and docstore
        retriever.vectorstore.add_documents(summary_docs)
        retriever.docstore.mset(list(zip(doc_ids, contents)))
    
    # Add each type of content
    add_documents(retriever, text_summaries, texts)
    add_documents(retriever, table_summaries, tables)
    add_documents(retriever, image_summaries, images)
    
    return retriever

if __name__ == "__main__":
    # Initialize models
    llm = Ollama(model="llama3")
    
    # Load and process PDF
    pdf_url = "https://breast-cancer-research.biomedcentral.com/counter/pdf/10.1186/s13058-025-01973-3.pdf"
    extracted_elements = extract_pdf_elements(pdf_url)
    
    # Generate summaries
    text_summaries, table_summaries = generate_text_summaries(
        extracted_elements["text"],
        extracted_elements["tables"],
        summarize_texts=True
    )
    
    # Process images
    img_base64_list, image_summaries = generate_img_summaries("./Qa-Bot/Extracted_Images")
    
    # Initialize vectorstore
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-mpnet-base-v2"
    )
    vectorstore = Chroma(
        collection_name="mm_rag_blog",
        embedding_function=embeddings
    )
    
    # Create retriever and chain
    retriever = create_multi_vector_retriever(
        vectorstore,
        text_summaries,
        extracted_elements["text"],
        table_summaries,
        extracted_elements["tables"],
        image_summaries,
        img_base64_list
    )
    
    chain = multi_modal_rag_chain(retriever, llm)
    
    # Test query
    query = "What are the medical areas discussed in this research?"
    try:
        response = chain.invoke(query)
        print("\nResponse:", response)
    except Exception as e:
        print(f"Error occurred: {str(e)}")