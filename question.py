from dataclasses import dataclass
from utils import load_json, load_jsonlines, write_json, write_jsonlines, PROJECT_ROOT_DIR, DATA_ROOT_DIR, load_matrices, SCRATCH_ROOT_DIR
from process_subreddit import ingest_and_process_subreddit, Subreddit, RedditComment, RedditPost
from typing import List, Dict, Any, Optional, Callable
import pandas as pd
import numpy as np
from simple_colors import red, green, magenta
import os
from IPython.display import HTML, display
import html
from collections import namedtuple, defaultdict
from interpretation_space.interpretations import Interpretation, process_interpretations
from interpretation_space.space_deduplication.graph_dedupe import dedupe_from_similarity_matrix, select_representative_wrt_clique_dissimilarity, select_representative_wrt_clique_similarity
from tqdm import tqdm


@dataclass
class Question:
    post_id: str
    post: RedditPost
    question: str # this is the post title
    interpretations: List[Interpretation] = None # raw interpretations (not deduped)
    interpretation_space: List[Interpretation] = None # deduped interpretations
    _interpretation_lookup: Dict[str, Interpretation] = None
    embedding: Any = None
    
    def get_interpretation(self, interpretation_id: str) -> Optional[Interpretation]:
        return self._interpretation_lookup.get(interpretation_id)
    
    def set_embedding(self, embedding):
        self.embedding = embedding
    
    def display_interpretation_space(self):
        """
        Display a collection of interpretations as an HTML table
        """
        table_html = """
        <div style="margin: 20px 0;">
            <table style="width: 100%; border-collapse: collapse; border: 1px solid #ddd;">
                <thead>
                    <tr style="background-color: #f2f2f2;">
                        <th style="padding: 8px; text-align: left; border: 1px solid #ddd; width: 100px;">Model</th>
                        <th style="padding: 8px; text-align: left; border: 1px solid #ddd;">Interpretation</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for interp in self.interpretation_space:
            table_html += f"""
                    <tr>
                        <td style="padding: 8px; border: 1px solid #ddd; width: 100px;">{"-".join(interp.model.split('-')[:2])}</td>
                        <td style="padding: 8px; border: 1px solid #ddd; white-space: pre-wrap;">{interp.interpretation}</td>
                    </tr>
            """
        
        table_html += """
                </tbody>
            </table>
        </div>
        """
        
        return HTML(table_html)
    
class SubredditDataset:
    def __init__(self, subreddit: str = 'NoStupidQuestions', interpretation_dedupe_threshold=0.86, dedupe_function=select_representative_wrt_clique_dissimilarity,raw_data_dir=f'{DATA_ROOT_DIR}'):
        self.subreddit = subreddit
        self.subreddit_data = Subreddit.load_object(
            os.path.join(raw_data_dir, f'{self.subreddit}/{self.subreddit}_processed.pkl')
        )
        print(f'Loaded r/{self.subreddit} data')
        
        selected_questions = load_jsonlines(f"data_selection/{self.subreddit}/questions_{self.subreddit}.jsonl")
        
        #LOAD MODEL-GENERATED INTERPRETATIONS
        interpretations = process_interpretations(
            result_dir=f'{PROJECT_ROOT_DIR}/interpretation_space/space_results/{self.subreddit}/interpretations_on_{self.subreddit}',
            question_lookup={q['id']: q['question'] for q in selected_questions}
        )
        questions = []
        ## LOAD QUESTIONS
        for q in selected_questions:
            post = self.subreddit_data.posts[q['id']]
            questions.append(
                Question(
                    post_id=post.id,
                    post=post,
                    question=post.title,
                    interpretations=interpretations[q['id']],
                    _interpretation_lookup={i.interpretation_id: i for i in interpretations[q['id']]}
                )
            )
        self.questions = questions
        self.questions_lookup = {q.post_id: q for q in questions}
        print('Loaded {} questions'.format(len(self.questions)))
        
        if interpretation_dedupe_threshold:
            #### COMPUTE INTERPRETATION SPACE ####
            self.identify_interpretation_spaces(
                matrices_path=f"{PROJECT_ROOT_DIR}/interpretation_space/space_results/{self.subreddit}/similarity_matrices.npz",
                representative_function=dedupe_function,
                threshold=interpretation_dedupe_threshold
            )
    
    def __iter__(self):
        return iter(self.questions)
    
    def __len__(self):
        return len(self.questions)
    
    def __getitem__(self, idx):
        return self.questions[idx]
        
    def identify_interpretation_spaces(
        self,
        matrices_path: str,
        representative_function: Callable,
        threshold: float = 0.86
    ):
        loaded = np.load(matrices_path)
        similarity_matrices = [loaded[f'arr_{i}'] for i in range(len(loaded.files))]
        
        for i, question in enumerate(self.questions):
            deduped_interpretations = dedupe_from_similarity_matrix(
                similarity_matrices[i], 
                question, 
                representative_function=representative_function,
                threshold=threshold
            )
            question.interpretation_space = deduped_interpretations
    
    
from functools import lru_cache


@lru_cache(maxsize=None)
def load_dataset(name):
    return SubredditDataset(subreddit=name, interpretation_dedupe_threshold=0.86, raw_data_dir=SCRATCH_ROOT_DIR)
    
# asklinguistics_dataset = SubredditDataset(subreddit='asklinguistics', interpretation_dedupe_threshold=0.906)
#NoStupidQuestions_dataset = SubredditDataset(subreddit='NoStupidQuestions', interpretation_dedupe_threshold=0.86)
#AskHistorians_dataset = SubredditDataset(subreddit='AskHistorians', interpretation_dedupe_threshold=0.86, raw_data_dir=fSCRATCH_ROOT_DIR)
# AskEconomics_dataset = SubredditDataset(subreddit='AskEconomics', interpretation_dedupe_threshold=None, raw_data_dir=fSCRATCH_ROOT_DIR)
# asklinguistics_dataset = SubredditDataset(subreddit='asklinguistics', interpretation_dedupe_threshold=None, raw_data_dir=fSCRATCH_ROOT_DIR)
# beyondthebump_dataset = SubredditDataset(subreddit='beyondthebump', interpretation_dedupe_threshold=None, raw_data_dir=fSCRATCH_ROOT_DIR)
# history_dataset = SubredditDataset(subreddit='history', interpretation_dedupe_threshold=None, raw_data_dir=fSCRATCH_ROOT_DIR)
# OutOfTheLoop_dataset = SubredditDataset(subreddit='OutOfTheLoop', interpretation_dedupe_threshold=None, raw_data_dir=fSCRATCH_ROOT_DIR)
# ScienceBasedParenting_dataset = SubredditDataset(subreddit='ScienceBasedParenting', interpretation_dedupe_threshold=None, raw_data_dir=fSCRATCH_ROOT_DIR)
# eli5_dataset = SubredditDataset(subreddit='explainlikeimfive', interpretation_dedupe_threshold=None, raw_data_dir=fSCRATCH_ROOT_DIR)