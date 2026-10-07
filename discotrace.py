from dataclasses import dataclass, field
from typing import List, Optional
from utils import load_jsonlines
from answer_tagging.ontology import ontology

# action name (full "action_AQ_assert_answer" or bare "assert_answer") -> family abbr
_ACTION_TO_FAMILY = {}
for _entry in ontology:
    _ACTION_TO_FAMILY[_entry["id"]] = _entry["action_family_abbr"]
    if _entry["id"].startswith("action_"):
        _ACTION_TO_FAMILY[_entry["id"].split("_", 2)[2]] = _entry["action_family_abbr"]


@dataclass
class DiscoTraceStep:
    text: str
    action: str #  "assert_answer", "clarification"
    interpretation_id: Optional[str]

    @property
    def action_family(self) -> str:
        """Map action to its family: AQ, CQ, SI, RQ, NO (or NONE if untagged/unknown)."""
        return _ACTION_TO_FAMILY.get(self.action, "NONE")


@dataclass
class DiscoTrace:
    question_id: str
    question_text: str
    comment_id: str
    comment_text: str
    steps: List[DiscoTraceStep] = field(default_factory=list)

    @property
    def action_sequence(self) -> List[str]:
        """Just the action labels, in order."""
        return [s.action for s in self.steps]

    @property
    def family_sequence(self) -> List[str]:
        """Just the family labels, in order."""
        return [s.action_family for s in self.steps]
    
    def __repr__(self):
        # format is "direct_to_resource:3 | assert_answer:3 | provide_recommendation_or_advice:3 | direct_to_resource:3"
        step_strs = [f"{s.action}:{s.interpretation_id or 'NONE'}" for s in self.steps]
        return " | ".join(step_strs)


def normalize_action(action_id: str) -> str:
    # action_AQ_assert_answer' -> 'assert_answer'
    parts = action_id.replace("action_", "").split("_", 1)
    return parts[1] if len(parts) > 1 else parts[0]


def load_discotraces(jsonl_path: str) -> List[DiscoTrace]:
    data = load_jsonlines(jsonl_path)
    discotraces = []

    for entry in data:
        qid = entry["question_id"]
        qtxt = entry["question_text"]

        for comment in entry["comments"]:
            steps = []
            for seg in comment["tagged_segments"]:
                interp = seg.get("interpretation_id")
                if interp == "NONE" or interp is None:
                    interp = None

                steps.append(DiscoTraceStep(
                    text=seg["text"],
                    action=normalize_action(seg["action_id"]),
                    interpretation_id=interp,
                ))

            discotraces.append(DiscoTrace(
                question_id=qid,
                question_text=qtxt,
                comment_id=comment["comment_id"],
                comment_text=comment["comment_text"],
                steps=steps,
            ))

    return discotraces


def load_and_preview(filepath: str):
    dts = load_discotraces(filepath)
    print(f"Loaded {len(dts)} DiscoTraces from {filepath}")
    print()

    dt = dts[0]
    print(f"Q: {dt.question_text}")
    print(f"A: {dt.comment_text[:100]}...")
    print(f"Steps ({len(dt.steps)}):")
    for s in dt.steps:
        print(f"  [{s.action_family}] {s.action} -> interp={s.interpretation_id}")
        print(f"       \"{s.text[:80]}...\"" if len(s.text) > 80 else f"       \"{s.text}\"")
    return dts