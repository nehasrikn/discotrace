import seaborn as sns
import matplotlib.pyplot as plt
from typing import List, Any, Tuple, Union
import pandas as pd
import json
import random
import string
from scipy.special import softmax
import numpy as np
#import tiktoken
import os
import socket
import subprocess 
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import re



PROJECT_ROOT_DIR = '.'
DATA_ROOT_DIR = PROJECT_ROOT_DIR + '/raw_data'
SCRATCH_ROOT_DIR = '.'

def get_line_count(file_path: str) -> int:
    return int(subprocess.run(f'wc -l {file_path}', shell=True, capture_output=True, text=True).stdout.split()[0]) 

def load_jsonlines(path: str) -> List[Any]:
    if not path.startswith(PROJECT_ROOT_DIR):
        path = os.path.join(PROJECT_ROOT_DIR, path)
        
    with open(path, 'r') as f:
        return [json.loads(line) for line in f.readlines()]

def write_jsonlines(l: List[Any], path: str) -> None:
    with open(path, 'w') as f:
        for entry in l:
            json.dump(entry, f)
            f.write('\n')

def load_matrices(path):
    loaded = np.load(path)
    return [loaded[key] for key in loaded]
    

def write_json(d: dict, path: str) -> None:
    if not path.startswith(DATA_ROOT_DIR):
        path = os.path.join(DATA_ROOT_DIR, path)

    with open(path, 'w') as fp:
        json.dump(d, fp)

def load_json(path: str) -> dict:
    if not path.startswith(DATA_ROOT_DIR):
        path = os.path.join(DATA_ROOT_DIR, path)

    with open(path, 'r') as json_file:
        data = json.load(json_file)
    return data

class PretrainedNLIModel:

    def __init__(self, trained_model_dir: str, cache_dir: str = 'checkpoints/hf_cache', label_map = ['E', 'N', 'C']) -> None:
        self.device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')
        self.tokenizer = PretrainedNLIModel.get_tokenizer(trained_model_dir, cache_dir)
        self.trained_model = self.get_model(trained_model_dir, cache_dir)
        self.label_map = label_map
        
    def predict(self, premise: str, hypothesis: str) -> np.ndarray:
        return self._get_prediction((premise, hypothesis))

    def predict_label(self, premise: str, hypothesis: str) -> str:
        prediction = self.predict(premise, hypothesis)
        return self.label_map[np.argmax(prediction)]

    def _get_prediction(self, inp: Union[str, Tuple[str, str]]) -> np.ndarray:
        result = self.tokenizer(
            [inp],
            padding="max_length", 
            max_length=128, 
            truncation=True, 
            return_tensors="pt"
        )
        outputs = self.trained_model(
            input_ids=result['input_ids'].clone().to(device=self.device), 
            attention_mask=result['attention_mask'].clone().to(device=self.device)
        )
        probs = softmax(outputs.logits.clone().detach().cpu().numpy(), axis=1)
        return probs[0]

    @staticmethod
    def get_tokenizer(model_path: str, hf_cache_path: str) -> AutoTokenizer:
        return AutoTokenizer.from_pretrained(
            model_path,
            cache_dir=hf_cache_path,
            use_fast=False,
            revision="main"
        )

    def get_model(self, model_path: str, hf_cache_path: str) -> AutoModelForSequenceClassification:
        print('Loading model from %s' % model_path)
        return AutoModelForSequenceClassification.from_pretrained(
            model_path,
            from_tf=bool(".ckpt" in model_path),
            cache_dir=hf_cache_path
        ).to(device=self.device)

def jaccard_similarity(list1, list2):
    s1 = set(list1)
    s2 = set(list2)
    return len(s1.intersection(s2)) / len(s1.union(s2))

class OpenAIModel:
    """
    a class the calls an openai model to generate text
    The openai key is fetched from the env variable OPENAI_API_KEY
    """
    # if not os.environ.get("OPENAI_API_KEY"):
    #     raise ValueError("OPENAI_API_KEY not set in environment variables")
    

    def __init__(self, 
                 model_name: str,
                model_details: dict=None):
        
        from openai import OpenAI
        
        self.model = model_name 
        self.model_details = model_details
        # if no model details are provided, set defaults
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        

    def generate_answer(self, messages: list[dict]):
        answer_object = self.client.chat.completions.create(
            model=self.model, 
            messages=messages,
            temperature = self.model_details['temperature'], 
            max_tokens = self.model_details['max_new_tokens'], 
            # get top_p if provided 
            top_p = self.model_details.get("top_p", 1),
        )

        return answer_object.choices[0].message.content
    
    
    def estimate_cost(self, prompt: str, completion_tokens: int, price_per_1m_prompt_tokens: float, price_per_1m_completion_tokens: float) -> float:

        encoding = tiktoken.encoding_for_model(self.model)
        prompt_tokens = len(encoding.encode(prompt))
        
        prompt_cost = (prompt_tokens / 1_000_000) * price_per_1m_prompt_tokens
        completion_cost = (completion_tokens / 1_000_000) * price_per_1m_completion_tokens
        return prompt_cost + completion_cost


def remove_markdown(text):
    text = re.sub(r'#{1,6}\s*', '', text)        # headers
    text = re.sub(r'\*{1,3}(.*?)\*{1,3}', r'\1', text)  # bold/italic
    text = re.sub(r'`{1,3}(.*?)`{1,3}', r'\1', text)    # code
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)  # bullets
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)  # numbered lists
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)  # links
    text = re.sub(r'\n{3,}', '\n\n', text)       # excess newlines
    return text.strip()