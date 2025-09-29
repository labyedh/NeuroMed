from typing import Any
from pydantic import BaseModel
from unstructured.partition.pdf import partition_pdf
from io import BytesIO
import requests

# Path to save images
pdf_url = "https://breast-cancer-research.biomedcentral.com/counter/pdf/10.1186/s13058-025-01973-3.pdf"
response = requests.get(pdf_url)
if response.status_code == 200:
        pdf_data = BytesIO(response.content)
# Get elements
print("Extracting elements from PDF...")
raw_pdf_elements = partition_pdf(
    file=pdf_data,
    extract_images_in_pdf=True,
    infer_table_structure=True,
    chunking_strategy="by_title",
    max_characters=4000,
    new_after_n_chars=3800,
    combine_text_under_n_chars=2000,
    image_output_dir_path="Qa-Bot/Extracted_Images",
)
print(raw_pdf_elements)