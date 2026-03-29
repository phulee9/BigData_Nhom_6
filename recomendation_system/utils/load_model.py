from sentence_transformers import SentenceTransformer
import numpy as np

def load_model(model_name='all-MiniLM-L6-v2'):
    model = SentenceTransformer(model_name)
    
    return model