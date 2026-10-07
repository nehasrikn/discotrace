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
from answer_tagging.prompts import action_prefix_prompt, action_example_prompt, ontology_str
from process_subreddit import RedditComment, RedditPost
from answer_tagging.answering_utils import CacheStats

PARSE_ERROR = "__PARSE_ERROR__"



class ActionTagger:
    DEFAULTS = {
        "anthropic": "claude-haiku-4-5-20251001",
        "openai": "gpt-4.1-2025-04-14",
    }

    def __init__(
        self,
        provider: str = "openai",
        model: str = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        self.provider = provider
        self.model = model or self.DEFAULTS[provider]
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.stats = CacheStats()
        self.system_prompt = action_prefix_prompt.format(ontology=ontology_str)

        if provider == "anthropic":
            self.client = AsyncAnthropic()
        elif provider == "openai":
            self.client = AsyncOpenAI()
        else:
            raise ValueError(f"Unknown provider: {provider}")

    async def tag_segment(
        self,
        question: str,
        full_answer: str,
        segment: dict,
        prev_segment: str = "",
        prev_label: str = "",
    ) -> List[Dict[str, str]]:
        if "subsegments" in segment:
            subsegments_str = "\n".join(
                f'[{i}] "{s}"' for i, s in enumerate(segment["subsegments"])
            )
        else:
            subsegments_str = "(atomic unit: no subsegments)"

        user_content = action_example_prompt.format(
            question=question,
            answer=full_answer,
            segment_prev=prev_segment,
            prev_label=prev_label,
            segment=segment["text"],
            subsegments=subsegments_str,
        )

        raw = await self._call(user_content)
        return self._parse(raw, segment)

    async def tag_comment(
        self,
        post : RedditPost,
        comment: Union[str, RedditComment],
        segments: List[dict],
        subsume: bool = True,
    ) -> List[Dict[str, str]]:
        comment = comment.body if isinstance(comment, RedditComment) else comment
        
        all_tagged = []
        prev_segment, prev_label = "", ""

        for segment in segments:
            results = await self.tag_segment(
                question=post.title,
                full_answer=comment,
                segment=segment,
                prev_segment=prev_segment,
                prev_label=prev_label,
            )
            all_tagged.extend(results)
            prev_segment = segment["text"]
            prev_label = results[-1]["action_id"]

        return self._subsume(all_tagged) if subsume else all_tagged

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
            except (
                AnthropicTimeoutError,
                OpenAITimeoutError,
                AnthropicAPIError,
                OpenAIAPIError,
            ) as e:
                last_error = e
                await asyncio.sleep(self.retry_delay * (attempt + 1))
        self.stats.failed_requests += 1
        raise last_error

    async def _call_anthropic(self, user_content: str) -> str:
        response = await self.client.messages.create(
            model=self.model,
            system=[
                {
                    "type": "text",
                    "text": self.system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[
                {"role": "user", "content": user_content},
                {"role": "assistant", "content": "["},
            ],
            temperature=0,
            max_tokens=1000,
        )
        usage = response.usage
        self.stats.total_requests += 1
        self.stats.total_input_tokens += usage.input_tokens
        self.stats.cached_tokens += getattr(usage, "cache_read_input_tokens", 0) or 0
        self.stats.cache_creation_tokens += getattr(usage, "cache_creation_input_tokens", 0) or 0
        return "[" + response.content[0].text.strip()

    async def _call_openai(self, user_content: str) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0,
            max_tokens=1000,
        )
        usage = response.usage
        self.stats.total_requests += 1
        self.stats.total_input_tokens += usage.prompt_tokens
        if hasattr(usage, "prompt_tokens_details") and usage.prompt_tokens_details:
            self.stats.cached_tokens += getattr(usage.prompt_tokens_details, "cached_tokens", 0) or 0
        return response.choices[0].message.content.strip()


    def _parse(self, raw: str, segment: dict) -> List[Dict[str, str]]:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            return [{"text": segment["text"], "action_id": PARSE_ERROR, "raw": raw}]

        if not isinstance(parsed, list) or not parsed:
            return [{"text": segment["text"], "action_id": PARSE_ERROR, "raw": raw}]

        if len(parsed) == 1 or "subsegment_index" not in parsed[0]:
            return [{"text": segment["text"], "action_id": parsed[0].get("action_id", PARSE_ERROR)}]

        if "subsegments" in segment:
            results = []
            for entry in parsed:
                idx = entry.get("subsegment_index", -1)
                if 0 <= idx < len(segment["subsegments"]):
                    results.append(
                        {
                            "text": segment["subsegments"][idx],
                            "action_id": entry.get("action_id", PARSE_ERROR),
                        }
                    )
            return results if results else [{"text": segment["text"], "action_id": PARSE_ERROR, "raw": raw}]

        return [{"text": segment["text"], "action_id": parsed[0].get("action_id", PARSE_ERROR)}]

    @staticmethod
    def _subsume(segments: List[Dict]) -> List[Dict]:
        if not segments:
            return []

        result = []
        current = segments[0].copy()

        for seg in segments[1:]:
            if seg["action_id"] == current["action_id"]:
                current["text"] = current["text"] + " " + seg["text"]
            else:
                result.append(current)
                current = seg.copy()

        result.append(current)
        return result