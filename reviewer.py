from ollama import chat
from dataclasses import dataclass, field
from pydantic import BaseModel

class ReviewResult(BaseModel):
    """You should put a result and reason here"""
    result: str
    reason: str

class QueryResult(BaseModel):
    """You should only return a list of queries here"""
    query: list[str]

@dataclass(kw_only=True)
class Reviewer:
    # used for review in misscellaneous scenarios
    model : str = field(default='qwen3.5:9b')
    
    def review(self,user_prompt,system_prompt) -> ReviewResult:
        
        messages =[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        response = chat(
            model=self.model,
            messages=messages,
            format = ReviewResult.model_json_schema(),
        )
        if response.message.content:
            return ReviewResult.model_validate_json(response.message.content)
        else:
            return ReviewResult(result="", reason="The model did not return any content.")
    
    def generate_query(self,user_prompt,system_prompt) -> QueryResult:
        
        messages =[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        response = chat(
            model=self.model,
            messages=messages,
            format = QueryResult.model_json_schema(),
            options = {
                "temperature":0,
            }
        )
        if response.message.content:
            return QueryResult.model_validate_json(response.message.content)
        
        else:
            return QueryResult(query=[""])