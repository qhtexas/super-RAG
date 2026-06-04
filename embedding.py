import chromadb
from pathlib import Path
import hashlib
from chromadb.utils.embedding_functions.ollama_embedding_function import (
    OllamaEmbeddingFunction,
)
from semantic_chunker import get_chunker


dir_path = Path(__file__).parent / ".chroma"
dir_path.mkdir(exist_ok=True)

client = chromadb.PersistentClient(path=str(dir_path)) 

ollama_embedding_function = OllamaEmbeddingFunction(
    url="http://localhost:11434",
    model_name="nomic-embed-text-v2-moe:latest",
)

collection = client.get_or_create_collection(
    name="baseline_guidelines",
    embedding_function=ollama_embedding_function,
)

path = Path(__file__).parent / "results"

for file_path in path.glob("*.md"):
    with open(file_path, "r", encoding="utf-8") as f:
        
        content = f.read()
        chunker = get_chunker(
        "gpt-3.5-turbo",
        chunking_type="markdown",
        max_tokens=500,
        trim=False,
        overlap=5,
        )
        chunks = chunker.chunks(content)
        print(f"Chunked {file_path.name} into {len(chunks)} chunks.")
        for i,chunk in enumerate(chunks):
            name = f"{file_path.name}_{i}_{chunk}"
            chunk_id = hashlib.sha256(name.encode("utf-8")).hexdigest()
            print(f"Chunk {i}: ID={chunk_id}, Text={chunk}...")
            collection.add(
                documents=[chunk],
                ids=[chunk_id],
                metadatas=[{"source": file_path.name, "chunk_index": chunk[1]}],
            )

if __name__ == "__main__":
    response = collection.query(
        query_texts=["standards for good app store search returns"],
        n_results=1,
    )
    print(response["documents"])
    
        
