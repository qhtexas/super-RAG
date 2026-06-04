import chromadb
from pathlib import Path
dir_path = Path(__file__).parent / ".chroma"
dir_path.mkdir(exist_ok=True)

client = chromadb.PersistentClient(path=str(dir_path))
collection = client.get_collection(
    name="baseline_guidelines",
)
def extract_keywords(text: str):
    pass

def query(keyword: str):
    response = collection.query(
            query_texts=[keyword],
            n_results=3,
        )
    print(response["documents"])
    return response["documents"]

if __name__ == "__main__":
    while True:
        keyword = input("请输入查询关键词：")
        query(keyword)
