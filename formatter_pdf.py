from openai import OpenAI
from ollama import chat

def help_md_formatt(input: str) :
    

    client = OpenAI(
        base_url='http://localhost:11434/v1/',
        api_key='ollama',  # required but ignored
    )
    message=list()
    system_prompt = (
        "You are a helpful formatting assistant, with requirements below you need to follow:\n"
        "1. Don't overthinking.\n"
        "2. Identify and add appropriate Markdown formatting (such as headings, lists, paragraphs).\n"
        "3. Only output the final Markdown text."
    )
    message.append({"role": "system", "content": system_prompt})
    message.append({"role": "user", "content": input})



    stream = chat(
    model='qwen3.5:9b',
    messages=message,
    think=True,
    stream=True,
    )

    in_thinking = False
    answer = ""
    for chunk in stream:
        if chunk.message.thinking and not in_thinking:
            in_thinking = True
            print('Thinking:\n', end='')

        if chunk.message.thinking:
            print(chunk.message.thinking, end='')
        elif chunk.message.content:
            if in_thinking:
                print('\n\nAnswer:\n', end='')
                in_thinking = False
            print(chunk.message.content, end='')
            answer += chunk.message.content
    return answer


if __name__ == "__main__":
    input = "specifically : one of the several keyboards of an organ or harpsichord that controls a separate division of the instrument, each with its own tone color and range of pitches. b : a device or apparatus intended for manual operation"
    help_md_formatt(input)

