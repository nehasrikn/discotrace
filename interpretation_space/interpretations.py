import re
from utils import PROJECT_ROOT_DIR, load_jsonlines
from collections import defaultdict
from dataclasses import dataclass
import os
from typing import Any


@dataclass
class Interpretation:
    post_id: str
    model: str # model that generated the interpretation
    interpretation: str
    interpretation_id: str
    embedding: Any = None
    
    ## to string
    def __str__(self):
        return f'{self.interpretation_id}: {self.interpretation}'
    
    def set_embedding(self, embedding):
        self.embedding = embedding
        
    def _repr_html_(self):
        """
        Custom HTML representation for IPython/Jupyter display
        """
        html = f"""
        <div style="border: 1px solid #ddd; border-radius: 5px; padding: 10px; margin: 10px 0; background-color: #f9f9f9;">
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 5px; font-weight: bold; width: 80px;">Model:</td>
                    <td style="padding: 5px;">{self.model}</td>
                </tr>
                <tr>
                    <td style="padding: 5px; font-weight: bold;">Interpretation:</td>
                    <td style="padding: 5px; white-space: pre-wrap;">{self.interpretation}</td>
                </tr>
            </table>
        </div>
        """
        return html
    
    
    
def extract_interpretations(numbered_list: str) -> list:
    if numbered_list.strip().upper() == 'NONE':
        return []
    description_pattern = r'\d+\.\s*(.+)'
    descriptions = re.findall(description_pattern, numbered_list)
    return descriptions


def process_interpretations(result_dir: str=f'{PROJECT_ROOT_DIR}/interpretation_space/interpretations_on_no_stupid_questions', exclude_list: list=['Llama-3.1-70B-Instruct'], question_lookup=None):
    
    results = defaultdict(list)
    for f in os.listdir(result_dir):
        # processing a single file of model-generated interpretations for a given question
        if not f.endswith('.jsonl') or any([exclude in f for exclude in exclude_list]):
            continue
        model = f.split('.jsonl')[0]
        for q in load_jsonlines(os.path.join(result_dir, f)):
            model_generated_interpretations = extract_interpretations(q['response'])
            if not model_generated_interpretations:
                # Model said NONE — use the original question as the sole interpretation
                assert question_lookup is not None, "question_lookup must be provided if model-generated interpretations are empty"
                assert type(question_lookup[q['id']]) == str, "question_lookup should map question IDs to question strings"
                
                results[q['id']].append(
                    Interpretation(
                        post_id=q['id'],
                        model=model,
                        interpretation=question_lookup[q['id']],
                        interpretation_id=f'{q["id"]}_{model}_original',
                        embedding=None
                    )
                )
            else:
                for i, interpretation in enumerate(model_generated_interpretations):
                    results[q['id']].append(
                        Interpretation(
                            post_id=q['id'], 
                            model=model, 
                            interpretation=interpretation,
                            interpretation_id=f'{q["id"]}_{model}_{i}',
                            embedding=None
                        )
                    )
    print('Processed interpretations')
    return results