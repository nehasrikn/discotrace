from filter_subreddit import has_multiple_statements_or_questions, is_normative_or_advice, is_poll_or_survey, is_validation_seeking, thread_length, comment_body_empty, low_comment_quality, has_nsfw_or_profanity, is_not_generic, has_reddit_terms
from functools import partial


SUBREDDIT_FILTERS = {
    "NoStupidQuestions": {
        "posts": [
            partial(thread_length, min_comments=5, max_comments=18),
            partial(is_not_generic, pronoun_threshold=1, allow_second_person=True),
            partial(has_nsfw_or_profanity, threshold=0.06),
            has_reddit_terms,
            is_validation_seeking,
            is_poll_or_survey,
            is_normative_or_advice,
            has_multiple_statements_or_questions,
        ],
        "comments": [
            comment_body_empty,
            partial(low_comment_quality, threshold=3),
        ]
    },
    "AskHistorians": {
        "posts": [
            partial(thread_length, min_comments=5, max_comments=12),
            partial(is_not_generic, allow_second_person=False),
            partial(has_nsfw_or_profanity, threshold=0.8),
            has_reddit_terms,
            has_multiple_statements_or_questions,
        ],
        "comments": [
            comment_body_empty,
            partial(low_comment_quality, threshold=3),
        ]
    },
    "asklinguistics": {
        "posts": [
            partial(thread_length, min_comments=5, max_comments=15),
            partial(is_not_generic, allow_second_person=False),
            partial(has_nsfw_or_profanity, threshold=0.8),
            has_reddit_terms,
            has_multiple_statements_or_questions,
        ],
        "comments": [
            comment_body_empty,
            partial(low_comment_quality, threshold=2),
        ]
    },
    "history": {
        "posts": [
            partial(thread_length, min_comments=5, max_comments=12),
            partial(is_not_generic, allow_second_person=False),
            partial(has_nsfw_or_profanity, threshold=0.8),
            has_reddit_terms,
            has_multiple_statements_or_questions,
        ],
        "comments": [
            comment_body_empty,
            partial(low_comment_quality, threshold=3),
        ]
    },
    "AskEconomics": {
        "posts": [
            partial(thread_length, min_comments=5, max_comments=30),
            partial(is_not_generic, allow_second_person=False),
            partial(has_nsfw_or_profanity, threshold=0.8),
            has_reddit_terms,
            has_multiple_statements_or_questions,
        ],
        "comments": [
            comment_body_empty,
            partial(low_comment_quality, threshold=2),
        ]
    },
    "OutOfTheLoop": {
        "posts": [
            partial(thread_length, min_comments=5, max_comments=12),
            partial(is_not_generic, allow_second_person=False),
            partial(has_nsfw_or_profanity, threshold=0.8),
            has_reddit_terms,
            has_multiple_statements_or_questions,
        ],
        "comments": [
            comment_body_empty,
            partial(low_comment_quality, threshold=3),
        ]
    },
    "ScienceBasedParenting": {
        "posts": [
            partial(thread_length, min_comments=4, max_comments=20),
            partial(is_not_generic, allow_second_person=False),
            partial(has_nsfw_or_profanity, threshold=0.8),
            has_reddit_terms,
            has_multiple_statements_or_questions,
        ],
        "comments": [
            comment_body_empty,
            partial(low_comment_quality, threshold=3),
        ]
    },
    "beyondthebump": {
        "posts": [
            partial(thread_length, min_comments=5, max_comments=12),
            partial(is_not_generic, allow_second_person=False),
            partial(has_nsfw_or_profanity, threshold=0.95),
            lambda post: len(post.title.split()) < 6,
            has_reddit_terms,
        ],
        "comments": [
            comment_body_empty,
            partial(low_comment_quality, threshold=3),
        ]
    },
    "explainlikeimfive": {
        "posts": [
            partial(thread_length, min_comments=5, max_comments=15),
            partial(is_not_generic, pronoun_threshold=1, allow_second_person=True),
            partial(has_nsfw_or_profanity, threshold=0.06),
            has_reddit_terms,
            has_multiple_statements_or_questions,
        ],
        "comments": [
            comment_body_empty,
            partial(low_comment_quality, threshold=3),
        ]
    },
}