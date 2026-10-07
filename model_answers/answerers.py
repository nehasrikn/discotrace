import json
from abc import ABC, abstractmethod
import argparse
import sys
import boto3
import openai
import anthropic

from utils import remove_markdown
from tqdm import tqdm
from utils import load_jsonlines, write_jsonlines
from model_answers.community_guidelines import community_guidelines

SUBREDDIT_EXPLANATIONS = {
    "AskHistorians": "users to ask questions about history and get detailed answers from knowledgeable historians",
    "NoStupidQuestions": "users to casually ask questions about general knowledge or any topic and get answers",
    "AskEconomics": "users to ask questions about economic theory, research, and policy and get answers rooted in economic theory and empirical research",
    "asklinguistics": "users to ask questions about linguistics and get answers from knowledgeable linguists",
    "history": "users to to discuss history",
    "OutOfTheLoop": "users to ask questions about current events, pop culture, or internet trends they feel out of the loop on and get answers",
    "ScienceBasedParenting": "users to ask questions related to parenting and receive answers based on science, share relevant research, and discuss existing scientific journalism",
    "beyondthebump": "users to discuss pregnancy, childbirth, and early parenting experiences",
}


def load_prompts(prompt_file: str) -> dict:
    with open(prompt_file) as f:
        return json.load(f)

def format_prompt(template: str, question: str, **kwargs) -> str:
    return template.format(question=question, **kwargs)


class BaseAnswerer(ABC):
    @abstractmethod
    def answer(self, prompt_prefix: str, question: str, max_tokens: int = 1000) -> str:
        pass

class AnthropicAnswerer(BaseAnswerer):
    def __init__(self, model: str = "claude-sonnet-4-20250514", api_key: str | None = None):
        self.model = model
        self.client = anthropic.Anthropic(api_key=api_key)

    def answer(self, prompt_prefix: str, question: str, max_tokens: int = 1000) -> str:
        kwargs = dict(
            model=self.model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": question}],
        )
        if prompt_prefix:
            kwargs["system"] = [
                {"type": "text", "text": prompt_prefix, "cache_control": {"type": "ephemeral"}}
            ]
        response = self.client.messages.create(**kwargs)
        return response.content[0].text

class OpenAIAnswerer(BaseAnswerer):
    def __init__(self, model: str = "gpt-4o", api_key: str | None = None):
        self.model = model
        self.client = openai.OpenAI(api_key=api_key)

    def answer(self, prompt_prefix: str, question: str, max_tokens: int = 1000) -> str:
        messages = []
        if prompt_prefix:
            messages.append({"role": "system", "content": prompt_prefix})
        messages.append({"role": "user", "content": question})
        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=messages,
        )
        return response.choices[0].message.content


class BedrockAnswerer(BaseAnswerer):
    def __init__(self, model: str = "anthropic.claude-3-sonnet-20240229-v1:0", region: str = "us-east-1"):
        self.model = model
        self.client = boto3.client("bedrock-runtime", region_name=region)

    def answer(self, prompt_prefix: str, question: str, max_tokens: int = 1000) -> str:
        kwargs = dict(
            modelId=self.model,
            messages=[{"role": "user", "content": [{"text": question}]}],
            inferenceConfig={"maxTokens": max_tokens},
        )
        if prompt_prefix:
            kwargs["system"] = [{"text": prompt_prefix}]
        response = self.client.converse(**kwargs)
        return response["output"]["message"]["content"][0]["text"]
    
    
def process_open_source_hf_fewshot(question_file: str):
    results = load_jsonlines(question_file)
    results_processed = []
    for record in tqdm(results, desc="Processing fewshot answers"):
        results_processed.append({
            "id": record["id"],
            "raw_answer": record["response"],
            "answer": remove_markdown(record["response"]),
        })
    output_file = question_file.replace(".jsonl", "_processed.jsonl")
    write_jsonlines(results_processed, output_file)
    
    
    
if __name__ == "__main__":
    
    # process_open_source_hf_fewshot("/fs/clip-projects/rlab/nehasrik/bad-qa/model_answers/results/ScienceBasedParenting/Qwen3-32B.jsonl")

    parser = argparse.ArgumentParser(description="Run answerers on a JSONL file of questions.")
    parser.add_argument("input_file", help="Path to JSONL file (each line: {\"question\": \"...\"})")
    parser.add_argument("--provider", choices=["openai", "bedrock", "anthropic"], default="openai")
    parser.add_argument("--model", default=None, help="Model name/ID (defaults per provider)")
    parser.add_argument("--max-tokens", type=int, default=1000)
    parser.add_argument("--output-file", default=None, help="Output JSONL path (default: stdout)")
    parser.add_argument("--prompt-file", default="prompts.json", help="Path to prompt templates JSON file")
    parser.add_argument("--prompt-key", default=None, help="Top-level key in prompts.json (e.g. answer_vanilla)")
    parser.add_argument("--prompt-type", default="zero_shot", help="Sub-key under prompt-key (e.g. zero_shot, followup)")
    parser.add_argument("--prompt-vars", default=None, help='Extra template variables as JSON string, e.g. \'{"subreddit": "AskHistorians"}\'')

    args = parser.parse_args()
    
    # Load prompt template if specified
    prompt_template = None
    if args.prompt_key:
        prompts = load_prompts(args.prompt_file)
        prompt_template = prompts[args.prompt_key][args.prompt_type]
        if isinstance(prompt_template, str):
            print(f"Using prompt [{args.prompt_key}][{args.prompt_type}]: {prompt_template[:80]}...", file=sys.stderr)
        else:
            print(f"Using prompt [{args.prompt_key}][{args.prompt_type}] (system/user split)", file=sys.stderr)

    extra_vars = json.loads(args.prompt_vars) if args.prompt_vars else {}

    if "subreddit" in extra_vars:
        if "subreddit_explanation" not in extra_vars:
            extra_vars["subreddit_explanation"] = SUBREDDIT_EXPLANATIONS[extra_vars["subreddit"]]
        if "community_guidelines" not in extra_vars:
            extra_vars["community_guidelines"] = community_guidelines[extra_vars["subreddit"]]
    
    if args.provider == "openai":
        answerer = OpenAIAnswerer(model=args.model)
    elif args.provider == "anthropic":
        answerer = AnthropicAnswerer(model=args.model)
    else:
        answerer = BedrockAnswerer(model=args.model)
            
    with open(args.input_file) as f:
        lines = [l.strip() for l in f if l.strip()]

    out = open(args.output_file, "w") if args.output_file else sys.stdout

    for line in tqdm(lines, desc=f"Answering ({args.model})"):
        record = json.loads(line)
        question = record["question"]
        
        if prompt_template:
            if isinstance(prompt_template, dict):
                # New format: {"system": "...", "user": "..."}
                system_prompt = format_prompt(prompt_template["system"], question=question, **extra_vars)
                user_prompt = format_prompt(prompt_template["user"], question=question, **extra_vars)
                answer = answerer.answer(system_prompt, user_prompt, max_tokens=args.max_tokens)
            else:
                # Old format: single string with {question} embedded
                formatted = format_prompt(prompt_template, question=question, **extra_vars)
                answer = answerer.answer("", formatted, max_tokens=args.max_tokens)
        else:
            answer = answerer.answer("", question, max_tokens=args.max_tokens)
        
        record["raw_answer"] = answer
        record["answer"] = remove_markdown(answer)
        record["model"] = args.model
        if args.prompt_key:
            record["prompt_key"] = args.prompt_key
            record["prompt_type"] = args.prompt_type
        out.write(json.dumps(record) + "\n")
        out.flush()

    if args.output_file:
        out.close()