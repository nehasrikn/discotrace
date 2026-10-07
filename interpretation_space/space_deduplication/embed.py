from sentence_transformers import SentenceTransformer
from tqdm import tqdm
from utils import PROJECT_ROOT_DIR, load_jsonlines
from typing import List, Tuple, Dict, Union
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import os
from utils import PROJECT_ROOT_DIR
from collections import defaultdict
from question import Question
from interpretation_space.interpretations import Interpretation

class Embedder:
    def __init__(self, model_path):
        self.model = SentenceTransformer(model_path, trust_remote_code=True)
        self.model.max_seq_length = 8192
        self.model.tokenizer.padding_side = "right"
        self.INSTRUCTION_PREFIX = "Instruct: Given a question, identify other duplicate questions.\nQuery: "

    def embed(self, text):
        return self.model.encode(
            [text],
            batch_size=1,
            prompt=self.INSTRUCTION_PREFIX,
            normalize_embeddings=True
        )[0]

    def embed_question_interpretations(self, questions: List[Question], outdir: str, compute_similarity=True):
        matrices = []
        question_ids = []

        for question in tqdm(questions):
            interpretations = question.interpretations
            embeddings = [self.embed(interpretation.interpretation) for interpretation in interpretations]
            print("done")
            similarity_matrix = cosine_similarity(embeddings)
            matrices.append(similarity_matrix)
            question_ids.append(question.post_id)

        question_ids = np.array(question_ids)
        print("Saving matrices and question ids to: ", outdir)
        np.savez(f'{outdir}/similarity_matrices.npz', *matrices)
        np.save(f'{outdir}/question_ids.npy', question_ids)


if __name__ == '__main__':

    embedder = Embedder('Qwen/Qwen3-Embedding-8B')
    from question import eli5_dataset as dset

    embedder.embed_question_interpretations(dset.questions, outdir=f'{PROJECT_ROOT_DIR}/interpretation_space/space_results/{dset.subreddit}')