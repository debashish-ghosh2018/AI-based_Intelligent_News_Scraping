"""
CLI Controller
Main interactive REPL loop for NewsLens.
"""

import os
import sys
from pathlib import Path
from datetime import datetime

from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.text import Text
from rich.rule import Rule
from rich import box

from core.ai_parser import parse_intent, summarise_articles, score_relevance
from core.scraper import NewsScraper
from output.formatters import (
    console,
    print_banner,
    print_intent_summary,
    print_articles_table,
    print_summary,
    print_article_detail,
    ScrapeProgress,
    export_json,
    export_markdown,
    export_csv,
)
from utils.config import get_api_key, save_api_key, get_output_dir


# ─── Setup ────────────────────────────────────────────────────────────────────

def setup_api_key() -> str:
    """Prompt user to enter and save their Anthropic API key."""
    console.print()
    console.print(Panel(
        "[white]NewsLens uses the [bold cyan]Anthropic Claude API[/bold cyan] to parse your queries "
        "and summarise articles intelligently.\n\n"
        "Get a free API key at: [blue underline]https://console.anthropic.com[/blue underline]",
        title="[bold yellow]API Key Required[/bold yellow]",
        border_style="yellow",
        padding=(1, 2),
    ))
    console.print()

    key = Prompt.ask("[yellow]Enter your Anthropic API key[/yellow]", password=True)
    if not key.startswith("sk-ant-"):
        console.print("[red]Warning: key doesn't look like a valid Anthropic key (should start with sk-ant-)[/red]")

    save_it = Confirm.ask("Save key to ~/.newslens/config.json for future sessions?", default=True)
    if save_it:
        save_api_key(key)
        console.print("[green]Key saved.[/green]")

    return key


# ─── Query Processing Pipeline ─────────────────────────────────────────────────

def process_query(query: str, api_key: str) -> tuple[list, dict, str]:
    """
    Full pipeline: parse → scrape → score → summarise.
    Returns (articles, intent, summary).
    """
    scraper = NewsScraper()

    # Step 1: AI Intent Parsing
    with ScrapeProgress("AI parsing your query...") as sp:
        intent = parse_intent(query, api_key)

    print_intent_summary(intent)

    # Step 2: Scraping
    articles = []
    with ScrapeProgress("Fetching articles from news sources...") as sp:
        def on_progress(msg):
            sp.update(msg)
        articles = scraper.fetch_by_intent(intent, progress_callback=on_progress)

    if not articles:
        console.print("[yellow]No articles found. Try a broader query.[/yellow]")
        return [], intent, ""

    console.print(f"[dim]Scraped {len(articles)} raw articles[/dim]")

    # Step 3: AI Relevance Scoring
    with ScrapeProgress(f"AI scoring relevance of {len(articles)} articles...") as sp:
        articles = score_relevance(articles, intent, api_key)

    # Trim to max_articles
    max_a = intent.get("max_articles", 10)
    articles = articles[:max_a]

    # Step 4: AI Summarisation
    with ScrapeProgress("Generating AI summary...") as sp:
        summary = summarise_articles(articles, intent, api_key)

    return articles, intent, summary


# ─── Post-Results Menu ────────────────────────────────────────────────────────

def post_results_menu(articles: list, intent: dict, summary: str):
    """Interactive menu after results are shown."""
    while True:
        console.print(Rule(style="bright_black"))
        console.print("[dim]What would you like to do next?[/dim]")
        console.print("  [cyan]1[/cyan] Read a specific article in detail")
        console.print("  [cyan]2[/cyan] Export as JSON")
        console.print("  [cyan]3[/cyan] Export as Markdown digest")
        console.print("  [cyan]4[/cyan] Export as CSV")
        console.print("  [cyan]5[/cyan] New search")
        console.print("  [cyan]6[/cyan] Quit")
        console.print()

        choice = Prompt.ask("[cyan]Choice[/cyan]", choices=["1","2","3","4","5","6"], default="5")

        if choice == "1":
            num = Prompt.ask(f"Article number (1–{len(articles)})")
            try:
                idx = int(num) - 1
                if 0 <= idx < len(articles):
                    print_article_detail(articles[idx])
                else:
                    console.print("[red]Invalid number.[/red]")
            except ValueError:
                console.print("[red]Please enter a number.[/red]")

        elif choice == "2":
            out_dir = get_output_dir()
            Path(out_dir).mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(out_dir, f"newslens_{ts}.json")
            export_json(articles, summary, intent, path)

        elif choice == "3":
            out_dir = get_output_dir()
            Path(out_dir).mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(out_dir, f"newslens_{ts}.md")
            export_markdown(articles, summary, intent, path)

        elif choice == "4":
            out_dir = get_output_dir()
            Path(out_dir).mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(out_dir, f"newslens_{ts}.csv")
            export_csv(articles, path)

        elif choice == "5":
            return True   # signal: new search

        elif choice == "6":
            return False  # signal: quit


# ─── Example Queries ──────────────────────────────────────────────────────────

EXAMPLE_QUERIES = [
    "Latest AI and machine learning news this week",
    "India economy news today",
    "US politics latest developments",
    "Climate change and environment news",
    "Global stock market and finance updates",
    "Technology startups and funding news",
    "Sports results and highlights today",
    "Health and medical breakthroughs",
]


def print_examples():
    console.print("[dim]Example queries:[/dim]")
    for i, q in enumerate(EXAMPLE_QUERIES[:5], 1):
        console.print(f"  [dim cyan]{i}.[/dim cyan] [dim]{q}[/dim]")
    console.print()


# ─── Main REPL ────────────────────────────────────────────────────────────────

def run_cli():
    print_banner()

    # API key check
    api_key = get_api_key()
    if not api_key:
        api_key = setup_api_key()
        if not api_key:
            console.print("[red]No API key provided. Exiting.[/red]")
            sys.exit(1)

    console.print("[green]Claude API key loaded.[/green]")
    console.print()

    # Main loop
    while True:
        console.print(Rule("[bold white]New Search[/bold white]", style="bright_black"))
        console.print()
        print_examples()

        query = Prompt.ask(
            "[bold white]What news are you looking for?[/bold white]",
            default=""
        ).strip()

        if not query:
            console.print("[yellow]Please enter a query.[/yellow]")
            continue

        if query.lower() in ("exit", "quit", "q", "bye"):
            console.print("[dim]Goodbye.[/dim]")
            break

        console.print()

        try:
            articles, intent, summary = process_query(query, api_key)
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            if "api" in str(e).lower() or "auth" in str(e).lower() or "key" in str(e).lower():
                retry = Confirm.ask("Re-enter API key?", default=True)
                if retry:
                    api_key = setup_api_key()
            continue

        if not articles:
            continue

        print_articles_table(articles)
        print_summary(summary, intent)

        keep_going = post_results_menu(articles, intent, summary)
        if not keep_going:
            console.print("[dim]Goodbye.[/dim]")
            break

        console.print()
