from ollama import chat,ResponseError
from pydantic import BaseModel, ValidationError
from typing import Any, Literal
from query_rag import query_guidelines
from query_web import  get_google, get_store, query_app_store
from playwright.sync_api import sync_playwright
import subprocess

subprocess.Popen([
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "--remote-debugging-port=9222",
    r"--user-data-dir=D:\coding\super RAG\user_data", # 让它自己存 Cookie 养号，别管它
    "--start-maximized"
])

# Initialize Playwright manually (Option 2)
p = sync_playwright().start()
browser = p.chromium.connect_over_cdp("http://localhost:9222")
if not browser.contexts:
    browser.new_context()
context = browser.contexts[0]
if not context.pages:
    context.new_page()
page = context.pages[0]

def cleanup_playwright():
    """Call this when validator is finished executing"""
    p.stop()

class query_model(BaseModel):
    """the generic format for querying"""
    keyword: str
class return_formatt(BaseModel):
    result: Literal["safe","vulnerable","service error"]
    sentence: str
class meta(BaseModel):
    query_type: str
    distribution: str
class question(BaseModel):
    metadata: meta
    search_keyword: str
    search_result : str
class answer(BaseModel):
    comment: str
    rating: Literal["perfect", "good", "acceptable", "irrelevant", "unacceptable", "unavailable", "spelling/formatting issue", "other problems"]
def check_confidential(input: str):
    system_prompt = ("""You are a secrecy checking assistant, who upon given a text, check if there is possibility of leaking the 'guideline' inside our organization.
                     You should return result and the sentences which may cause leaking.
                     the result should be either vulnerable or safe"""
                    )   
    messages = [{"role":"system","content":system_prompt},{"role":"user","content":f"{input}"}]
    print("AI check_confidential input:", input)
    res = None
    for _  in range(3):
        try:
            response = chat(
                model = "qwen3.5:9b",
                messages = messages,
                format = return_formatt.model_json_schema(),
            )
        except ResponseError as e:
            print("AI check_confidential ResponseError:", e)
            continue
        print("AI check_confidential raw response:", response.message.content)
        if not response.message.content:
            continue
        try: 
            return_formatt.model_validate_json(response.message.content)
        except ValidationError as e:
            messages.append({"role":"user", "content":f"Your output format is wrong, see {e}"})
            continue
        res = return_formatt.model_validate_json(response.message.content)
        break
    else:
        return return_formatt(result="service error",sentence="Something unprecedented happened, try recall this service")
    return res

from pathlib import Path
path =  Path(__file__).parent / "results" / "Guideline for Search - App Store Suggestions.md"
file = open(path, "r", encoding="utf-8")
guidelines = file.read()
file.close()

def google_search(keyword: str) -> list[str]:
        """
        Use this tool ONLY to search the live internet for external app names and market descriptions.
        NEVER use this tool to search for internal organizational guidelines, evaluation criteria, or typos.
        """
    #a = check_confidential(keyword)
    #if a.result == "safe" or a.result == "service error":
        try:
            query_model.model_validate(keyword)
        except ValidationError as e:
            return [f"Your input value is wrong,{e}"]
        model = query_model.model_validate(keyword)
        result = get_google(page, model.keyword)        
        return result
    #else:
        result = list()
        result.append("There is a potential of leakage of guideline error, reformalize your query")
        for sentence in a.sentence:
            result.append(sentence)
        return result
def google_play_search(keyword: str)->list[str]:
    """
    Use this tool ONLY to search the Google Play Store for specific Android applications and their descriptions.
    NEVER use this tool to search for rules or guidelines.
    Only check keywords or phrases, rather than sentences.
    """
    #a = check_confidential(keyword)
    source: list[str] = []
    source.append('"source":google play')
    #if a.result == "safe" or a.result == "service error":
    try:
        query_model.model_validate(keyword)
    except ValidationError as e:
        return [f"Your input value is wrong,{e}"]
    model = query_model.model_validate(keyword)
    result = get_google(page, model.keyword)
    final =  source + result
    return final
#    else:
#        result = list()
#        result.append("There is a potential of leakage of guideline error, reformalize your query")
#        for sentence in a.sentence:
#            result.append(sentence)
#        return result
def apple_app_store_search(keyword: str) -> list[str]:
#    a = check_confidential(keyword)
    source: list[str] = []
    source.append('"source":app_store')
#    if a.result == "safe" or a.result == "service error":
    result = query_app_store(page, keyword)
    final =  source + result
    return final
    """
    else:
        result = list()
        result.append("There is a potential of leakage of guideline error, reformalize your query")
        for sentence in a.sentence:
            result.append(sentence)
        return result   
    """

dispatcher = {
    "query_rag": query_guidelines,
    "google_search": google_search,
    "google_play_search": google_play_search,
    #"app_store_search": apple_app_store_search,
}

def validator():
    variables={}
    ans = None
    iter = ["query_type","distribution","search_input","search_output"]
    for item in iter:
        variables[item] = input(f"please enter {item}")
    sample = question(metadata=meta(query_type=variables["query_type"], distribution=variables["distribution"]),search_keyword=variables["search_input"],search_result=variables["search_output"])    
    messages = []
    messages.append({"role":"system","content":"""You are an evaluation assistant. You evaluate a search output's(can be a certain name or description) relevance to the input based strictly on the provided JSON data and guidelines.
    CRITICAL TOOL ROUTING RULES:
    1. If you need clarification on further criteria and guidance, you MUST use the `query_guidelines` tool.
    2. NEVER use `Google Search` or `google_play_search` to look up guidelines. Those tools are STRICTLY for verifying external app existence or checking search outputs on other platforms.
    3. Assume all apps provided in the initial data exist. Keep your web search queries concise.
    4.Once you make a logical conclusion in your thinking phase, commit to it in your output. Do not hedge, backpedal, or use words like "However" to justify lower ratings for top-tier global brands."""
})
    messages.append({"role":"user","content":f"data:{sample.model_dump_json()}, guidelines: {guidelines}"})
    while True:
        response = chat(
            model="qwen3.5:9b",
            messages=messages,
            tools=[query_guidelines, google_play_search, google_search],
            think=True,
            format=answer.model_json_schema(),
        )
        
        # 将助手的回复加入历史记录
        messages.append(response.message)
        print(f"thinking:\n{response.message.thinking}")
        print(f"content:\n{response.message.content}")

        # 1. 优先处理工具调用
        if response.message.tool_calls:
            for call in response.message.tool_calls:
                print(f"AI validator tool call: {call.function.name}, args: {call.function.arguments}")
                if call.function.name in dispatcher:
                    # 修复 1：使用 ** 解包 arguments 字典，避免 Pydantic 报错 input_type=dict
                    args = call.function.arguments
                    result = dispatcher[call.function.name](args) 
                    print(f"Tool {call.function.name} result:", result)
                    messages.append({
                        "role": "tool",
                        "tool_name": call.function.name,
                        "content": str(result)
                    })
            # 拿到工具结果后，立刻 continue 进入下一轮，让模型读取工具返回的信息
            continue

        # 2. 处理模型的文本/JSON 输出
        if response.message.content:
            try:
                ans = answer.model_validate_json(response.message.content)
            except ValidationError as e:
                # 格式错误，提示模型重新生成
                messages.append({
                    "role": "user",
                    "content": f"Your output format is wrong, {e}"
                })
        else:
            # 修复 2：拦截“无工具调用且内容为空”的死循环
            if not response.message.tool_calls:
                messages.append({
                    "role": "user",
                    "content": "You successfully completed your reasoning, but you outputted an empty response. You MUST output your final decision purely in the required JSON format."
                })

        # 3. 检查是否成功拿到了合法的 JSON 解析结果
        if ans is not None:
            print(f"Rating: {ans.rating}")
            print(f"Comment: {ans.comment}")
            break
    
if __name__ == "__main__":
    validator()
    cleanup_playwright()
