import json
import asyncio
from tqdm.asyncio import tqdm

from answer_tagging.action_tagging import ActionTagger
from answer_tagging.interpretation_tagging import InterpretationTagger
from answer_tagging.rst import RSTSegmenter
from answer_tagging.answering_utils import highlight_spans
from process_subreddit import RedditComment, RedditPost


semaphore = asyncio.Semaphore(5)


def initialize(provider="openai", parser_version="rstdt", semaphore_limit=5):
    global semaphore
    semaphore = asyncio.Semaphore(semaphore_limit)
    rst_rstdt = RSTSegmenter(parser_version=parser_version)
    action_tagger = ActionTagger(provider=provider)
    interpretation_tagger = InterpretationTagger(provider=provider)
    return rst_rstdt, action_tagger, interpretation_tagger


async def process_comment(question, comment, rst_rstdt, action_tagger, interpretation_tagger):
    async with semaphore:
        segments = rst_rstdt.segment(comment)
        tagged = await action_tagger.tag_comment(post=question.post, comment=comment, segments=segments)
        interpretations = "\n".join(
            json.dumps({"interpretation_id": interp.interpretation_id, "text": interp.interpretation})
            for interp in question.interpretation_space
        )
        tagged_interps = await interpretation_tagger.tag(
            post=question.post,
            interpretations=interpretations,
            full_answer=comment,
            tagged_segments=tagged
        )
        
        if "RedditComment" in str(type(comment)): # hacky
            return {
                "comment_id": comment.id,
                "comment_text": comment.body,
                "tagged_segments": tagged_interps
            }
        else:
            return {
                "comment_id": None,
                "comment_text": comment,
                "tagged_segments": tagged_interps
            }


async def process_question(question, rst_rstdt, action_tagger, interpretation_tagger):
    comments = question.post.filtered_comments()

    tasks = [
        process_comment(question, comment, rst_rstdt, action_tagger, interpretation_tagger)
        for comment in comments
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    successes = []
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            import traceback
            traceback.print_exception(type(r), r, r.__traceback__)
        else:
            successes.append(r)

    return {
        "question_id": question.post.id,
        "question_text": question.post.title,
        "comments": successes
    }


async def run(posts, rst_rstdt, action_tagger, interpretation_tagger, output_file="results.jsonl"):
    tasks = [
        process_question(q, rst_rstdt, action_tagger, interpretation_tagger)
        for q in posts
    ]
    results = []
    with open(output_file, "w") as f:
        for coro in tqdm.as_completed(tasks, total=len(tasks)):
            result = await coro
            f.write(json.dumps(result) + "\n")
            results.append(result)
    return results


async def process_model_answer(question, answer_dict, rst_rstdt, action_tagger, interpretation_tagger):
    answer_text = answer_dict["answer"]
    async with semaphore:
        segments = rst_rstdt.segment(answer_text)
        tagged = await action_tagger.tag_comment(post=question.post, comment=answer_text, segments=segments)
        interpretations = "\n".join(
            json.dumps({"interpretation_id": interp.interpretation_id, "text": interp.interpretation})
            for interp in question.interpretation_space
        )
        tagged_interps = await interpretation_tagger.tag(
            post=question.post,
            interpretations=interpretations,
            full_answer=answer_text,
            tagged_segments=tagged
        )
        return {
            "question_id": question.post.id,
            "question_text": question.post.title,
            "comments": [{
                "comment_id": answer_dict["id"],
                "comment_text": answer_text,
                "tagged_segments": tagged_interps
            }]
        }


async def run_model_answers(questions, answers_file, rst_rstdt, action_tagger, interpretation_tagger, output_file="model_tagged.jsonl"):
    with open(answers_file) as f:
        answers = [json.loads(line) for line in f if line.strip()]

    question_map = {q.post.id: q for q in questions}

    tasks = []
    for ans in answers:
        qid = ans.get("id") or ans.get("question_id")
        question = question_map.get(qid)
        if question is None:
            print(f"Skipping unknown question id: {qid}")
            continue
        tasks.append(process_model_answer(question, ans, rst_rstdt, action_tagger, interpretation_tagger))

    results = []
    with open(output_file, "w") as f:
        for coro in tqdm.as_completed(tasks, total=len(tasks)):
            result = await coro
            f.write(json.dumps(result) + "\n")
            results.append(result)
    return results