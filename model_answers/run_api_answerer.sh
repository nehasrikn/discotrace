# SUBREDDIT=NoStupidQuestions

# echo "Running answerer for $SUBREDDIT with Claude Haiku 4.5..."

# python -m model_answers.answerers $ROOT_DIR/$SUBREDDIT/questions_$SUBREDDIT.jsonl --provider anthropic --model "claude-haiku-4-5-20251001" --output-file "$SUBREDDIT"_claude-haiku-4.5.jsonl


# SUBREDDIT=ScienceBasedParenting

# echo "Running mimic+guidelines answerer for $SUBREDDIT with Claude Sonnet 4.5..."

# python -m model_answers.answerers $ROOT_DIR/$SUBREDDIT/questions_$SUBREDDIT.jsonl \
#   --provider anthropic \
#   --model "claude-sonnet-4-5-20250929" \
#   --prompt-key answer_mimic_community_guidelines \
#   --prompt-type zero_shot \
#   --prompt-file $ROOT_DIR/model_answers/prompt.json \
#   --prompt-vars "{\"subreddit\": \"$SUBREDDIT\"}" \
#   --output-file "${SUBREDDIT}_claude-sonnet-4.5_mimic_community_guidelines.jsonl"

SUBREDDIT=ScienceBasedParenting
ROOT_DIR="."

echo "Running vanilla answerer for $SUBREDDIT with Claude Sonnet 4.5..."

python -m model_answers.answerers $ROOT_DIR/$SUBREDDIT/questions_$SUBREDDIT.jsonl \
  --provider anthropic \
  --model "claude-sonnet-4-5-20250929" \
  --prompt-key answer_vanilla \
  --prompt-type zero_shot \
  --prompt-file $ROOT_DIR/model_answers/prompt.json \
  --output-file "${SUBREDDIT}_claude-sonnet-4.5.jsonl"