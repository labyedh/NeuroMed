# # Load model directly
# from transformers import AutoTokenizer, AutoModelForCausalLM

# tokenizer = AutoTokenizer.from_pretrained("emredeveloper/DeepSeek-R1-Medical-COT")
# model = AutoModelForCausalLM.from_pretrained("emredeveloper/DeepSeek-R1-Medical-COT")
# Load model directly
# Load model directly
# Use a pipeline as a high-level helper
from transformers import pipeline

pipe = pipeline("fill-mask", model="answerdotai/ModernBERT-large")