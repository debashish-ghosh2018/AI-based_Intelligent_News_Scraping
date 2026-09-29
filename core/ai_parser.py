"""
AI Intent Parser
Uses Claude to convert natural language queries into structured scraping instructions.
"""

import json
import os
import anthropic


INTENT_SYSTEM_PROMPT = """You are a news search intent parser. Given a user's natural language query about news,
extract structured search parameters. Respond ONLY with valid JSON — no explanation, no markdown, no backticks.

Output this exact JSON structure:
{
  "topics": ["list", "of", "key", "topics"],
  "keywords": ["search", "keywords"],
  "regions": ["countries or regions, e.g. US, EU, India, global"],
  "categories": ["technology|politics|business|science|health|sports|entertainment|world"],
  "date_range": "today|week|month|all",
  "sentiment": "any|positive|negative|neutral",
  "max_articles": <number between 5 and 30>,
  "summary_style": "brief|detailed|bullets",
  "search_query": "optimised RSS/web search query string"
}

Rules:
- topics: extract the main subjects from the query (2-5 items)
- keywords: specific terms to look for in article titles/descriptions
- regions: infer from query; default to ["global"] if not specified
- categories: best matching categories (1-3)
- date_range: infer from words like "latest", "today", "this week"
- max_articles: infer from query; default 10
- search_query: a clean, concise search string for news APIs
"""


def parse_intent(user_query: str, api_key: str) -> dict:
    """
    Use Claude to parse a natural language news query into structured intent.
    Returns a dict of search parameters.
    """
    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        system=INTENT_SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": f"Parse this news query: {user_query}"}
        ]
    )

    raw = message.content[0].text.strip()

    # Strip accidental markdown fences
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    return json.loads(raw)


SUMMARISE_SYSTEM_PROMPT = """You are a professional news analyst. Given raw article data, produce a clean,
insightful summary. Be factual, concise, and neutral unless asked otherwise.

Rules:
- Lead with the most important information
- For "brief" style: 2-3 sentences max per article
- For "detailed" style: a paragraph per article with context
- For "bullets" style: 3-5 bullet points per article
- Always include: title, source, key facts, significance
- Flag if sources conflict on the same story
- Respond ONLY with the formatted summaries — no preamble
"""


def summarise_articles(articles: list, intent: dict, api_key: str) -> str:
    """
    Use Claude to summarise and analyse scraped articles.
    """
    client = anthropic.Anthropic(api_key=api_key)

    style = intent.get("summary_style", "brief")
    topics = ", ".join(intent.get("topics", ["news"]))

    articles_text = ""
    for i, a in enumerate(articles, 1):
        articles_text += f"\n--- Article {i} ---\n"
        articles_text += f"Title: {a.get('title', 'N/A')}\n"
        articles_text += f"Source: {a.get('source', 'N/A')}\n"
        articles_text += f"Date: {a.get('date', 'N/A')}\n"
        articles_text += f"URL: {a.get('url', 'N/A')}\n"
        articles_text += f"Content: {a.get('content', a.get('description', ''))[:800]}\n"

    prompt = (
        f"Summarise these {len(articles)} articles about '{topics}'. "
        f"Use '{style}' style. "
        f"Sentiment filter: {intent.get('sentiment', 'any')}.\n\n"
        f"{articles_text}"
    )

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        system=SUMMARISE_SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return message.content[0].text.strip()


def score_relevance(articles: list, intent: dict, api_key: str) -> list:
    """
    Use Claude to score and rank articles by relevance to the user's query.
    Returns articles with an added 'relevance_score' field (0-10).
    """
    client = anthropic.Anthropic(api_key=api_key)

    topics = ", ".join(intent.get("topics", []))
    keywords = ", ".join(intent.get("keywords", []))

    titles = "\n".join(
        f"{i}. {a.get('title', '')} — {a.get('description', '')[:100]}"
        for i, a in enumerate(articles, 1)
    )

    prompt = (
        f"Rate the relevance of each article (1-10) to the topic: '{topics}' "
        f"with keywords: '{keywords}'.\n\n"
        f"Articles:\n{titles}\n\n"
        f"Respond ONLY with JSON array of integers in order, e.g.: [8, 5, 9, 3, 7]"
    )

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    scores = json.loads(raw)
    for i, a in enumerate(articles):
        a["relevance_score"] = scores[i] if i < len(scores) else 5

    return sorted(articles, key=lambda x: x.get("relevance_score", 0), reverse=True)
