import os
import base64
from byaldi import RAGMultiModalModel

RAG = RAGMultiModalModel.from_pretrained("vidore/colpali-v1.2", verbose=1)
RAG.index(
    input_path="https://breast-cancer-research.biomedcentral.com/counter/pdf/10.1186/s13058-025-01973-3.pdf",
    index_name="attention",
    store_collection_with_index=True,  # Store base64 representation of images
    overwrite=True
)
query = "What's the BLEU score of the transformer architecture in EN-DE"
results = RAG.search(query, k=1)
print(results)