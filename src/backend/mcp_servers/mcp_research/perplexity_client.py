"""Perplexity API client using OpenAI-compatible interface."""

import sys

from openai import AsyncOpenAI

from config import PERPLEXITY_API_KEY


def initialize_client() -> AsyncOpenAI:
    """Initialize and return an AsyncOpenAI client configured for Perplexity."""
    return AsyncOpenAI(
        api_key=PERPLEXITY_API_KEY,
        base_url="https://api.perplexity.ai",
    )


async def research(
    client: AsyncOpenAI,
    system_prompt: str,
    user_query: str,
    model: str,
    temperature: float,
    max_tokens: int,
) -> str:
    """
    Send a research query to Perplexity and return the response text.

    Args:
        client: Initialized AsyncOpenAI client
        system_prompt: System instruction defining research behavior
        user_query: The user's research question
        model: Perplexity model to use
        temperature: Generation temperature
        max_tokens: Maximum tokens in response

    Returns:
        Response text from Perplexity

    Raises:
        Exception: If API call fails
    """
    sys.stderr.write(f"Sending request to Perplexity ({model})...\n")
    sys.stderr.flush()

    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )

    sys.stderr.write("Received response from Perplexity\n")
    sys.stderr.flush()

    return response.choices[0].message.content
