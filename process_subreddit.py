import json
from tqdm import tqdm
from simple_colors import yellow, green, red, magenta
import re
import os
import subprocess
from collections import defaultdict
from typing import List
from dataclasses import dataclass, field
from utils import load_jsonlines, get_line_count, PROJECT_ROOT_DIR, DATA_ROOT_DIR
from subreddit_filters import SUBREDDIT_FILTERS
import dill as pickle

@dataclass
class RedditComment:
    id: str
    link_id: str
    parent_id: str
    score: int
    author: str
    body: str
    subreddit_id: str
    op_reply: 'RedditComment' = None
    
    def __post_init__(self):
        if self.parent_id is not None:
            parent_post_type, self.parent_post_id = self.parent_id.split('_')
            self.is_top_level = parent_post_type == 't3'
            self.is_reply = parent_post_type == 't1'
    
    @property
    def has_author(self):
        return self.author != '[deleted]'
    
    @property
    def has_op_reply(self):
        return self.op_reply is not None
    
    def set_op_reply(self, op_reply):
        self.op_reply = op_reply
    
    @property
    def is_self_contained(self):
        return len(self.body) > 50 # from followupQG
    
    def pretty_print(self):
        print(f'[{self.id}] ({self.score} ⬆️)', yellow(self.body))
        if self.has_op_reply:
            # check if info_need is set
            if hasattr(self, 'info_need'):
                print(f'[OP Reply] {self.info_need}:', red(self.op_reply.body))
            else:
                print('[OP Reply]:', red(self.op_reply.body))
        print()
        
    def set_op_reply_information_need(self, model_prediction):
        self.info_need = model_prediction
        
@dataclass
class RedditPost:
    id: str
    title: str
    score: int
    url: str
    author: str
    num_comments: int
    selftext: str
    subreddit_id: str
    over_18: bool
    top_level_comments: List[RedditComment] = field(default_factory=list) # these are all comments
    has_op_reply: bool = False
    subreddit_name: str = None
    
    # post init, set up comment lookup
    def __post_init__(self):
        self.comment_lookup = {c.id: c for c in self.top_level_comments}
        # these are filtered comments! not used in badq project (top_level_comments used there)
    
    @property
    def has_author(self):
        return self.author != '[deleted]'
    
    @property
    def comments_with_op_replies(self):
        return [c for c in self.top_level_comments if c.has_op_reply]
    
    @property
    def comments_with_need_signaled_in_op_reply(self):
        return [c for c in self.comments_with_op_replies if c.info_need != 'unrelated']
    
    @property
    def has_comments_with_op_replies(self):
        return any([c.has_op_reply for c in self.top_level_comments])
    
    def pretty_print(self, only_comments_with_op_replies=False, display_post_text=False):
        print(f'[{self.id}] ({self.score})', green(self.title, ['bold']))
        if display_post_text:
            print(magenta(self.selftext))
        print('----------------------------------------------------------------------------------------')
        
        comments = self.top_level_comments
        
        for i, c in enumerate(comments):
            if only_comments_with_op_replies and not c.has_op_reply:
                continue
            c.pretty_print()
            
    def get_comment(self, comment_id):
        return self.comment_lookup.get(comment_id)
    
    def filtered_comments(self, filter_functions=[]):
        if not filter_functions:
            filter_functions = SUBREDDIT_FILTERS[self.subreddit_name]['comments']
        return [c for c in self.top_level_comments if not any(f(c) for f in filter_functions)]
    
class Subreddit:
    
    def __init__(self, subreddit_name, submission_file, comment_file, require_information_seeking=True):
        self.subreddit_name = subreddit_name
        self.submission_file = submission_file
        self.comment_file = comment_file
        self.posts = {} # id -> RedditPost
        self.top_level_comments_eligible_for_op_replies = None
        self.filters = SUBREDDIT_FILTERS[subreddit_name] # this has posts and comments
        self.require_information_seeking = require_information_seeking
    
    @property
    def posts_with_op_replies(self):
        return [p for _,p in self.posts.items() if p.has_comments_with_op_replies]
    
    @staticmethod
    def post_based_filter(post_json, require_information_seeking=True):
        criteria = [
            post_json['title'] == '[deleted by user]',
            post_json['over_18'],
            post_json['score'] < 5,
            len(post_json['title'].split()) < 4,
        ]
        if require_information_seeking:
            criteria.append(not Subreddit.surface_form_is_information_seeking(post_json['title']))
        if any(criteria):
            return True
        return False
    
    @staticmethod
    def surface_form_is_information_seeking(string): 
        has_question_word = re.match(r'^(who|which|what|where|why|how|when|whom|whose|is|do|could|would|should|did|can|will|has|had|might|must|may|shall|does|are|was|were|have)', string.lower().strip(), re.I)
        ends_with_question_mark = string.endswith("?")
        long_enough = len(string.split()) > 3
        
        if has_question_word and ends_with_question_mark and long_enough:
            return True
        return False
    
    def filter_posts(self, outfile_path):
        """
        Filter posts based on post-only criteria and write to a new file
        """
        total_posts = get_line_count(self.submission_file)
        num_filtered_posts = 0
        with open(self.submission_file, 'r') as infile, open(outfile_path, 'w') as jsonl_file:
            for line in tqdm(infile, total=total_posts):
                post = json.loads(line)
                if Subreddit.post_based_filter(post, require_information_seeking=self.require_information_seeking):
                    continue
                jsonl_file.write(json.dumps(post) + '\n')
                num_filtered_posts += 1
        print(f'Written {num_filtered_posts} posts to {outfile_path}')
        
    def load_filtered_posts(self, filtered_posts_file):
        with open(filtered_posts_file, 'r') as jsonl_file:
            for line in tqdm(jsonl_file, total=get_line_count(filtered_posts_file)):
                post = RedditPost(**{k:v for k, v in json.loads(line).items() if k in RedditPost.__annotations__}, subreddit_name=self.subreddit_name)
                self.posts[post.id] = post
        print(f"Loaded {len(self.posts)} filtered posts")
        
    def filter_comments(self):
        """
        Only keep top level comments that are replies to filtered posts
        """
        top_level_comments_eligible_for_op_replies = {}
        total_comments = get_line_count(self.comment_file)
        with open(self.comment_file, 'r') as file:
            for line in tqdm(file, total=total_comments):
                comment = RedditComment(**{k:v for k, v in json.loads(line).items() if k in RedditComment.__annotations__})
                if comment.is_top_level and comment.parent_post_id in self.posts.keys() and comment.body != '[deleted]':
                    self.posts[comment.parent_post_id].top_level_comments.append(comment)
                    # if top level comment AND post's author is not deleted and is "self contained (followupQG)"
                    if self.posts[comment.parent_post_id].has_author and comment.is_self_contained:
                        top_level_comments_eligible_for_op_replies[comment.id] = comment.parent_post_id
            print(f"Number of top level comments eligible for OP replies: {len(top_level_comments_eligible_for_op_replies)}")
        
        self.top_level_comments_eligible_for_op_replies = top_level_comments_eligible_for_op_replies
    
    @staticmethod
    def save_object(filename, processor_object):
        with open(filename, 'wb') as outp:
            pickle.dump(processor_object, outp, pickle.HIGHEST_PROTOCOL)
    
    @staticmethod
    def load_object(filename):
        with open(filename, 'rb') as inp:
            obj = pickle.load(inp)
            for p in obj.posts.values():
                p.__post_init__()
            return obj
    
    def load_op_reply_model_predictions(self, filename):
        op_predictions = load_jsonlines(filename)
        
        results = defaultdict(list)
        for example in load_jsonlines(filename):
            results[example['post_id']].append(example['response'].split('[END]')[0].strip())
        
        for post_id, labels in results.items():
            for comment_id, _ in enumerate(self.posts[post_id].comments_with_op_replies):
                self.posts[post_id].comments_with_op_replies[comment_id].set_op_reply_information_need(labels[comment_id])
    
    def get_posts_with_needs_signaled(self) -> List[RedditPost]:
        return [p for _, p in self.posts.items() if p.comments_with_need_signaled_in_op_reply]

    
    def find_op_replies(self):
        assert hasattr(self, 'top_level_comments_eligible_for_op_replies')

        with open(self.comment_file, 'r') as file:
            # now go through comments and find OP reply to top level comments
            for line in tqdm(file, total=get_line_count(self.comment_file)):
                comment = RedditComment(**{k:v for k, v in json.loads(line).items() if k in RedditComment.__annotations__})
    
                is_reply_to_top_level_comment = comment.parent_post_id in self.top_level_comments_eligible_for_op_replies.keys()                    
                
                if comment.is_reply and is_reply_to_top_level_comment:
                    post_has_author = self.posts[self.top_level_comments_eligible_for_op_replies[comment.parent_post_id]].has_author
                    comment_posted_by_op = comment.author == self.posts[self.top_level_comments_eligible_for_op_replies[comment.parent_post_id]].author
                    if post_has_author and comment_posted_by_op:
                        # find the right top level comment and set the op reply
                        found_top_level_comment = False
                        for c in self.posts[self.top_level_comments_eligible_for_op_replies[comment.parent_post_id]].top_level_comments:
                            if c.id == comment.parent_post_id:
                                c.set_op_reply(comment)
                                found_top_level_comment = True
                                break
                        assert found_top_level_comment
        
        print(f"Number of posts with top level comments with OP replies: {len(set([v for k, v in self.top_level_comments_eligible_for_op_replies.items()]))}")

def ingest_and_process_subreddit(subreddit_name, submission_file, comment_file, filtered_posts_file, pkl_outfile, require_information_seeking=True):
    subreddit = Subreddit(subreddit_name, submission_file, comment_file, require_information_seeking=require_information_seeking)
    subreddit.filter_posts(filtered_posts_file)
    subreddit.load_filtered_posts(filtered_posts_file)
    subreddit.filter_comments()
    subreddit.find_op_replies()
    Subreddit.save_object(pkl_outfile, subreddit)
    print(f"Saved processed subreddit to {pkl_outfile}")
    
from IPython.display import HTML, display
import html

def pretty_print_collapsible(post: RedditPost):
    """
    Creates a collapsible section for a Reddit post with Solarized Dark theme.
    
    Args:
        post: Reddit post object with title, body, and comments
        
    Returns:
        HTML object with collapsible content
    """
    # Solarized Dark color palette
    colors = {
        'base03': '#002b36',  # background
        'base02': '#073642',  # background highlights
        'base01': '#586e75',  # comments
        'base00': '#657b83',  # body text
        'base0': '#839496',   # primary content
        'base1': '#93a1a1',   # emphasized content
        'base2': '#eee8d5',   # background highlights
        'base3': '#fdf6e3',   # background
        'yellow': '#b58900',  # headers
        'orange': '#cb4b16',  # keywords
        'red': '#dc322f',     # variables
        'magenta': '#d33682', # values
        'violet': '#6c71c4',  # emphasize
        'blue': '#268bd2',    # primary
        'cyan': '#2aa198',    # strings
        'green': '#859900'    # success
    }
    
    # Escape HTML in post content to avoid rendering issues
    post_body = html.escape(post.selftext) if hasattr(post, 'selftext') and post.selftext else "[No content]"
    post_body = post_body.replace('\n', '<br>')
    
    # Create comments section if available
    comments_html = ""
    if hasattr(post, 'top_level_comments') and post.top_level_comments:
        comments_html = f"<h4 style='color: {colors['yellow']};'>Top Comments:</h4><div style='color: {colors['base0']};'>"
        for comment in post.top_level_comments:
            comment_text = html.escape(comment.body).replace('\n', '<br>') if hasattr(comment, 'body') else "[No text]"
            comment_score = comment.score if hasattr(comment, 'score') else 'Unknown'
            
            # Add the comment with score
            comments_html += f"<div style='margin-bottom: 10px;'><span style='color: {colors['red']};'>⬆️ <strong>{comment_score}</strong></span> <strong style='color: {colors['cyan']};'>({comment.author if hasattr(comment, 'author') else 'Unknown'})</strong>: {comment_text}"
            
            # Add OP reply if it exists
            if hasattr(comment, 'has_op_reply') and comment.has_op_reply:
                op_reply_text = html.escape(comment.op_reply.body).replace('\n', '<br>') if hasattr(comment.op_reply, 'body') else "[No reply text]"
                
                # Check if info_need is set and include it if available
                if hasattr(comment, 'info_need'):
                    comments_html += f"<div style='margin-left: 20px; margin-top: 5px;'><strong style='color: {colors['magenta']};'>[OP Reply] {comment.info_need}:</strong> <span style='color: {colors['red']};'>{op_reply_text}</span></div>"
                else:
                    comments_html += f"<div style='margin-left: 20px; margin-top: 5px;'><strong style='color: {colors['magenta']};'>[OP Reply]:</strong> <span style='color: {colors['red']};'>{op_reply_text}</span></div>"
                
            comments_html += "</div>"
        comments_html += "</div>"
    
    # Create the collapsible HTML
    html_content = f"""
    <details style="margin-bottom: 10px; border: none; padding: 0; border-radius: 5px; background-color: {colors['base03']}; color: {colors['base0']};">
        <summary style="font-weight: bold; cursor: pointer; padding: 8px; background-color: {colors['base02']}; color: {colors['blue']}; border-radius: 3px; border: none; outline: none; box-shadow: none;">
            {html.escape(post.title)} ({html.escape(post.id)})
        </summary>
        <div style="margin-top: 10px; padding: 10px; background-color: {colors['base02']}; border-radius: 5px; border: 1px solid {colors['base01']};">
            <p><strong style="color: {colors['orange']};">Score:</strong> <span style="color: {colors['green']};">{post.score if hasattr(post, 'score') else 'Unknown'}</span></p>
            <h4 style="color: {colors['yellow']};">Post Content:</h4>
            <p style="color: {colors['base1']};">{post_body}</p>
            {comments_html}
        </div>
    </details>
    """
    return HTML(html_content)


    
if __name__ == "__main__":
    # argparser
    import argparse
    parser = argparse.ArgumentParser(description='Process a subreddit')
    parser.add_argument('--subreddit_name', type=str, help='Name of the subreddit', required=True)
    parser.add_argument('--directory', type=str, help='Directory where the subreddit data is stored', default=DATA_ROOT_DIR)
    parser.add_argument('--no-require-information-seeking', dest='require_information_seeking', action='store_false',
                        help='Disable the surface_form_is_information_seeking filter (useful for subreddits like ELI5)')
    parser.set_defaults(require_information_seeking=True)
    args = parser.parse_args()
    
    ingest_and_process_subreddit(
        subreddit_name=args.subreddit_name,
        submission_file=os.path.join(args.directory, args.subreddit_name, f'{args.subreddit_name}_submissions.jsonl'),
        comment_file=os.path.join(args.directory, args.subreddit_name, f'{args.subreddit_name}_comments.jsonl'),
        filtered_posts_file=os.path.join(args.directory, args.subreddit_name, f'{args.subreddit_name}_filtered_submissions.jsonl'),
        pkl_outfile=os.path.join(args.directory, args.subreddit_name, f'{args.subreddit_name}_processed.pkl'),
        require_information_seeking=args.require_information_seeking
    )