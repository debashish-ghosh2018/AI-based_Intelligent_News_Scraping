"""
News Scraper
Scrapes from RSS feeds and HTML pages across global news sources.
Adapts strategy per source automatically.
"""

import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from dateutil import parser as dateparser
from urllib.parse import urlparse, quote_plus
import time
import re


# ─── Source Registry ──────────────────────────────────────────────────────────

RSS_SOURCES = {
    "global": [
        {"name": "Reuters", "url": "https://feeds.reuters.com/reuters/topNews"},
        {"name": "AP News", "url": "https://rsshub.app/apnews/topics/apf-topnews"},
        {"name": "BBC News", "url": "http://feeds.bbci.co.uk/news/rss.xml"},
        {"name": "Al Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml"},
        {"name": "The Guardian", "url": "https://www.theguardian.com/world/rss"},
    ],
    "technology": [
        {"name": "TechCrunch", "url": "https://techcrunch.com/feed/"},
        {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml"},
        {"name": "Ars Technica", "url": "http://feeds.arstechnica.com/arstechnica/index"},
        {"name": "Wired", "url": "https://www.wired.com/feed/rss"},
        {"name": "Hacker News", "url": "https://hnrss.org/frontpage"},
    ],
    "business": [
        {"name": "Bloomberg Markets", "url": "https://feeds.bloomberg.com/markets/news.rss"},
        {"name": "Financial Times", "url": "https://www.ft.com/?format=rss"},
        {"name": "CNBC", "url": "https://www.cnbc.com/id/100003114/device/rss/rss.html"},
        {"name": "Forbes", "url": "https://www.forbes.com/real-time/feed2/"},
    ],
    "science": [
        {"name": "Science Daily", "url": "https://www.sciencedaily.com/rss/all.xml"},
        {"name": "New Scientist", "url": "https://www.newscientist.com/feed/home/"},
        {"name": "NASA", "url": "https://www.nasa.gov/rss/dyn/breaking_news.rss"},
    ],
    "health": [
        {"name": "WHO", "url": "https://www.who.int/rss-feeds/news-english.xml"},
        {"name": "Medical News Today", "url": "https://www.medicalnewstoday.com/newsfeeds/news.xml"},
        {"name": "Health Day", "url": "https://consumer.healthday.com/rss_feed"},
    ],
    "politics": [
        {"name": "Politico", "url": "https://rss.politico.com/politics-news.xml"},
        {"name": "The Hill", "url": "https://thehill.com/rss/syndicator/19109"},
        {"name": "NPR Politics", "url": "https://feeds.npr.org/1014/rss.xml"},
    ],
    "india": [
        {"name": "Times of India", "url": "https://timesofindia.indiatimes.com/rssfeedstopstories.cms"},
        {"name": "NDTV", "url": "https://feeds.feedburner.com/ndtvnews-top-stories"},
        {"name": "The Hindu", "url": "https://www.thehindu.com/feeder/default.rss"},
        {"name": "India Today", "url": "https://www.indiatoday.in/rss/1206514"},
    ],
    "us": [
        {"name": "NY Times", "url": "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml"},
        {"name": "Washington Post", "url": "https://feeds.washingtonpost.com/rss/national"},
        {"name": "CNN", "url": "http://rss.cnn.com/rss/edition.rss"},
        {"name": "Fox News", "url": "https://moxie.foxnews.com/google-publisher/latest.xml"},
    ],
    "eu": [
        {"name": "Euronews", "url": "https://www.euronews.com/rss"},
        {"name": "Deutsche Welle", "url": "https://rss.dw.com/xml/rss-en-all"},
        {"name": "EUobserver", "url": "https://euobserver.com/rss"},
    ],
    "sports": [
        {"name": "ESPN", "url": "https://www.espn.com/espn/rss/news"},
        {"name": "BBC Sport", "url": "http://feeds.bbci.co.uk/sport/rss.xml"},
        {"name": "Sky Sports", "url": "https://www.skysports.com/rss/12040"},
    ],
    "entertainment": [
        {"name": "Variety", "url": "https://variety.com/feed/"},
        {"name": "Hollywood Reporter", "url": "https://www.hollywoodreporter.com/feed/"},
        {"name": "Entertainment Weekly", "url": "https://ew.com/feed/"},
    ],
}

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"


# ─── Scraper Class ─────────────────────────────────────────────────────────────

class NewsScraper:

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    # ── RSS Feed Scraping ─────────────────────────────────────────────────────

    def scrape_rss(self, feed_url: str, source_name: str, max_items: int = 10) -> list:
        """Parse an RSS/Atom feed and return structured articles."""
        articles = []
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:max_items]:
                article = self._parse_rss_entry(entry, source_name, feed_url)
                if article:
                    articles.append(article)
        except Exception:
            pass
        return articles

    def _parse_rss_entry(self, entry, source_name: str, feed_url: str) -> dict | None:
        title = getattr(entry, "title", "").strip()
        if not title:
            return None

        description = ""
        if hasattr(entry, "summary"):
            description = BeautifulSoup(entry.summary, "html.parser").get_text(separator=" ")
        elif hasattr(entry, "description"):
            description = BeautifulSoup(entry.description, "html.parser").get_text(separator=" ")

        description = re.sub(r'\s+', ' ', description).strip()[:500]

        url = getattr(entry, "link", "")

        date_str = "Unknown"
        for date_field in ["published", "updated", "created"]:
            if hasattr(entry, date_field):
                try:
                    dt = dateparser.parse(getattr(entry, date_field))
                    date_str = dt.strftime("%Y-%m-%d %H:%M UTC")
                    break
                except Exception:
                    date_str = getattr(entry, date_field, "Unknown")
                    break

        domain = urlparse(feed_url).netloc.replace("www.", "").replace("feeds.", "").replace("rss.", "")

        return {
            "title": title,
            "description": description,
            "url": url,
            "source": source_name,
            "domain": domain,
            "date": date_str,
            "content": description,
            "relevance_score": 5,
        }

    # ── Google News RSS Search ─────────────────────────────────────────────────

    def scrape_google_news(self, query: str, max_items: int = 15) -> list:
        """Scrape Google News RSS for a search query."""
        encoded = quote_plus(query)
        url = GOOGLE_NEWS_RSS.format(query=encoded)
        return self.scrape_rss(url, "Google News", max_items)

    # ── HTML Article Scraping (fallback) ──────────────────────────────────────

    def scrape_article_content(self, url: str) -> str:
        """Try to fetch the full article text from a URL."""
        try:
            resp = self.session.get(url, timeout=self.timeout)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")

            # Remove clutter
            for tag in soup(["script", "style", "nav", "footer", "header",
                              "aside", "iframe", "noscript", "figure"]):
                tag.decompose()

            # Try common article selectors
            for selector in ["article", "[class*='article-body']",
                             "[class*='story-body']", "[class*='post-content']",
                             "main", ".content", "#content"]:
                el = soup.select_one(selector)
                if el:
                    text = el.get_text(separator=" ")
                    text = re.sub(r'\s+', ' ', text).strip()
                    if len(text) > 200:
                        return text[:1500]

            # Fallback: collect all paragraphs
            paragraphs = soup.find_all("p")
            text = " ".join(p.get_text() for p in paragraphs if len(p.get_text()) > 50)
            return re.sub(r'\s+', ' ', text).strip()[:1500]

        except Exception:
            return ""

    # ── Main Fetch Orchestrator ───────────────────────────────────────────────

    def fetch_by_intent(self, intent: dict, progress_callback=None) -> list:
        """
        Fetch news articles based on parsed AI intent.
        Selects appropriate sources and scraping strategy.
        """
        categories = intent.get("categories", ["global"])
        regions = [r.lower() for r in intent.get("regions", ["global"])]
        search_query = intent.get("search_query", "")
        max_articles = intent.get("max_articles", 10)
        keywords = [k.lower() for k in intent.get("keywords", [])]

        all_articles = []
        seen_titles = set()

        # 1. Google News search (most targeted)
        if search_query:
            if progress_callback:
                progress_callback(f"Searching Google News: '{search_query}'")
            articles = self.scrape_google_news(search_query, max_items=max_articles)
            for a in articles:
                key = a["title"].lower()[:60]
                if key not in seen_titles:
                    seen_titles.add(key)
                    all_articles.append(a)
            time.sleep(0.5)

        # 2. Category-specific RSS feeds
        source_keys = set(["global"])
        for cat in categories:
            cat_lower = cat.lower()
            if cat_lower in RSS_SOURCES:
                source_keys.add(cat_lower)
        for region in regions:
            if region in RSS_SOURCES:
                source_keys.add(region)

        for key in source_keys:
            sources = RSS_SOURCES.get(key, [])
            for src in sources[:3]:  # max 3 sources per category
                if progress_callback:
                    progress_callback(f"Scraping {src['name']}...")
                articles = self.scrape_rss(src["url"], src["name"], max_items=8)

                # Filter by keywords if provided
                if keywords:
                    articles = [
                        a for a in articles
                        if any(
                            kw in a["title"].lower() or kw in a["description"].lower()
                            for kw in keywords
                        )
                    ]

                for a in articles:
                    key_t = a["title"].lower()[:60]
                    if key_t not in seen_titles:
                        seen_titles.add(key_t)
                        all_articles.append(a)

                time.sleep(0.3)  # polite delay

        return all_articles[:max_articles * 2]  # return extras for AI ranking
