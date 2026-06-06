import httpx
from playwright.sync_api import sync_playwright, Page
from pydantic import BaseModel, ValidationError
from typing import Any,Literal
from openai import OpenAI
from dotenv import load_dotenv
import os
load_dotenv()
import json
key = os.getenv("DEEPSEEK")
class SearchItemBrowser(BaseModel):
    title:str
    url:str
    description:str
class SortResultBrowser(BaseModel):
    result: list[ SearchItemBrowser ]

class StoreItem(BaseModel):
    name: str
    description:str

class StoreResult(BaseModel):
    result: list[StoreItem]

class WikiSearch(BaseModel):
    keywords: list[str]

class WikiResult(BaseModel):
    status : Literal["success","fail","partial"]
    text: list[str] | None = None
    error_msg : str | None = None

google_instance = SortResultBrowser(
    result=[
        SearchItemBrowser(title="example", url="example.com", description="This is a demo"),
    ]
)

store_instance = StoreResult(
    result=[
        StoreItem(name="example",description="This is a demo")
    ]
)

# 动态寻找 Pydantic 对象中列表长度的万能小函数
def get_main_list_length(pydantic_obj):
    # 将模型转化为原生字典
    data_dict = pydantic_obj.model_dump()
    # 遍历所有的值，找到那个真正的列表
    for value in data_dict.values():
        if isinstance(value, list):
            return len(value)
    return 0


import subprocess
from pathlib import Path
path1 = Path(__file__).parent / "webpages"
subprocess.Popen([
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "--remote-debugging-port=9222",
    r"--user-data-dir=D:\coding\super RAG\user_data", # 让它自己存 Cookie 养号，别管它
    "--start-maximized"
])



def get_imdb(page: Page, keyword: str|None = None) -> list[str]:
    path = Path(__file__).parent / "webpages" / "imdb.html"
    page.goto(path)
    person = page.get_by_test_id("find-results-section-name").locator(".ipc-metadata-list-summary-item")#演员和出演电影
    print(person.all_inner_texts())
    title = page.get_by_test_id("find-results-section-title").locator(".ipc-metadata-list-summary-item")#电影
    print(title.all_inner_texts())
    

def get_youtube(page: Page):
    page.goto("https://www.youtube.com/results?search_query=cs50")
    play_list = page.locator(".text-wrapper style-scope ytd-video-renderer")
    print(play_list.all_inner_texts())    
    

def get_spotify():
    #path = Path(__file__).parent / 
    pass


def search_wiki(keyword: str) -> str:
    try:
        input = WikiSearch.model_validate_json(keyword)
    except ValidationError:
        return WikiResult(status="fail", error_msg="invalid attributes passed").model_dump_json()
    url = "https://en.wikipedia.org/w/api.php"
    header = {"User-Agent":"My-Rag-Agent (Contact: qhtexas777@gmail.com)"}
    params = {"action":"query","prop":"extracts","exintro":True,"format":"json","explaintext":True,"exlimit":1,"redirects":1}
    result = list()
    fail = list()
    with httpx.Client(headers=header, http2=True) as c:
        for word in input.keywords:
            params["titles"]=word
            try:
                response = c.get(url,params=params)
                response.raise_for_status()
                response = response.json()
            except httpx.HTTPStatusError as e:
                return WikiResult(status = "fail", error_msg=f"{e}").model_dump_json()
            page = response.get("query",{}).get("pages",{})
            for id, info in page.items():
                if id == "-1":
                    fail.append(word)
                    continue
                text = info.get("extract","")
                if not text:
                    fail.append(word)
                    continue
                    
                result.append(text.strip())
    if fail:
        return WikiResult(status="partial", text = result if result else [],error_msg=f"Your search keyword(s) {', '.join(fail)} is too general thus doesn't exactly match anything, try more specific ones").model_dump_json()
    return WikiResult(status="success", text = result).model_dump_json()
            
            
            
def get_google(page: Page, keyword: str) -> list[str]:
    url = f"https://www.google.com/search?q={keyword}"
    page.goto(url)
    main = page.locator("#main").locator("#center_col").locator("#search").locator("#rso").locator(".MjjYud")
    print(main.all_inner_texts())
    results = main.all_inner_texts()
    for result in results:
        result.replace("Read More","")
    print(results)
    return results                    
            
def get_store(page: Page,keyword:str) -> list[str]:
    path = path1 /"imsta - Android Apps on Google Play.html"
    page.goto(f"https://play.google.com/store/search?q={keyword}&c=apps")
    result = page.locator(".cXFu1")
    print(result.all_inner_texts())#内涵app名字和简短描述
    return result.all_inner_texts()


client_formatter = OpenAI(
    base_url="https://api.deepseek.com",
    api_key=key,
)


google_json = google_instance.model_dump_json(indent=2)

store_json = store_instance.model_dump_json(indent=2)

model = [SortResultBrowser,StoreResult]

def query_web(keyword:str) -> list[str]:
    with sync_playwright() as p:
        # setting up
        browser = p.chromium.connect_over_cdp("http://localhost:9222")
        if not browser.contexts:
            browser.new_context
        context = browser.contexts[0]
        if not context.pages:
            context.new_page
        page = context.pages[0]
        google_result = get_google(page,keyword = keyword)
        google_play_result = get_store(page, keyword)
        result = []
        for i, (k,v) in enumerate({google_json:google_result, store_json:google_play_result}.items()):
            system_prompt = f"""You are a professional recommendation system data extraction agent.
            Your task is to read the web search results provided by the user and extract each piece of information clearly and separately, avoiding arbitrary merging.
            You must output strictly in the required JSON format and remove meaningless content and advertisements. Format: {k}"""
            user_prompt = f"""
            Based on the content captured inside the `<search_results>` tag below, extract the feature data.
            <search_results>
            {v}
            </search_results>
            Please begin your extraction:
            """
            messages=[{"role":"system","content":system_prompt},{"role":"user","content":user_prompt}]
            for j in range(3):
                response = client_formatter.chat.completions.create(
                    model="deepseek-v4-pro",
                    messages=messages,
                    response_format={"type":"json_object"},
                )
                text = response.choices[0].message.content
                if text:
                    try:
                        r = model[i].model_validate_json(text)
                        result.append(r.model_dump_json())
                        break
                    except ValidationError as e:
                        messages.append(response.choices[0].message)
                        messages.append({"role":"user","content":f"The return format is incorrect, error: {e}"})
                        continue
            else:
                return []
    print(result)
    return result


from helper import generate_function_tool

tools = [
    generate_function_tool(name="search_wikipedia",
                            description="This is a function, by given the exact keyword, return the extract of that word's corresponding page on wikipedia",
                            parameters = WikiSearch.model_json_schema(),
                            )
]

def further_description(content: list[str]) -> list[str]:
    # 🌟 改动三：强力 System Prompt，定死行为边界
    system_prompt = """You are a rigorous data repair agent.
    1. Your task is to inspect the description field in the JSON. If it is a meaningless short comment (for example containing "star") or is extremely incomplete, call the search_wikipedia tool to replace it with objective information.
    2. If the entity cannot be found on Wikipedia, change its description to "No detailed description available". Do not delete the item under any circumstances! You must keep the total number of items in the JSON list exactly the same as before.
    3. All modifications must be extremely concise, within 50 words, and only describe objective facts.
    4. If the description is already sufficiently detailed and objective, keep it unchanged; do not add unnecessary expansion.
    5. Return only the complete modified JSON string, strictly preserving the original schema structure."""
    
    json_list = [google_json, store_json]
    obj = []
    
    for i, item in enumerate(content):
        # 🌟 改动一：智能路由检查，防止“好数据被过度加工”
        try:
            data_dict = json.loads(item)
            needs_fix = False
            # 尝试扫描所有 description
            if "result" in data_dict:
                for entry in data_dict["result"]:
                    desc = entry.get("description", "")
                    # 如果描述太短，或者包含应用商店星级等垃圾数据，才需要触发大模型清洗
                    if len(desc) < 20 or "star" in desc.lower():
                        needs_fix = True
                        break
            
            if not needs_fix:
                print(f"✅ 第 {i} 组数据质量良好（如 Google 搜索结果），直接免检放行。")
                obj.append(item)
                continue
        except Exception as e:
            print(f"⚠️ JSON 初步解析异常，将直接交由大模型处理: {e}")
            pass

        print(f"🔄 第 {i} 组数据存在瑕疵，正在呼叫 Agent 与 Wikipedia 联动修复...")
        message = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"This is the content you should modify {item}, you should keep the schema {json_list[i]}"}
        ]
        
        for j in range(3):
            chat = client_formatter.chat.completions.create(
                model="deepseek-v4-pro", 
                tools=tools,
                messages=message,
                response_format={"type": "json_object"}
            )
            
            response_msg = chat.choices[0].message
            text = response_msg.content
            
            # 处理工具调用 (Tool Calls)
            if response_msg.tool_calls:
                message.append(response_msg)
                for tool in response_msg.tool_calls:
                    args = tool.function.arguments
                    result = search_wiki(args)
                    message.append({
                        "role": "tool",
                        "tool_call_id": tool.id, 
                        "content": f"{result}"
                    })
                continue # 工具调用结束后，直接触发下一次请求
            
            # 处理大模型最终的 JSON 返回
            if text:
                try:
                    r = model[i].model_validate_json(text)
                    a = model[i].model_validate_json(content[i])
                    
                    if get_main_list_length(r) != get_main_list_length(a):
                        raise ValueError("大模型擅自增加了或删除了列表内的项目！")
                        
                    obj.append(r.model_dump_json())
                    print(f"🎉 第 {i} 组数据修复并校验成功！")
                    break
                    
                except ValidationError as e:
                    # 🌟 改动二：打破盲盒，追加 Debug 打印
                    print(f"⚠️ [第 {j+1}/3 次重试] 格式校验失败: {e}")
                    message.append(response_msg)
                    message.append({"role": "user", "content": f"The return format is incorrect, error: {e}"})
                    continue
                except ValueError as e:
                    # 🌟 改动二：打印长度异常警告，并给大模型下达死命令
                    print(f"⚠️ [第 {j+1}/3 次重试] 列表长度校验失败！")
                    message.append(response_msg)
                    message.append({
                        "role": "user", 
                        "content": f"Data tampering warning: {e}. Strictly preserve the original list length! If an item cannot be found on Wikipedia, set its description to 'No detailed description available'. Do not remove it from the JSON under any circumstances."
                    })
                    continue
        else:
            print(f"❌ 第 {i} 组数据经过 3 次重试仍未修复成功，启用原样兜底保留。")
            obj.append(item) # 兜底保护：即使大模型彻底失败，也把原始数据塞进去，防止后续算法崩溃
            
    print("\n--- 终极清洗流水线输出 ---")
    print(obj)
    return obj if obj else []
                

if __name__ == "__main__":
    result = query_web("instagram")
    further_description(result)                