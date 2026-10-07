from answer_tagging.ontology import ontology, ontology_to_prompt_string


action_prefix_prompt = """You are an expert discourse analyst trying to understand how people answer questions on Reddit. You will analyze answers by tagging each text segment from a Reddit answer with a discourse action.

### Rules
1. **Select EXACTLY ONE action_id per segment or subsegment.**
2. If the current segment continues the previous action, reuse the previous action_id.
3. If a new rhetorical move begins, select the appropriate new action_id.
4. If no action fits, use "NONE".

### Subsegment Labeling
Each segment you receive was produced by a discourse parser. You will also be shown the subsegments (sentences) that make up the segment. If all subsegments serve the same discourse function, return a single-element array with one action_id. If different subsegments serve **different discourse functions**, return an array with one entry per subsegment, each with its subsegment_index and action_id.

Common patterns worth splitting:
- Background/reasoning subsegments followed by an answer subsegment
- An answer subsegment followed by a redirect or recommendation
- A presupposition rejection followed by an alternative answer

Do NOT split when:
- A subsegment contains light framing for the next (e.g., "So basically," followed by an answer → single Assert Answer)
- The difference is just emphasis vs. substance within the same move

### Caveats and Task Nuances
1. Consider the expected answer type of the question when labeling actions. Responding to "Where can I find X" with a website recommendation is an "Answer the Question" action, not a "Direct to Resource" action. If the resource is the answer itself, label it as "Assert Answer". If the resource is suggested as additional reading, use Direct to Resource.
2. When a segment contains both an answer and supporting reasoning:
   - If subsegments are provided and the answer and reasoning fall in **different subsegments**, split them (e.g., reasoning subsegments get "Provide Reasoning or Justification", the answer subsegment gets "Assert Answer").
   - If they are in the **same subsegment** (tightly integrated), label it as "Provide Reasoning or Justification" if the justification is non-trivial, otherwise "Assert Answer".
3. When a segment explains WHY something is the case, determine what it's explaining:
   - If it explains why an ANSWER is correct -> "Provide Reasoning or Justification"
   - If it explains why a PREMISE OF THE QUESTION is wrong -> "Reject Presupposition"
   
   Example: For "Why is the sky blue?", the segment "Because of Rayleigh scattering" is justification.
   For "What's the best liver detox cleanse?", the segment "The concept of 'detoxing' your liver is misleading—your liver already filters toxins continuously" is rejecting the presupposition.
   
4. Sharing a personal anecdote or experience to is "Provide Example", NOT "Provide Background." Background sets up context, frameworks, or history *before* answering. Examples use concrete cases (including personal ones) to *support or illustrate* an answer.
   
   - "I have a doctorate, and sometimes introduce myself as Dr." -> Provide Example (personal illustration)
   - "The use of honorifics has a long and contested history in academia." -> Provide Background (contextual framing)
   
5. When a segment follows a recommendation and provides supporting information, ask: does it explain why the recommendation is good *in terms of the original question*, or does it answer a *different* question?
   - If it explains why the recommendation addresses the original question → "Provide Reasoning or Justification"
   - If it introduces new information that answers a tangentially related but different question → "Answer a Question or Interpretation outside of Interpretation Space"
   
   Example: For a question about whether chiropractors have the same training as MDs:
   - "Because chiropractors don't attend accredited medical schools" → Provide Reasoning (directly about training/credentials)
   - "The PT's goal will be to rehabilitate you; a chiropractor will be looking to retain you as a customer for steady cash flow" → Answer outside Interpretation Space (this answers "what's the difference in their professional incentives?" — a different question)

6. When a segment invokes an external source (study, statistic, law, quote, expert consensus) to support a claim, use "Cite External Source" — NOT "Provide Example" or "Provide Reasoning." The key test: does the credibility derive from an independently verifiable external source, or from the answerer's own experience/logic?
   - "A 2019 Lancet study found no significant effect." → Cite External Source
   - "I saw the same thing happen at my last job." → Provide Example
   - "That's because the compiler needs type info at compile time." → Provide Reasoning

### Action Ontology
{ontology}

### Output Format
Always respond with ONLY a JSON array. No explanation, no reasoning, no commentary.

Single action for whole segment:
[{{"action_id": "action_AQ_assert_answer"}}]

Distinct actions per subsegment:
[
  {{"subsegment_index": 0, "action_id": "action_CQ_reject_presupposition"}},
  {{"subsegment_index": 1, "action_id": "action_AQ_assert_answer"}}
]

When no action fits:
[{{"action_id": "NONE"}}]"""

action_example_prompt = """### Question
{question}

### Full Answer
{answer}

### Previous Segment action="{prev_label}"
{segment_prev}

### Current Segment
{segment}

### Subsegments
{subsegments}

Respond with ONLY a JSON array."""


ontology_str = ontology_to_prompt_string(ontology)

eligible_for_interpretation_pairing = {
    entry["id"] for entry in ontology if entry.get("interpretation_eligible", False)
}


interpretation_prefix_prompt = """You are an expert discourse analyst. A Reddit answer segment has already been labeled with a discourse action. Your task is to determine which interpretation of the original question the segment best addresses.

### Rules
1. You are given a question, its possible interpretations, and a segment from an answer that has been labeled with a discourse action.
2. Determine which question interpretation the segment most directly addresses, adopts, or targets. This may be explicit or implicit.
3. If the segment clearly and directly addresses one of the interpretations, return that interpretation's ID
4. If the segment does not clearly target any specific interpretation, return "NONE".

### Output Format
Respond with exactly ONE JSON object:
{{"interpretation_id": "id_1"}}

When no specific interpretation is targeted:
{{"interpretation_id": "NONE"}}"""

interpretation_example_prompt = """### Question
{question}

### Question Interpretations
{interpretations}

### Full Answer
{answer}

### Segment (labeled as "{action_label}")
{segment}

**Respond with EXACTLY ONE JSON DICTIONARY (NOT an array).**"""