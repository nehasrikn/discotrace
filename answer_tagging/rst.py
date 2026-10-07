from isanlp_rst.parser import Parser
import io, contextlib
import isanlp_rst
from process_subreddit import RedditComment
import json
from dataclasses import dataclass
import json
import os
from pathlib import Path
from dataclasses import dataclass, asdict
from answer_tagging.answering_utils import highlight_spans
from typing import List, Dict

class RSTSegmenter:
    
    BOUNDARY_RELATIONS = {
        'rstdt': {
            'Contrast_NN',
            'Comparison_NN', 
            'Topic-Change_NN',
            'Topic-Change_NS',
            'Topic-Change_SN',
            'Evaluation_SN',
            'Evaluation_NS',
            'Evaluation_NN',
            'Summary_NN',
            'Summary_NS',
            'Summary_SN',
            'Background_NS',
            'Background_SN',
        },
        'gumrrg': {
            'adversative_NN',
            'adversative_NS',
            'adversative_SN',
            'organization_NS',
            'organization_SN',
            'topic_SN',
            'evaluation_NS',
            'evaluation_SN',
            'restatement_NN',
            'restatement_NS',
            'context_NS',
            'context_SN',
        }
    }
    
    def __init__(self, parser_version='rstdt'): # Choose from {'gumrrg', 'rstdt', 'rstreebank'}
        self.boundary_relations = self.BOUNDARY_RELATIONS.get(parser_version, self.BOUNDARY_RELATIONS['rstdt'])
        self.parser = Parser(hf_model_name='tchewik/isanlp_rst_v3', hf_model_version=parser_version, cuda_device=0) # Use -1 for CPU

    def segment(self, item, visualize=False):
        if "RedditComment" in str(type(item)): # hacky
            item = item.body
        
        rst_tree = self.parser(item)['rst'][0]
        text_segments = self.get_spans(rst_tree, min_span_size=3)
        
        if visualize:
            highlight_spans(text_segments)

        results = []
        for span in text_segments:
            edus = [node.text for node in span]
            sentences = group_edus_into_sentences(edus)
            entry = {"text": " ".join(edus)}
            if len(sentences) > 1:
                entry["subsegments"] = sentences
            results.append(entry)
        return results

    def get_spans(self, node, min_span_size=3):
        # walk the RST tree recursively and deicde where to split on relation types and spansizes
        
        if node.left is None and node.right is None:
            # this is a leaf node
            return [[node]]
        
        relation = f"{node.relation}_{node.nuclearity}"
        
        if relation in self.boundary_relations:
            # boundary relations are relations where we expect a rhetorical shift -- children likely
            # correspond to different discourse moves

            # recurse into both children
            left_spans = self.get_spans(node.left, min_span_size)
            right_spans = self.get_spans(node.right, min_span_size)
            
            left_size = sum(len(s) for s in left_spans)
            right_size = sum(len(s) for s in right_spans)

            # for most boundary relations, always split, but for Background only split of both sides are "heavy enough" (>= 3 EDUs)
            needs_size_check = relation.startswith('Background') # right now
            
            if not needs_size_check or (left_size >= min_span_size and right_size >= min_span_size):
                return left_spans + right_spans
            else:
                return [RSTSegmenter.get_leaves(node)]
        else:
            # this node's relation is safe (not boundary prone), there may be 
            # boundary relations deeper in the tree, recurse into both children to check
            # recurse into children to check for splits below
            left_spans = self.get_spans(node.left, min_span_size)
            right_spans = self.get_spans(node.right, min_span_size)

            if len(left_spans) + len(right_spans) > 2: # each child returns a list of spans. if no split happened, each child returns exactly 1 span, itself
                # at least one child got split internally 
                return left_spans + right_spans
            else:
                # if less than 2 spans, collapse everything into one span
                return [RSTSegmenter.get_leaves(node)]

    @staticmethod
    def get_leaves(node):
        # Flattens a subtree into a list of all its leaf EDUs. 
        # Used when we decide NOT to split—we return all leaves as one span.
        if node.left is None and node.right is None:
            return [node]
        return RSTSegmenter.get_leaves(node.left) + RSTSegmenter.get_leaves(node.right)
    
    
def group_edus_into_sentences(edus: List[str]) -> List[str]:
    if not edus:
        return []
    
    sentences = []
    current = []
    
    for edu in edus:
        current.append(edu)
        # Sentence ends with terminal punctuation (not inside parens/quotes)
        stripped = edu.rstrip()
        if stripped and stripped[-1] in '.!?' and not stripped.endswith('e.g.') and not stripped.endswith('i.e.'):
            sentences.append(" ".join(current))
            current = []
    
    if current:
        sentences.append(" ".join(current))
    
    return sentences