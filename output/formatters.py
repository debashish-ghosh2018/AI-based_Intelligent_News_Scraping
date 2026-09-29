"""
Output Formatters
Handles terminal display (rich), JSON export, and Markdown digest export.
"""

import json
import os
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns
from rich import box
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.markdown import Markdown
from rich.rule import Rule
from rich.align import Align

console = Console()


# ─── Terminal Display ──────────────────────────────────────────────────────────

def print_banner():
    banner = Text()
    banner.append("  NewsLens ", style="bold white")
    banner.append("AI-Powered News Intelligence", style="dim white")
    console.print(Panel(Align.center(banner), style="blue", border_style="bright_blue", padding=(0, 2)))
    console.print()


def print_intent_summary(intent: dict):
    """Show the AI-parsed intent as a compact summary."""
    topics = ", ".join(intent.get("topics", []))
    keywords = ", ".join(intent.get("keywords", []))
    regions = ", ".join(intent.get("regions", []))
    categories = ", ".join(intent.get("categories", []))
    date_range = intent.get("date_range", "any")
    max_articles = intent.get("max_articles", 10)

    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    table.add_column("Key", style="dim", width=14)
    table.add_column("Value", style="white")

    table.add_row("Topics", f"[bold cyan]{topics}[/bold cyan]")
    if keywords:
        table.add_row("Keywords", keywords)
    table.add_row("Regions", regions)
    table.add_row("Categories", categories)
    table.add_row("Date range", date_range)
    table.add_row("Max articles", str(max_articles))
    table.add_row("Style", intent.get("summary_style", "brief"))

    console.print(Panel(table, title="[bold blue]AI Intent Parsed[/bold blue]",
                        border_style="blue", padding=(0, 1)))
    console.print()


def print_articles_table(articles: list):
    """Display articles in a rich table."""
    if not articles:
        console.print("[yellow]No articles found.[/yellow]")
        return

    table = Table(
        title=f"[bold]Found {len(articles)} Articles[/bold]",
        box=box.ROUNDED,
        show_lines=True,
        border_style="bright_black",
        header_style="bold bright_blue",
        padding=(0, 1),
    )
    table.add_column("#", style="dim", width=3, justify="right")
    table.add_column("Title", min_width=30, max_width=52)
    table.add_column("Source", style="cyan", width=16)
    table.add_column("Date", style="dim", width=17)
    table.add_column("Score", justify="center", width=6)

    for i, a in enumerate(articles, 1):
        title = a.get("title", "")
        if len(title) > 70:
            title = title[:68] + "…"

        score = a.get("relevance_score", 5)
        if score >= 8:
            score_fmt = f"[bold green]{score}[/bold green]"
        elif score >= 6:
            score_fmt = f"[yellow]{score}[/yellow]"
        else:
            score_fmt = f"[dim]{score}[/dim]"

        date = a.get("date", "")[:16]

        table.add_row(str(i), title, a.get("source", ""), date, score_fmt)

    console.print(table)
    console.print()


def print_summary(summary_text: str, intent: dict):
    """Display AI-generated summary in a panel."""
    topics = ", ".join(intent.get("topics", ["News"]))
    title = f"[bold green]AI Summary — {topics}[/bold green]"
    console.print(Panel(
        Markdown(summary_text),
        title=title,
        border_style="green",
        padding=(1, 2),
    ))
    console.print()


def print_article_detail(article: dict):
    """Display a single article in detail."""
    console.print(Rule(f"[bold cyan]{article.get('source', '')}[/bold cyan]", style="cyan"))
    console.print(f"[bold white]{article.get('title', '')}[/bold white]")
    console.print(f"[dim]{article.get('url', '')}[/dim]")
    console.print(f"[dim]Published: {article.get('date', 'Unknown')}[/dim]")
    console.print()
    content = article.get("content") or article.get("description", "No content available.")
    console.print(content)
    console.print()


# ─── Spinner / Progress ────────────────────────────────────────────────────────

class ScrapeProgress:
    def __init__(self, description: str = "Fetching news..."):
        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("[cyan]{task.description}"),
            transient=True,
            console=console,
        )
        self._task = None
        self._description = description

    def __enter__(self):
        self._progress.__enter__()
        self._task = self._progress.add_task(self._description)
        return self

    def update(self, text: str):
        if self._task is not None:
            self._progress.update(self._task, description=text)

    def __exit__(self, *args):
        self._progress.__exit__(*args)


# ─── Export Functions ──────────────────────────────────────────────────────────

def export_json(articles: list, summary: str, intent: dict, filepath: str):
    """Export results to a JSON file."""
    data = {
        "query_intent": intent,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "article_count": len(articles),
        "ai_summary": summary,
        "articles": articles,
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    console.print(f"[green]Exported JSON → {filepath}[/green]")


def export_markdown(articles: list, summary: str, intent: dict, filepath: str):
    """Export results as a Markdown digest."""
    topics = ", ".join(intent.get("topics", ["News"]))
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        f"# NewsLens Digest — {topics}",
        f"*Generated: {now}*",
        "",
        "---",
        "",
        "## AI Summary",
        "",
        summary,
        "",
        "---",
        "",
        f"## Articles ({len(articles)} found)",
        "",
    ]

    for i, a in enumerate(articles, 1):
        lines.append(f"### {i}. {a.get('title', 'Untitled')}")
        lines.append(f"**Source:** {a.get('source', 'Unknown')} | "
                     f"**Date:** {a.get('date', 'Unknown')} | "
                     f"**Relevance:** {a.get('relevance_score', '?')}/10")
        lines.append("")
        lines.append(a.get("description", ""))
        lines.append("")
        lines.append(f"[Read full article]({a.get('url', '#')})")
        lines.append("")
        lines.append("---")
        lines.append("")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    console.print(f"[green]Exported Markdown → {filepath}[/green]")


def export_csv(articles: list, filepath: str):
    """Export articles as CSV."""
    import csv
    fields = ["title", "source", "date", "relevance_score", "url", "description"]
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(articles)
    console.print(f"[green]Exported CSV → {filepath}[/green]")
