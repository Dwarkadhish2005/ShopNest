
import sys
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

from src.config import EMBEDDING_MODEL, FAISS_INDEX_DIR




def get_embeddings() -> HuggingFaceEmbeddings:
    print(f"  Loading embedding model: {EMBEDDING_MODEL} ...")
    device = "cpu"
    try:
        import torch
        if torch.cuda.is_available():
            device = "cuda"
    except Exception:
        device = "cpu"

    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": device},
        encode_kwargs={"normalize_embeddings": True},
    )




def build_and_save_vectorstore(docs: List[Document]) -> FAISS:
    if not docs:
        raise ValueError("No documents provided — run chunker first.")

    embeddings = get_embeddings()

    print(f"  Building FAISS index over {len(docs)} chunks ...")
    vectorstore = FAISS.from_documents(docs, embeddings)

    FAISS_INDEX_DIR.mkdir(parents=True, exist_ok=True)
    vectorstore.save_local(str(FAISS_INDEX_DIR))
    print(f"  FAISS index saved → {FAISS_INDEX_DIR}")

    return vectorstore




def load_vectorstore() -> FAISS:
    if not FAISS_INDEX_DIR.exists():
        raise FileNotFoundError(
            f"FAISS index not found at {FAISS_INDEX_DIR}. "
            "Run  python build_index.py  first."
        )

    embeddings = get_embeddings()
    vectorstore = FAISS.load_local(
        str(FAISS_INDEX_DIR),
        embeddings,
        allow_dangerous_deserialization=True,
    )
    print(f"  FAISS index loaded from {FAISS_INDEX_DIR}")
    return vectorstore
