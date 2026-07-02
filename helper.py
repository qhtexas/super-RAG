from pydantic import validate_call, ValidationError
import jsonref
import json
from ollama import ChatResponse
from typing import List, Tuple, Iterator

@validate_call
def generate_function_tool(name: str, description: str, parameters: dict) -> dict:
    """
    根据提供的函数信息生成一个符合规范的工具定义。
    
    参数:
        name (str): 函数名称
        description (str): 函数描述
        parameters (dict): 函数参数的 JSON Schema 定义
        
    返回:
        dict: 符合规范的工具定义
    """
    try:
    # 使用 jsonref 处理可能存在的 $ref 引用，确保参数定义是纯净的 Python dict
        clean_parameters = json.loads(jsonref.dumps(jsonref.replace_refs(parameters)))
    
        if "$defs" in clean_parameters:
            clean_parameters.pop("$defs",None)  # 删除 $defs，确保参数定义干净无冗余
        clean_parameters.pop("title",None)  # 删除 title，确保参数定义干净无冗余    
    # 构建工具定义
        tool_definition = {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": clean_parameters
            }
        }

    except ValidationError as e:
        print(f"工具定义参数验证失败: {e}")
        return {}    
    return tool_definition

@validate_call
def output_with_stream(response) -> Tuple[str,str]:
    think = False
    think_content = ""
    answer = ""
    for chunk in response:
        if chunk.message.thinking and not think:
            think = True
            think_content += chunk.message.thinking
            print("think: ",end='')
            print(chunk.message.thinking,end="")
        if think and chunk.message.thinking:
            think_content+=chunk.message.thinking
            print(chunk.message.thinking,end="")
        elif chunk.message.content:
            print(chunk.message.content,end='')
            answer+=chunk.message.content
    return (think_content,answer)
