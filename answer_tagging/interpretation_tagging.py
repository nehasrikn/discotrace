import json
import asyncio
from dataclasses import dataclass, asdict
from typing import List, Dict, Union
from anthropic import (
    AsyncAnthropic,
    APIError as AnthropicAPIError,
    RateLimitError as AnthropicRateLimitError,
    APITimeoutError as AnthropicTimeoutError,
)
from openai import (
    AsyncOpenAI,
    APIError as OpenAIAPIError,
    RateLimitError as OpenAIRateLimitError,
    APITimeoutError as OpenAITimeoutError,
)
from answer_tagging.prompts import (
    interpretation_prefix_prompt,
    interpretation_example_prompt,
    eligible_for_interpretation_pairing,
)
from process_subreddit import RedditComment, RedditPost
from answer_tagging.action_tagging import ActionTagger
from answer_tagging.answering_utils import CacheStats


class InterpretationTagger:

    def __init__(self, provider: str = "anthropic", model: str = None, max_retries: int = 3, retry_delay: float = 1.0):
        self.provider = provider
        self.model = model or ActionTagger.DEFAULTS[provider]
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.stats = CacheStats()
        self.system_prompt = interpretation_prefix_prompt

        if provider == "anthropic":
            self.client = AsyncAnthropic()
        elif provider == "openai":
            self.client = AsyncOpenAI()
        else:
            raise ValueError(f"Unknown provider: {provider}")

    async def tag(
        self, 
        post: RedditPost, 
        interpretations: str,
        full_answer: Union[RedditComment, str], 
        tagged_segments: List[Dict]
    ) -> List[Dict]:
        
        if "RedditComment" in str(type(full_answer)): # hacky
            full_answer = full_answer.body
        
        for seg in tagged_segments:
            if seg["action_id"] in eligible_for_interpretation_pairing:
                seg["interpretation_id"] = await self._tag_single(
                    question=post.title,
                    interpretations=interpretations,
                    full_answer=full_answer,
                    segment_text=seg["text"],
                    action_id=seg["action_id"],
                )
            else:
                seg["interpretation_id"] = ""
        return tagged_segments

    async def _tag_single(self, question: str, interpretations: str, full_answer: str, segment_text: str, action_id: str) -> str:
        user_content = interpretation_example_prompt.format(
            question=question,
            interpretations=interpretations,
            answer=full_answer,
            segment=segment_text,
            action_label=action_id,
        )
        raw = await self._call(user_content)
        try:
            parsed = json.loads(raw)
            return parsed.get("interpretation_id", "NONE")
        except json.JSONDecodeError:
            return "__PARSE_ERROR__"

    async def _call(self, user_content: str) -> str:
        last_error = None
        for attempt in range(self.max_retries):
            try:
                if self.provider == "anthropic":
                    return await self._call_anthropic(user_content)
                else:
                    return await self._call_openai(user_content)
            except (AnthropicRateLimitError, OpenAIRateLimitError) as e:
                last_error = e
                await asyncio.sleep(self.retry_delay * (2 ** attempt))
            except (AnthropicTimeoutError, OpenAITimeoutError, AnthropicAPIError, OpenAIAPIError) as e:
                last_error = e
                await asyncio.sleep(self.retry_delay * (attempt + 1))
        self.stats.failed_requests += 1
        raise last_error

    async def _call_anthropic(self, user_content: str) -> str:
        response = await self.client.messages.create(
            model=self.model,
            system=[{"type": "text", "text": self.system_prompt, "cache_control": {"type": "ephemeral"}}],
            messages=[
                {"role": "user", "content": user_content},
                {"role": "assistant", "content": "{"},
            ],
            temperature=0, max_tokens=300,
        )
        usage = response.usage
        self.stats.total_requests += 1
        self.stats.total_input_tokens += usage.input_tokens
        self.stats.cached_tokens += getattr(usage, "cache_read_input_tokens", 0) or 0
        self.stats.cache_creation_tokens += getattr(usage, "cache_creation_input_tokens", 0) or 0
        return "{" + response.content[0].text.strip()

    async def _call_openai(self, user_content: str) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0, max_tokens=300,
        )
        usage = response.usage
        self.stats.total_requests += 1
        self.stats.total_input_tokens += usage.prompt_tokens
        if hasattr(usage, "prompt_tokens_details") and usage.prompt_tokens_details:
            self.stats.cached_tokens += getattr(usage.prompt_tokens_details, "cached_tokens", 0) or 0
        return response.choices[0].message.content.strip()