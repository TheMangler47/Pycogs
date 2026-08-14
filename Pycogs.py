import os
import sys
import time
import json
import csv
import sqlite3
import requests

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

DISCOGS_TOKEN = "Discogs_Token_Here"

HEADERS = {
    "User-Agent": "Pycogs/1.1 (by TheMangler47)",
    "Authorization": f"Discogs token={DISCOGS_TOKEN}"
}

BASE_URL = "https://api.discogs.com"
GITHUB_URL = "https://github.com/TheMangler47"
DB_FILE = "pycogs_cache.db"

console = Console()


def init_db():
    """Initializes SQLite database tables for local API response caching."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS search_cache (
            cache_key TEXT PRIMARY KEY,
            data_json TEXT,
            timestamp REAL
        )
    """)
    conn.commit()
    conn.close()

def get_cached_data(cache_key, max_age_seconds=86400):
    """Retrieves cached json if it exists and is not expired (default 24h)."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT data_json, timestamp FROM search_cache WHERE cache_key = ?", (cache_key,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        data_json, timestamp = row
        if time.time() - timestamp < max_age_seconds:
            return json.loads(data_json)
    return None

def set_cached_data(cache_key, data):
    """Saves data dictionary/list to SQLite cache."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO search_cache (cache_key, data_json, timestamp)
        VALUES (?, ?, ?)
    """, (cache_key, json.dumps(data), time.time()))
    conn.commit()
    conn.close()


def make_clickable_url(url, label=None):
    if label is None:
        label = url
    return f"\033]8;;{url}\033\\{label}\033]8;;\033\\"

def show_banner():
    banner_text = r"""[bold cyan]
  _____  _   _  _____ ____   _____  _____ 
 |  __ \| | | |/ ____/ __ \ / ____|/ ____|
 | |__) | |_| | |   | |  | | |  __| (___  
 |  ___/ \__  | |   | |  | | | |_ |\___ \ 
 | |        | | |___| |__| | |__| |____) |
 |_|        |_|\_____\____/ \_____|_____/ 
[/bold cyan]"""
    console.print(banner_text)
    console.print("[bold yellow]>> PYCOGS — Discogs API Explorer v1.1[/bold yellow]")
    console.print("[bold green]>> Developed by: TheMangler47[/bold green]")
    
    clickable_git = make_clickable_url(GITHUB_URL, "https://github.com/TheMangler47")
    console.print(f"[bold magenta]>> GitHub: {clickable_git}[/bold magenta]")
    console.print("[dim]>> Authenticated & SQLite Cache Active[/dim]\n" + "=" * 60 + "\n")


def search_artist(artist_name):
    """Search for an artist by name with cache check."""
    cache_key = f"artist_search:{artist_name.lower().strip()}"
    cached = get_cached_data(cache_key)
    if cached:
        return cached

    search_url = f"{BASE_URL}/database/search"
    params = {"q": artist_name, "type": "artist"}
    
    response = requests.get(search_url, headers=HEADERS, params=params)
    if response.status_code != 200:
        return None
        
    results = response.json().get("results", [])
    if not results:
        return None
        
    artist_data = {
        "id": results[0].get("id"),
        "title": results[0].get("title")
    }
    set_cached_data(cache_key, artist_data)
    return artist_data

def fetch_discography_by_format(artist_name, choice):
    """Queries Discogs Search API with explicit format filters + caching."""
    cache_key = f"discog:{artist_name.lower().strip()}:choice_{choice}"
    cached = get_cached_data(cache_key)
    if cached:
        return cached, True

    search_url = f"{BASE_URL}/database/search"
    params = {
        "artist": artist_name,
        "type": "master",
        "per_page": 100
    }
    
    if choice == "1":
        params["format"] = "album"
    elif choice == "2":
        params["format"] = "compilation"
    elif choice == "3":
        params["format"] = "single"
    elif choice == "4":
        pass
    elif choice == "5":
        params.pop("type")
    else:
        params["format"] = "album"

    response = requests.get(search_url, headers=HEADERS, params=params)
    if response.status_code != 200:
        return [], False
        
    results = response.json().get("results", [])
    
    valid_results = []
    for item in results:
        year_str = str(item.get("year", ""))
        if year_str.isdigit():
            valid_results.append(item)
            
    valid_results.sort(key=lambda x: int(x.get("year", 0)))
    set_cached_data(cache_key, valid_results)
    return valid_results, False


def process_results(raw_results):
    """Parses raw API results including community stats and cover URLs."""
    cleaned = []
    for item in raw_results:
        year = str(item.get("year", "N/A"))
        raw_title = item.get("title", "Unknown Title")
        title = raw_title.split(" - ", 1)[-1] if " - " in raw_title else raw_title
        
        genres = ", ".join(item.get("genre", [])) if item.get("genre") else "N/A"
        styles = ", ".join(item.get("style", [])) if item.get("style") else "N/A"
        labels = ", ".join(item.get("label", [])) if item.get("label") else "N/A"
        master_id = str(item.get("id", "N/A"))
        
        community = item.get("community", {})
        want_count = community.get("want", 0)
        have_count = community.get("have", 0)
        cover_url = item.get("cover_image", item.get("thumb", ""))

        cleaned.append({
            "year": year,
            "title": title,
            "genres": genres,
            "styles": styles,
            "labels": labels,
            "master_id": master_id,
            "want": want_count,
            "have": have_count,
            "cover_url": cover_url
        })
    return cleaned

def display_stats_dashboard(artist_title, data, is_cached):
    """Renders a summary dashboard with career stats."""
    if not data:
        return

    total_releases = len(data)
    first_year = data[0]["year"]
    latest_year = data[-1]["year"]
    
    genre_counts = {}
    for entry in data:
        for g in entry["genres"].split(", "):
            if g != "N/A":
                genre_counts[g] = genre_counts.get(g, 0) + 1
                
    top_genre = max(genre_counts, key=genre_counts.get) if genre_counts else "N/A"
    cache_badge = "[bold green](Loaded from Local SQLite Cache)[/bold green]" if is_cached else "[bold yellow](Fetched via Discogs API)[/bold yellow]"

    stats_text = (
        f"[bold cyan]Artist:[/bold cyan] {artist_title} {cache_badge}\n"
        f"[bold green]Total Discography Entries:[/bold green] {total_releases}\n"
        f"[bold yellow]First Known Release:[/bold yellow] {first_year}\n"
        f"[bold yellow]Latest Release:[/bold yellow] {latest_year}\n"
        f"[bold magenta]Primary Genre:[/bold magenta] {top_genre}"
    )
    
    console.print(Panel(stats_text, title="[bold white]CAREER DASHBOARD[/bold white]", border_style="cyan"))

def display_formatted_table(data):
    """Renders data into a clean, color-coded Rich Table."""
    table = Table(title="[bold yellow]Pycogs Discography Results[/bold yellow]", show_lines=True)
    
    table.add_column("Year", style="bold cyan", justify="center")
    table.add_column("Title", style="bold white")
    table.add_column("Genre / Styles", style="magenta")
    table.add_column("Label(s)", style="green")
    table.add_column("Have / Want", style="yellow", justify="center")
    table.add_column("Master ID", style="dim", justify="right")
    
    for row in data:
        genre_style_str = f"{row['genres']}\n[italic dim]({row['styles']})[/italic dim]"
        stats_str = f"H: {row['have']} | W: {row['want']}"
        
        table.add_row(
            row["year"],
            row["title"],
            genre_style_str,
            row["labels"],
            stats_str,
            row["master_id"]
        )
        
    console.print(table)


def download_covers(artist_name, data):
    """Downloads thumbnail cover art to a local covers/ folder."""
    covers_dir = os.path.join("covers", artist_name.replace(" ", "_").lower())
    os.makedirs(covers_dir, exist_ok=True)
    
    downloaded = 0
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), BarColumn(), transient=True) as progress:
        task = progress.add_task("Downloading album covers...", total=len(data))
        for item in data:
            url = item.get("cover_url")
            if url and url.startswith("http"):
                safe_title = "".join(c for c in item['title'] if c.isalnum() or c in (' ', '_')).strip().replace(' ', '_')
                file_path = os.path.join(covers_dir, f"{item['year']}_{safe_title}.jpg")
                
                if not os.path.exists(file_path):
                    try:
                        res = requests.get(url, headers=HEADERS, timeout=5)
                        if res.status_code == 200:
                            with open(file_path, "wb") as img_file:
                                img_file.write(res.content)
                            downloaded += 1
                    except Exception:
                        pass
            progress.advance(task)

    console.print(f"[bold green]✔ Downloaded {downloaded} cover image(s) to '[cyan]{covers_dir}[/cyan]'[/bold green]")

def export_data(artist_name, data):
    """Handles export choices (JSON, CSV, Markdown, Covers)."""
    console.print("\n[bold cyan]Export Options:[/bold cyan]")
    console.print(" [1] JSON File (.json)")
    console.print(" [2] CSV Spreadsheet (.csv)")
    console.print(" [3] Markdown Checklist (.md)")
    console.print(" [4] Download Cover Art Images to local folder")
    console.print(" [5] Skip Export")
    
    choice = input("\nSelect export format (1-5): ").strip()
    clean_filename = "".join(c for c in artist_name if c.isalnum() or c in (' ', '_')).rstrip().replace(' ', '_').lower()

    if choice == "1":
        filepath = f"{clean_filename}_discography.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        console.print(f"[bold green]✔ Saved to {filepath}[/bold green]")

    elif choice == "2":
        filepath = f"{clean_filename}_discography.csv"
        fieldnames = ["year", "title", "genres", "styles", "labels", "have", "want", "master_id", "cover_url"]
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        console.print(f"[bold green]✔ Saved to {filepath}[/bold green]")

    elif choice == "3":
        filepath = f"{clean_filename}_checklist.md"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# Discography Checklist: {artist_name}\n\n")
            f.write("Generated via **Pycogs v1.1** by TheMangler47\n\n")
            for item in data:
                f.write(f"- [ ] **[{item['year']}]** {item['title']} *(Label: {item['labels']})*\n")
        console.print(f"[bold green]✔ Saved to {filepath}[/bold green]")

    elif choice == "4":
        download_covers(artist_name, data)


def run_app():
    artist_name = console.input("[bold yellow]Enter artist/band name (or 'q' to quit): [/bold yellow]").strip()
    
    if artist_name.lower() in ["q", "quit", "exit"]:
        return False

    if not artist_name:
        console.print("[bold red][!] No name entered. Try again.\n[/bold red]")
        return True

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), BarColumn(), transient=True) as progress:
        task = progress.add_task(f"Searching Discogs for '{artist_name}'...", total=100)
        artist_info = search_artist(artist_name)
        progress.update(task, completed=100)
    
    if not artist_info:
        console.print(f"[bold red][!] Could not find artist: '{artist_name}'[/bold red]\n")
        return True
        
    verified_name = artist_info['title']
    console.print(f"[bold green]✔ Found Artist:[/bold green] {verified_name} [dim](ID: {artist_info['id']})[/dim]\n")

    console.print("[cyan]" + "-" * 60 + "[/cyan]")
    console.print(" [bold white]Select release type to filter:[/bold white]")
    console.print("  [1] Studio Albums ONLY")
    console.print("  [2] Compilations ONLY")
    console.print("  [3] Singles & EPs ONLY")
    console.print("  [4] All Master Entries (Albums + Singles + Compilations)")
    console.print("  [5] Everything (Unfiltered raw data)")
    console.print("[cyan]" + "-" * 60 + "[/cyan]")
    
    filter_choice = input("Enter choice (1-5): ").strip()

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), BarColumn(), transient=True) as progress:
        task = progress.add_task(f"Fetching discography metadata for {verified_name}...", total=100)
        raw_results, is_cached = fetch_discography_by_format(verified_name, filter_choice)
        progress.update(task, completed=100)

    processed_data = process_results(raw_results)

    if not processed_data:
        console.print("\n[bold red]No entries match the selected criteria.[/bold red]\n")
        return True

    console.print()
    display_stats_dashboard(verified_name, processed_data, is_cached)
    console.print()
    display_formatted_table(processed_data)
    
    export_data(verified_name, processed_data)

    console.print("\n" + "=" * 60)
    again = console.input("[bold yellow]Search for another artist? (Y/n): [/bold yellow]").strip().lower()
    if again in ["n", "no", "q", "quit", "exit"]:
        return False
        
    console.print("\n" + "=" * 60 + "\n")
    return True

def main():
    init_db()
    show_banner()
    try:
        keep_running = True
        while keep_running:
            keep_running = run_app()
            
        console.print("\n[bold cyan]Thank you for using Pycogs v1.1! Goodbye![/bold cyan]")
    except KeyboardInterrupt:
        console.print("\n\n[bold red][!] Program interrupted (Ctrl+C). Exiting Pycogs... Goodbye![/bold red]")
        sys.exit(0)

if __name__ == "__main__":
    main()
