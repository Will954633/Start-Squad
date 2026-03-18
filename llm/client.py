"""Async OpenAI API wrapper with retry logic."""

import asyncio
from openai import AsyncOpenAI
from config import Config
from logger import log

client = AsyncOpenAI(api_key=Config.OPENAI_API_KEY)


async def generate_message(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 150,
    temperature: float = 0.9,
) -> str | None:
    """
    Call OpenAI API with retry logic.
    Returns the generated text or None on failure.
    """
    for attempt in range(Config.MAX_RETRIES):
        try:
            response = await client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_completion_tokens=max_tokens,
                temperature=temperature,
            )
            text = response.choices[0].message.content.strip()
            log.debug(f"LLM response ({len(text)} chars): {text[:80]}...")
            return text

        except Exception as e:
            log.warning(f"LLM call failed (attempt {attempt + 1}/{Config.MAX_RETRIES}): {e}")
            if attempt < Config.MAX_RETRIES - 1:
                await asyncio.sleep(Config.RETRY_DELAY * (attempt + 1))

    log.error("LLM call failed after all retries")
    return None
