ontology = [
    ########### Seek Information from Asker (SI) ############
    {
        "id": "action_SI_clarification",
        "name": "Clarification",
        "action_family": "seek_information_from_asker",
        "action_family_abbr": "SI",
        "interpretation_eligible": True,
        "description": "The text requests additional information or elaboration to better understand how to answer the question before providing an answer. This could include asking for term definitions, specifying the scope, explaining the intention, or narrow down what the asker is looking for.",
        "segment_examples": ["What exactly do you mean?", "Can you share what error you're getting and what you've tried so far?"]
    },
    {
        "id": "action_SI_probe_context",
        "name": "Probe Context",
        "action_family": "seek_information_from_asker",
        "action_family_abbr": "SI",
        "interpretation_eligible": False,
        "description": "The text asks about the asker's background, situation, or motivations to better understand why they're asking the question. Rather than clarifying the question itself, this probes the broader context surrounding it, such as the asker's goals, experience level, or the circumstances that prompted the question.",
        "segment_examples": ["Are you coming from a statistics background or more of a software engineering one?", "Why are you asking this?", "What kind of project are you working on?"]
    },
    {
        "id": "action_SI_counter_question",
        "name": "Counter-Question",
        "action_family": "seek_information_from_asker",
        "action_family_abbr": "SI",
        "interpretation_eligible": True,
        "description": "The text responds with a question that challenges the premise, framing, or assumptions behind the original question.",
        "segment_examples": ["Why is speed the priority here?", "Do you actually need a framework for what you're building?", "Is venue prestige really what matters most for your career stage?"]
    },
    ############ Comment on Question (CQ) ############
    {
        "id": "action_CQ_reject_presupposition",
        "name": "Reject Presupposition",
        "action_family": "comment_on_question",
        "action_family_abbr": "CQ",
        "interpretation_eligible": False,
        "description": "The text explicitly rejects or denies a premise or assumption embedded in the question. This includes explaining WHY the premise is false or doesn't hold. The key distinction is that the segment is challenging the question's framing rather than supporting an answer to it.",
        "segment_examples": [
            "That's not actually how memory allocation works.",
            "The question assumes there's a single 'best' approach, but there isn't.",
            "'Nationality' doesn't exist in biological terms—you can't transfer your German-ness to your kids genetically.",
            "This assumes the two are mutually exclusive, but they're not."
        ]
    },
    {
        "id": "action_CQ_correct_fact_or_terminology",
        "name": "Correct Fact or Terminology",
        "action_family": "comment_on_question",
        "action_family_abbr": "CQ",
        "interpretation_eligible": False,
        "description": "The text corrects a factual error or misuse of terminology in the question.",
        "segment_examples": ["That's actually called a 'monad,' not a 'monoid.'", "Just to clarify, Python is interpreted, not compiled."]
    },
    {
        "id": "action_CQ_comment_on_question",
        "name": "Comment on Question",
        "action_family": "comment_on_question",
        "action_family_abbr": "CQ",
        "interpretation_eligible": False,
        "description": "The text makes an observation or remark about the question itself without directly answering or rejecting it.",
        "segment_examples": ["This is a really common misconception.", "Interesting question—it's more nuanced than it might seem."]
    },
    {
        "id": "action_CQ_redirect_formulation",
        "name": "Redirect Formulation",
        "action_family": "comment_on_question",
        "action_family_abbr": "CQ",
        "interpretation_eligible": True,
        "description": "The text suggests a better or more productive way to frame the question.",
        "segment_examples": ["A better question might be whether the benefits outweigh the costs.", "It's more useful to think about this in terms of trade-offs rather than which is 'better.'"]
    },
    {
        "id": "action_CQ_surface_interpretations_or_disambiguate",
        "name": "Surface Interpretations or Disambiguate",
        "action_family": "comment_on_question",
        "action_family_abbr": "CQ",
        "interpretation_eligible": False,
        "description": "The text explicitly identifies, enumerates, or distinguishes between multiple possible readings or meanings of the question. The answerer makes the interpretation space visible rather than silently adopting one reading or asking the asker to clarify.",
        "segment_examples": [
            "Is the question 'can math describe a range of phenomena' or 'can math describe the totality of phenomena'?",
            "This depends on whether you mean nationality, citizenship, or ethnic heritage.",
            "There are two ways to read this: legally or colloquially.",
            "In terms of citizenship... vs in biological terms..."
        ]
    },
    ############ Answer the Question (AQ) ############
    {
        "id": "action_AQ_provide_background",
        "name": "Provide Background",
        "action_family": "answer_question",
        "action_family_abbr": "AQ",
        "interpretation_eligible": True,
        "description": "The text provides context, history, or a broader framework to situate the question before or instead of directly answering. This includes reframing the question by situating it within a broader debate or recurring issue, as long as the segment provides substantive context rather than proposing a new question.",
        "segment_examples": ["To understand this, it helps to know how compilers evolved.", "This debate goes back to the Chomsky-Skinner controversy in the 1950s.", "There are a few different schools of thought on this.", "People ask this a lot, but the real issue is..."]
    },
    {
        "id": "action_AQ_provide_example",
        "name": "Provide Example",
        "action_family": "answer_question",
        "action_family_abbr": "AQ",
        "interpretation_eligible": True,
        "description": "The text offers a concrete example, case, or illustration to address the question.",
        "segment_examples": ["For instance, in Japanese, the verb always comes at the end.", "Consider how Google handled this with MapReduce.", "A good example is the way 'literally' has shifted meaning over time."]
    },
    {
        "id": "action_AQ_assert_answer",
        "name": "Assert Answer",
        "action_family": "answer_question",
        "action_family_abbr": "AQ",
        "interpretation_eligible": True,
        "description": "The answerer directly states an answer or claim in response to the question.",
        "segment_examples": ["Yes, language can be formally modeled using mathematical logic.", "The short answer is no.", "It depends on what you mean, but generally speaking, yes."]
    },
    {
        "id": "action_AQ_provide_reasoning_justification",
        "name": "Provide Reasoning or Justification",
        "action_family": "answer_question",
        "action_family_abbr": "AQ",
        "interpretation_eligible": True,
        "description": "The text provides reasoning, evidence, explanation, or argumentation that supports or defends an answer that has been (or is being) asserted. This typically follows an answer and explains WHY the claim is correct. Unlike 'Provide Background' which situates the question in context, justification specifically defends the answer. NOTE: If the segment explains why a *premise of the question* is wrong (rather than why an *answer* is correct), use 'Reject Presupposition' instead.",
        "segment_examples": [
            "That's because the compiler needs to know the size at compile time.",
            "The reason is that plagiarism applies to any original content, not just prose.",
            "This makes sense when you consider how memory is allocated."
        ]
    },
    {
        "id": "action_AQ_provide_recommendation_or_advice",
        "name": "Provide Recommendation or Advice",
        "action_family": "answer_question",
        "action_family_abbr": "AQ",
        "interpretation_eligible": True,
        "description": "The text offers actionable guidance, tips, recommendations, or instructions that help the asker accomplish a goal or navigate a situation. This may involve telling the asker how to do something, what they should do, or why they should do something.",
        "segment_examples": [
            "Here are a few tips: first, decide what feeling you want to convey.",
            "To avoid this, create original wording or paraphrase substantially and cite.",
            "I'd recommend starting with the documentation before diving into the codebase.",
            "Make sure you back up your files before attempting this."
        ]
    },
    {
        "id": "action_AQ_answer_question_or_interpretation_outside_space",
        "name": "Answer a Question or Interpretation outside of Interpretation Space",
        "action_family": "answer_question",
        "action_family_abbr": "AQ",
        "interpretation_eligible": False,
        "description": "The text provides substantive information that answers a different question than the one asked or reasonable direct interpretations. The answerer has drifted to a related but distinct topic. This includes segments that follow a recommendation but justify it by answering a tangential question rather than addressing the original one. If the segment explicitly proposes a better way to ask the question, use Redirect Formulation instead.",
        "segment_examples": [
            {
                "original_question": "Is it better to learn Python or Java first?",
                "question_interpretations": [
                "Which language is better for beginners?",
                "Which language has better career prospects?"
                ],
                "answer": "You should start with whatever language your project or coursework requires.",
                "question_answered": "How should I decide which language to learn first?"
            },
            {
                "original_question": "Can I spray paint my stethoscope?",
                "question_interpretations": [
                "Is it safe to spray paint medical equipment?",
                "Is it allowed to modify medical tools?"
                ],
                "answer": "You can buy colored stethoscope covers or charms instead.",
                "question_answered": "How can I personalize my stethoscope?"
            }
        ]
    },
    {
        "id": "action_AQ_cite_source",
        "name": "Cite External Source",
        "action_family": "answer_question",
        "action_family_abbr": "AQ",
        "interpretation_eligible": True,
        "description": "The text invokes an external, independently verifiable source (such as a document, dataset, quotation, study, law, statistic, or established expert consensus) to support a claim or answer. The credibility derives from the cited source rather than from the answerer's personal experience or reasoning. This is distinct from Provide Example (where the answerer uses a concrete case, including personal experience, to illustrate a point) and from Direct to Resource (where the answerer redirects the asker elsewhere for further reading rather than using an excerpt from source to support a claim here).",
        "segment_examples": [
            "Current GDP estimates from the Atlanta Fed's GDP Now are above 4% growth.",
            "As LKY said in Parliament in 1984, 'one-man-one-vote is a very difficult system to operate.'",
            "A 2019 study in The Lancet found that the treatment had no significant effect.",
            "According to Section 230 of the Communications Decency Act, platforms are not liable for user-generated content.",
            "The scientific consensus is that vaccines do not cause autism."
        ]
    },
    ############ Redirect the Question (RQ) ############
    {
        "id": "action_RQ_direct_to_resource",
        "name": "Direct to Resource",
        "action_family": "redirect_question",
        "action_family_abbr": "RQ",
        "interpretation_eligible": True,
        "description": "The text points the asker toward an external resource such as a book, article, website, or documentation.",
        "segment_examples": ["The Wikipedia article on formal grammars covers this well.", "Check out Chapter 3 of Jurafsky & Martin.", "The official Python docs have a good explanation of this."]
    },
    {
        "id": "action_RQ_recommend_expert",
        "name": "Recommend Expert",
        "action_family": "redirect_question",
        "action_family_abbr": "RQ",
        "interpretation_eligible": True,
        "description": "The text suggests the asker consult a specific person, professional, or community better suited to answer.",
        "segment_examples": ["You'd probably get a better answer from a tax professional.", "Try asking in r/AskHistorians—they're good with this.", "This is really a question for your doctor."]
    },
    ############ No-Op (NO) ############
    {
        "id": "action_NO_non_answer",
        "name": "Non-Answer",
        "action_family": "no_op",
        "action_family_abbr": "NO",
        "interpretation_eligible": False,
        "description": "The text explicitly declines to answer or expresses uncertainty without providing substantive information.",
        "segment_examples": ["I don't know.", "I'm not sure, honestly.", "I don't think I'm qualified to answer this.", "No idea, sorry."]
    },
    {
        "id": "action_NO_presentational",
        "name": "Presentational",
        "action_family": "no_op",
        "action_family_abbr": "NO",
        "interpretation_eligible": False,
        "description": "The answerer uses filler or framing language that signals a response is coming but doesn't itself convey information.",
        "segment_examples": ["I'm sure", "I have a few thoughts on this.", "So, here's the thing.", "Great question!", "Okay, let me try to unpack this."]
    },
    {
        "id": "action_NO_aside_or_other_remark",
        "name": "Aside or Other Remark",
        "action_family": "no_op",
        "action_family_abbr": "NO",
        "interpretation_eligible": False,
        "description": "The text expresses a personal reaction, evaluation, or commentary that doesn't directly serve the information-seeking goal. This includes evaluative remarks about the asker's situation, empathetic responses, tangential personal thoughts, jokes, or other miscellaneous content that doesn't fit elsewhere.",
        "segment_examples": ["That sounds like a fun project!", "That must be frustrating.", "Haha, I've been there.", "Good question!! Lol"]
    },
    {
        "id": "action_NO_offer",
        "name": "Offer",
        "action_family": "no_op",
        "action_family_abbr": "NO",
        "interpretation_eligible": False,
        "description": "The text offers to provide further help, elaboration, or continuation of the exchange. The answerer signals availability for follow-up rather than directly providing information.",
        "segment_examples": ["If you'd like, I can dive deeper into this.", "Let me know if you have any questions.", "Tell me the details and I'll help you figure it out.",]
    },
    {
        "id": "NONE",
        "name": "NONE",
        "action_family": "none",
        "action_family_abbr": "NONE",
        "interpretation_eligible": False,
        "description": "This is a special label used when no action is identified for a segment. It indicates that the segment does not fit any of the defined action categories in the ontology.",
        "segment_examples": []
    }
]

ontology_map = {action["id"]: action for action in ontology}
ontology_family = {}
for action in ontology:
    family = action["action_family"]
    if family not in ontology_family:
        ontology_family[family] = []
    ontology_family[family].append(action)
    
interpretation_eligible_actions = set([action["id"] for action in ontology if action["interpretation_eligible"]])
    
    
family_colors = {
    "SI": "#f5c6c6",
    "CQ": "#fde2a7",
    "AQ": "#b8f0cd",
    "RQ": "#b3d9f2",
    "NO": "#d5d8dc",
}

def get_color(action_id):
    for prefix, color in family_colors.items():
        if f"_{prefix}_" in action_id:
            return color
    return family_colors["NO"]


import json


def ontology_to_prompt_string(ontology):
    """Convert structured ontology list to the prompt string format."""
    family_labels = {
        "SI": "Seeking Information from Asker (SI)",
        "CQ": "Comment on the Question (CQ)",
        "AQ": "Answer the Question (AQ)",
        "RQ": "Redirect the Question (RQ)",
        "NO": "NO-OP Actions",
        "NONE": "Other",
    }

    sections = []
    current_family = None
    counter = 0

    for entry in ontology:
        abbr = entry["action_family_abbr"]

        # Add section header when family changes
        if abbr != current_family:
            current_family = abbr
            label = family_labels.get(abbr, abbr)
            sections.append(f"\n----- {label} -----\n")

        counter += 1
        display = {
            "id": entry["id"],
            "name": entry["name"],
            "description": entry["description"],
            "segment_examples": entry["segment_examples"],
        }
        body = json.dumps(display, indent=4).replace("{", "{{").replace("}", "}}")
        sections.append(f"{counter}. {body}")

    return "# Action Space:\n" + "\n".join(sections)