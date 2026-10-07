from functools import partial

from tqdm import tqdm
from profanity_check import predict, predict_prob 
# from process_subreddit import Subreddit, RedditPost, RedditComment
import re
from typing import List


thread_length = lambda post, min_comments, max_comments: len(post.filtered_comments) > max_comments or len(post.filtered_comments) < min_comments
comment_body_empty = lambda comment: comment.body == "[removed]"
low_comment_quality = lambda comment, threshold: comment.score < threshold
has_nsfw_or_profanity = lambda post, threshold: predict_prob([post.title])[0] > threshold
has_reddit_terms = lambda post: any(tok in {"redditors", "redditor", "reddit", "subreddit", "upvote", "downvote", "karma"} for tok in re.findall(r"\b\w+\b", post.title.lower()))


from functools import partial


FIRST_PERSON = {
    "i", "me", "my", "mine", "we", "our", "ours", "us"
}

SECOND_PERSON = {
    "you", "your", "yours"
}

RELATIONS = {
    "husband", "wife", "boyfriend", "girlfriend", "bf", "gf",
    "mom", "dad", "mother", "father", "son", "daughter",
    "friend", "boss", "coworker", "teacher", "neighbor"
}

VALIDATION_PATTERNS = [
    r"\bis this (okay|enough|bad|weird|normal)\b",
    r"\bam i (wrong|weird|bad|crazy|an asshole)\b",
    r"\bshould i\b",
    r"\bwhat should i do\b",
    r"\banyone else",
    r"\bopinion",
]

DEICTIC = {"this", "that", "these", "those"}

def is_not_generic(
    post,
    pronoun_threshold=1,
    relation_threshold=1,
    allow_second_person=True,
):
    t = post.title.lower()
    tokens = re.findall(r"\b\w+\b", t)
    pronoun_count = sum(tok in FIRST_PERSON for tok in tokens)
    second_person = sum(tok in SECOND_PERSON for tok in tokens)
    relation_count = sum(tok in RELATIONS for tok in tokens)
    validation_hit = any(re.search(pat, t) for pat in VALIDATION_PATTERNS)
    deictic_hit = any(tok in DEICTIC for tok in tokens)

    reasons_not_generic = [
        not allow_second_person and second_person > 0,
        validation_hit,
        pronoun_count >= pronoun_threshold,
        relation_count >= relation_threshold,
        pronoun_count > 0 and deictic_hit,
    ]
    return any(reasons_not_generic)

def is_validation_seeking(post) -> bool:
    t = post.title.lower()
    patterns = [
        r"^does (anybody|anyone) else", 
        r"^am i the only one",
        r"^is it (normal|weird|okay|bad) to",
        r"^is it just me"
    ]
    return any(re.search(p, t) for p in patterns)

def is_poll_or_survey(post) -> bool:
    t = post.title.lower()
    poll_patterns = [
        r"^what (is|are) your favorite",
        r"^what are some (good|bad|things)",
        r"^who (here|is|has)",
        r"your (opinion|thoughts) on"
    ]
    return any(re.search(p, t) for p in poll_patterns)

def is_normative_or_advice(post) -> bool:
    t = post.title.lower()
    
    permission_words = [
        r"\b(is|was) it (okay|ok|acceptable|appropriate|rude|disrespectful)\b",
        r"\b(is|was) it (weird|normal|wrong|fair)\b",
        r"\bdo i have to\b",
        r"\bam i allowed to\b"
    ]
    
    advice_words = [
        r"\bshould (i|we|they|you|someone)\b",
        r"\bought to\b",
        r"\bwho is in the (wrong|right)\b",
        r"\bis it my responsibility\b"
    ]
    
    moral_venting = [
        r"^why (is it|is it considered|do people think) (okay|ok|acceptable|right to)\b",
        r"^why is (.*) allowed to\b"
    ]

    combined_patterns = permission_words + advice_words + moral_venting
    return any(re.search(p, t) for p in combined_patterns)

def has_multiple_statements_or_questions(post) -> bool:
    t = post.title.strip()
    question_marks = t.count("?")
    
    sentences = [s.strip() for s in re.split(r'[.!?]+', t) if s.strip()]
    
    multi_clause_separators = len(re.findall(r'[;–—]|\.\s', t))
    
    if question_marks >= 2:
        return True
    
    # Multiple sentences (e.g. "I did X. Now Y is happening. What do I do?")
    if len(sentences) >= 3:
        return True
    
    if multi_clause_separators >= 2:
        return True
    
    return False

def should_filter_post(post, post_filters, comment_filters, use_comment_filters_for_post_filtering=False):
    import copy
    p = copy.deepcopy(post)
    p.filtered_comments = (
        [c for c in p.top_level_comments if not any(f(c) for f in comment_filters)]
        if use_comment_filters_for_post_filtering
        else p.top_level_comments
    )
    should_filter = any(f(p) for f in post_filters)
    del p
    return should_filter
    

def filter_subreddit(
    subreddit,
    post_filters=[], 
    comment_filters=[],
    use_comment_filters_for_post_filtering=False,
):
    filtered_posts = []
    for post in tqdm(subreddit.posts.values(), total=len(subreddit.posts), desc="Filtering posts"):
        post.filtered_comments = (
            [c for c in post.top_level_comments if not any(f(c) for f in comment_filters)]
            if use_comment_filters_for_post_filtering
            else post.top_level_comments
        )
        if any(f(post) for f in post_filters):
            continue
        filtered_posts.append(post)
    
    return filtered_posts