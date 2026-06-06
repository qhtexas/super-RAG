import chromadb
from pathlib import Path
from reviewer import Reviewer, ReviewResult
from pydantic import BaseModel

class GuidelinesQuery(BaseModel):
    """This function accept a question of guidelines and backgrounds of question, and return the relevant guidelines."""
    question: str
    background: list[str]


dir_path = Path(__file__).parent / ".chroma"
dir_path.mkdir(exist_ok=True)

client = chromadb.PersistentClient(path=str(dir_path))
collection = client.get_collection(
    name="baseline_guidelines",
)


def query_rag(keyword: str):
    r = GuidelinesQuery.model_validate_json(keyword)
    system_prompt = ("You are a helpful assistant which given the question and background, formulates some query to search the rag database.")
    user_prompt = f"Question: {r.question}\nBackground: {r.background}\nPlease give me some query to search the rag database, and you should return the query"
    
    reviewer = Reviewer(model = "qwen3.5:4b")
    
    review_result = reviewer.generate_query(system_prompt=system_prompt, user_prompt=user_prompt).query
    if not review_result:
        return [""]
    response = collection.query(
                query_texts=review_result,
                n_results=3,
                include = ["documents"],
            )
    print(response["documents"])
    unique_docs_map = {}
    
    # 双层循环解开嵌套：先遍历每一个查询词的返回结果
    for docs_list, ids_list in zip(response["documents"], response["ids"]):
        # 再遍历单个查询词对应的具体文档和 ID
        for doc, doc_id in zip(docs_list, ids_list):
            if doc_id not in unique_docs_map:
                # 如果这个 ID 还没见过，就存入字典
                unique_docs_map[doc_id] = doc
                
    # 字典的值就是去重后的纯文档列表
    flatten_response = list(unique_docs_map.values())
    
    return flatten_response

if __name__ == "__main__":
    while True:
        keyword = input("请输入查询关键词：")
        query_rag(keyword)
