from sentence_transformers import SentenceTransformer

_model = None


def get_model():
    """Get or load Sentence Transformer model (cached)"""
    global _model
    if _model is None:
        print("⏳ Loading Sentence Transformer...")
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        print("✓ Model ready!")
    return _model
