import httpx
from playwright.sync_api import sync_playwright, Page
from pydantic import BaseModel, ValidationError
from typing import Any,Literal
from openai import OpenAI
from dotenv import load_dotenv
import os
from ollama import chat
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
google_json = google_instance.model_dump_json(indent=2)

store_json = store_instance.model_dump_json(indent=2)
schema_map = {
        "app_store": StoreResult,
        "google_play": StoreResult,
        "web": SortResultBrowser,
    }
prompt_example_map = {
        "app_store": store_json,
        "google_play": store_json,
        "web": google_json,
    }
source_list = Literal["app_store", "google_play", "web"]
# 动态寻找 Pydantic 对象中列表长度的万能小函数
def get_main_list_length(pydantic_obj):
    # 将模型转化为原生字典
    data_dict = pydantic_obj.model_dump()
    # 遍历所有的值，找到那个真正的列表
    for value in data_dict.values():
        if isinstance(value, list):
            return len(value)
    return 0

from pathlib import Path
path1 = Path(__file__).parent / "webpages"




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
    
    #word = extract(keyword)
    print(f"extracted keyword:{keyword}")
    url = f"https://www.google.com/search?q={keyword}"
    page.goto(url)
    main = page.locator("#main").locator("#center_col").locator("#search").locator("#rso").locator(".MjjYud")
    print(main.all_inner_texts())
    results = main.all_inner_texts()
    a = []
    for result in results[:5]:
        j = result.replace("Read more","")
        a.append(j)
    print(results)
    formatted = formatter(content=a,source="web")
    detailed = further_description(content=formatted,source="web")
    return detailed 
            
def get_store(page: Page,keyword:str) -> list[str]:
    #word = extract(keyword)
    print(f"extracted query:{keyword}")
    path = path1 /"imsta - Android Apps on Google Play.html"
    page.goto(f"https://play.google.com/store/search?q={keyword}&c=apps")
    result = page.locator(".cXFu1")
    print(result.all_inner_texts())#内涵app名字和简短描述
    text = result.all_inner_texts()
    formatted = formatter(content=text[:5],source="google_play")
    detailed = further_description(content=formatted,source="google_play")
    return detailed

def query_app_store(page: Page, keyword:str)->list[str]:
    #word = extract(keyword)
    print(f"extracted keyword: {keyword}")
    page.goto(f"https://www.apple.com/us/search/{keyword}?src=globalnav")
    texts = page.locator(".as-search-wrapper").locator(".rf-serp-product-description")
    result = texts.all_inner_texts()
    appear = []
    for i in result[:5]:
        j = i.replace("View more","")
        appear.append(j)
    print(appear)
    formatted = formatter(content=result,source="app_store")
    detailed = further_description(content=formatted,source="google_play")
    return detailed

client_formatter = OpenAI(
    base_url="https://api.deepseek.com",
    api_key=key,
)



model = [SortResultBrowser,StoreResult]

def extract(keyword: str)->str:
        ollama_system = "You are a helpful formatter, upon given a search query, if it is not a concise word or phrase, you should return only the keyword and nothing else. If it is, return the original word/phrase."
        messages=[{"role":"system","content":f"{ollama_system}"},{"role":"user","content":f"{keyword}"}]
        word = ""
        for _ in range(3):
            print("AI extract request:", keyword)
            r = chat(
                model = "qwen3.5:4b",
                messages=messages,
                think= False
            )
            print("AI extract raw response:", r.message.content)
            if r.message.content:
                try:
                    if len(r.message.content) > 15:
                        raise ValueError
                except ValueError:
                    messages.append({"role":"user","content":"still not concise enough, try another time"})
                    continue
                word = r.message.content
                break
            else:
                messages.append({"role":"user","content":"you should say something..."})
                continue
        return word

def formatter(content: list[str], source: source_list) -> list[str]:
        result = []
        system_prompt = f"""You are a professional recommendation system data extraction agent.
            Your task is to read the web search results provided by the user and extract each piece of information clearly and separately, avoiding arbitrary merging.
            You must output strictly in the required JSON format and remove meaningless content and advertisements. Format: {prompt_example_map[source]}"""
        user_prompt = f"""
            Based on the content captured inside the `<search_results>` tag below, extract the feature data.
            <search_results>
            {content}
            </search_results>
            Please begin your extraction:
            """
        messages=[{"role":"system","content":system_prompt},{"role":"user","content":user_prompt}]
        for j in range(3):
                print(f"AI formatter request source={source} attempt={j+1}")
                response = client_formatter.chat.completions.create(
                    model="deepseek-v4-pro",
                    messages=messages,
                    response_format={"type":"json_object"},
                )
                text = response.choices[0].message.content
                print("AI formatter raw response:", text)
                if text:
                    try:
                        r = schema_map[source].model_validate_json(text)
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





def further_description(content: list[str], source: source_list) -> list[str]:
    """Repair JSON results from a single source and return the same list-of-JSON-strings format."""

    model_cls = schema_map[source]
    example_json = prompt_example_map[source]

    system_prompt = """You are a rigorous data repair agent.
    1. Inspect the description field inside the JSON. If it is meaningless, too short, or contains star rating noise, replace it with objective information.
    2. If Wikipedia does not have the entity, set "description" to "No detailed description available".
    3. Preserve the exact number of items in the JSON list. Do not delete or add items.
    4. Keep modifications concise (within 50 words) and factual.
    5. Return only the complete modified JSON string in the original schema."""

    def needs_repair(parsed_json: dict) -> bool:
        if not isinstance(parsed_json, dict):
            return True
        for entry in parsed_json.get("result", []):
            desc = entry.get("description", "")
            if len(desc.strip()) < 20 or "star" in desc.lower():
                return True
        return False

    repaired_results: list[str] = []

    for idx, item in enumerate(content):
        parsed = None
        try:
            parsed = json.loads(item)
        except json.JSONDecodeError as exc:
            print(f"⚠️ 第 {idx} 个条目 JSON 解析失败，交给大模型处理: {exc}")

        if parsed is not None and not needs_repair(parsed):
            print(f"✅ 第 {idx} 组数据无需修复，保持原样。")
            repaired_results.append(item)
            continue

        print(f"🔄 第 {idx} 组数据需要修复，启动修复流程...")
        message = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    f"Repair the following JSON and preserve its schema exactly as shown:\n{example_json}\n\n"
                    f"Input: {item}"
                ),
            },
        ]

        for attempt in range(3):
            print(f"AI further_description request index={idx} attempt={attempt+1}")
            chat_response = client_formatter.chat.completions.create(
                model="deepseek-v4-pro",
                tools=tools,
                messages=message,
                response_format={"type": "json_object"},
            )

            response_msg = chat_response.choices[0].message
            text = response_msg.content
            print("AI further_description raw response:", text)

            if response_msg.tool_calls:
                print("AI further_description tool call(s):", [tool_call.function.name for tool_call in response_msg.tool_calls])
                message.append(response_msg)
                for tool_call in response_msg.tool_calls:
                    args = tool_call.function.arguments
                    print(f"AI further_description tool call {tool_call.function.name} args:", args)
                    result = search_wiki(args)
                    print(f"Tool search_wiki result:", result)
                    message.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    })
                continue

            if not text:
                continue

            try:
                repaired = model_cls.model_validate_json(text)
                original = model_cls.model_validate_json(item)

                if get_main_list_length(repaired) != get_main_list_length(original):
                    raise ValueError("列表长度必须与原始输入一致。")

                repaired_results.append(repaired.model_dump_json())
                print(f"🎉 第 {idx} 组数据修复成功。")
                break

            except ValidationError as exc:
                print(f"⚠️ [第 {attempt + 1}/3] 格式校验失败: {exc}")
                message.append(response_msg)
                message.append({"role": "user", "content": f"The return format is incorrect, error: {exc}"})
                continue
            except ValueError as exc:
                print(f"⚠️ [第 {attempt + 1}/3] 列表长度校验失败: {exc}")
                message.append(response_msg)
                message.append({
                    "role": "user",
                    "content": (
                        "Strictly preserve the original list length. "
                        "If Wikipedia lookup fails, set description to 'No detailed description available'. "
                        "Do not remove or add items."
                    ),
                })
                continue
        else:
            print(f"❌ 第 {idx} 组数据三次尝试未修复成功，保留原始 JSON。")
            repaired_results.append(item)

    return repaired_results
                

            