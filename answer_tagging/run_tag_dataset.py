import json
import asyncio
import gc

from answer_tagging.tag_dataset import initialize, process_question, process_model_answer
from question import SubredditDataset
from utils import DATA_ROOT_DIR, PROJECT_ROOT_DIR, SCRATCH_ROOT_DIR
from tqdm.asyncio import tqdm


def load_completed_ids(output_file):
    completed = set()
    try:
        with open(output_file) as f:
            for line in f:
                if line.strip():
                    completed.add(json.loads(line)["question_id"])
    except FileNotFoundError:
        pass
    return completed


async def run_comments(dataset, rst_rstdt, action_tagger, interpretation_tagger):
    output_file = f"{PROJECT_ROOT_DIR}/answer_tagging/results/{dataset.subreddit}/{dataset.subreddit}/comments_tagged.jsonl"
    completed_ids = load_completed_ids(output_file)
    remaining = [q for q in dataset.questions if q.post_id not in completed_ids]
    print(f"Comments: {len(completed_ids)} done, {len(remaining)} remaining")

    tasks = [
        process_question(q, rst_rstdt, action_tagger, interpretation_tagger)
        for q in remaining
    ]
    with open(output_file, "a") as f:
        for coro in tqdm.as_completed(tasks, total=len(tasks)):
            result = await coro
            f.write(json.dumps(result) + "\n")


async def run_model(dataset, answers_file, model_name, rst_rstdt, action_tagger, interpretation_tagger):
    output_file = f"{PROJECT_ROOT_DIR}/answer_tagging/results/{dataset.subreddit}/{model_name}_tagged.jsonl"
    completed_ids = load_completed_ids(output_file)

    with open(answers_file) as f:
        answers = [json.loads(line) for line in f if line.strip()]

    question_map = {q.post_id: q for q in dataset.questions}

    tasks = []
    for ans in answers:
        qid = ans.get("id") or ans.get("question_id")
        if qid in completed_ids:
            continue
        question = question_map.get(qid)
        if question is None:
            print(f"Skipping unknown question id: {qid}")
            continue
        tasks.append(process_model_answer(question, ans, rst_rstdt, action_tagger, interpretation_tagger))

    print(f"Model ({model_name}): {len(completed_ids)} done, {len(tasks)} remaining")

    with open(output_file, "a") as f:
        for coro in tqdm.as_completed(tasks, total=len(tasks)):
            result = await coro
            f.write(json.dumps(result) + "\n")


async def main(tag_comments=True, tag_models=True):
    rst_rstdt, action_tagger, interpretation_tagger = initialize()

    for name in ["ScienceBasedParenting"]:
        model_name = "claude-sonnet-4.5"
        model_path = f"{PROJECT_ROOT_DIR}/model_answers/results/{name}/{model_name}.jsonl"
    
        dataset = SubredditDataset(subreddit=name, interpretation_dedupe_threshold=0.86, raw_data_dir=SCRATCH_ROOT_DIR)
        
        if tag_comments:
            await run_comments(dataset, rst_rstdt, action_tagger, interpretation_tagger)

        if tag_models:
            await run_model(dataset, model_path, model_name, rst_rstdt, action_tagger, interpretation_tagger)

        del dataset
        gc.collect()

asyncio.run(main(tag_comments=False, tag_models=True))