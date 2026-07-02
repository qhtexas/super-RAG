from ollama import chat
from pathlib import Path
from appleInc import app_store,Input
import argparse
from main import answer
from helper import output_with_stream
parser = argparse.ArgumentParser()
parser.add_argument("region",help="The Region Search is Operated",type=str)
parser.add_argument("platform",help="The Platform of Result",type=str)
parser.add_argument("input",help="The Name of App",type=str)
parser.add_argument("output",help="The Input of Search", type=str)
parser.add_argument("type",help="App, Developer, or what?",type=str)
parser.add_argument("--description",'-d',help="Discription or Exact Name?",action="store_true")
args = parser.parse_args()


def main():
    
    path = Path(__file__).parent /"detailed_guideline.md"

    with open(path,"r",encoding='utf-8') as file:
        text = file.read()
    
    if not args.description:
        app_store_result = app_store(args.output,args.region,args.platform)
        user = f"""
        You are an expert, rigorous, and objective App Store Search Algorithm Auditor who's aim is enhance our searching algorithm. 
        Your primary core objective is to evaluate the relevance, availability, and overall quality of an app returned in a search result, strictly eliminating any subjective bias. You must base your evaluation exclusively on the provided Data Context and the Official Evaluation Guidelines.

        ### 1. Data Context (Search Result)
        Please evaluate the following search result data:
        - Search Input: {args.input}
        - Search Output: {args.output}
        - Region: {args.region}
        - Platform: {args.platform}
        - Current App Store Result Details for the Output(for checking availability and Views/stars to infer intent): 
        {app_store_result}

        ### 2. Official Evaluation Guidelines
        Strictly apply the rules and decision trees outlined in the following guideline document to make your assessment:
        {text}
        
        ### 3. Output
        Write your reason in comment, and your rating in rating, then return the json object
        """
    else:
        user = f"""
        You are an expert, rigorous, and objective App Store Search Algorithm Auditor who's aim is enhance our searching algorithm. 
        Your primary core objective is to evaluate the relevance and overall quality of a description returned in a search result, strictly eliminating any subjective bias. You must base your evaluation exclusively on the provided Data Context and the Official Evaluation Guidelines.
         ### 1. Data Context (Search Result)
        Please evaluate the following search result data:
        - Search Input: {args.input}
        - Search Result Description: {args.output}
        - Region: {args.region}
        - Platform: {args.platform}

        ### 2. Official Evaluation Guidelines
        Strictly apply the rules and decision trees outlined in the following guideline document to make your assessment:
        {text}
        """
    messages = [
        {"role": "system", "content": "You are a helpful and precise auditing assistant."},
        {"role": "user", "content": user}
    ]
    
    
    response = chat(
        model="qwen3.5:9b",
        messages=messages,
        stream = True,
        format = answer.model_json_schema(),
    )
    output_with_stream(response)

if __name__ == "__main__":
    main()
    
    
    