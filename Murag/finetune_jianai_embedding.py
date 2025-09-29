from llava.model.builder import load_pretrained_model
import torch
model_path='your_model_path'
model_base=None
model_name='llava-med-v1.5-mistral-7b'

if torch.cuda.is_available():
    device = "cuda"
else:
    device = "cpu"
tokenizer, model, image_processor, context_len = load_pretrained_model(model_path, model_base, model_name, load_8bit=False, load_4bit=False, device=device)
# processor = AutoProcessor.from_pretrained("Veda0718/llava-med-v1.5-mistral-7b-finetuned")

# # Load an image
# image = Image.open("Qa-Bot\image.jpg")

# # Preprocess the image and extract features
# inputs = processor(images=image, return_tensors="pt", padding=True)

# # Extract image embeddings (vision encoder outputs)
# with torch.no_grad():
#     image_embeddings = model.get_image_features(**inputs)

# # image_embeddings is now a tensor containing the image features
# print(image_embeddings.shape)  # Example: torch.Size([1, 256, 1024])