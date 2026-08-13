import sys
import time
import requests

DISCOGS_TOKEN = "Discogs_Token_Here"

HEADERS = {
    "User-Agent": "Pycogs/1.0 (by TheMangler47)",
    "Authorization": f"Discogs token={DISCOGS_TOKEN}"
}

BASE_URL = "https://api.discogs.com"
GITHUB_URL = "https://github.com/TheMangler47"

def type_writer(text, delay=0.02):
    """Prints text with a retro typing animation."""
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print()

def make_clickable_url(url, label=None):
    """Formats The Github Link To Be Clickable Lolz"""
    if label is None:
        label = url
    return f"\033]8;;{url}\033\\{label}\033]8;;\033\\"

def show_banner():
    """Displays the Pycogs intro screen."""
    banner = r"""
  _____  _   _  _____ ____   _____  _____ 
 |  __ \| | | |/ ____/ __ \ / ____|/ ____|
 | |__) | |_| | |   | |  | | |  __| (___  
 |  ___/ \__  | |   | |  | | | |_ |\___ \ 
 | |        | | |___| |__| | |__| |____) |
 |_|        |_|\_____\____/ \_____|_____/ 
    """
    print(banner)
    type_writer(">> PYCOGS — Discogs API Explorer v1.2", 0.02)
    type_writer(">> Developed by: TheMangler47", 0.02)
    
    clickable_git = ">> GitHub: " + make_clickable_url(GITHUB_URL)
    type_writer(clickable_git, 0.02)
    
    type_writer(">> Authenticated & Ready", 0.02)
    time.sleep(0.3)
    print("=" * 55 + "\n")

def loading_spinner(seconds=1.5, message="Processing"):
    """Displays an animated spinner in the terminal."""
    spinner_symbols = ["|", "/", "-", "\\"]
    end_time = time.time() + seconds
    i = 0
    while time.time() < end_time:
        sys.stdout.write(f"\r[ {spinner_symbols[i % len(spinner_symbols)]} ] {message}...")
        sys.stdout.flush()
        time.sleep(0.1)
        i += 1
    sys.stdout.write("\r" + " " * (len(message) + 15) + "\r")
    sys.stdout.flush()

def search_artist(artist_name):
    """Search for an artist by name and return their verified Discogs ID & Name."""
    search_url = f"{BASE_URL}/database/search"
    params = {"q": artist_name, "type": "artist"}
    
    response = requests.get(search_url, headers=HEADERS, params=params)
    
    if response.status_code != 200:
        print(f"\n[!] Error fetching search results: {response.status_code}")
        return None
        
    results = response.json().get("results", [])
    if not results:
        print(f"\n[!] No artist found with name: '{artist_name}'")
        return None
        
    return {
        "id": results[0].get("id"),
        "title": results[0].get("title")
    }

def fetch_discography_by_format(artist_name, choice):
    """
    Queries Discogs Search API directly using explicit format filters
    to cleanly separate Albums from Singles/EPs/Compilations.
    """
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
        print("Invalid choice. Defaulting to Albums.")
        params["format"] = "album"

    response = requests.get(search_url, headers=HEADERS, params=params)
    
    if response.status_code != 200:
        print(f"\n[!] Error fetching discography: {response.status_code}")
        return []
        
    results = response.json().get("results", [])
    results.sort(key=lambda x: str(x.get("year", "9999")))
    return results

def run_app():
    """Main execution block inside the program loop."""
    artist_name = input("Enter artist/band name (or 'q' to quit): ").strip()
    
    if artist_name.lower() in ["q", "quit", "exit"]:
        return False

    if not artist_name:
        print("[!] No name entered. Try again.\n")
        return True

    loading_spinner(seconds=1.2, message=f"Searching for '{artist_name}'")
    
    artist_info = search_artist(artist_name)
    if not artist_info:
        print()
        return True
        
    verified_name = artist_info['title']
    print(f"✔ Found Artist: {verified_name} (ID: {artist_info['id']})\n")

    print("-" * 55)
    print(" Select release type to filter:")
    print("  [1] Studio Albums ONLY (Filtered by Album format)")
    print("  [2] Compilations ONLY (Greatest Hits, Collections)")
    print("  [3] Singles & EPs ONLY")
    print("  [4] All Master Entries (Albums + Singles + Compilations)")
    print("  [5] Everything (Includes features, promos, formats)")
    print("-" * 55)
    
    filter_choice = input("Enter choice (1-5): ").strip()
    
    print()
    loading_spinner(seconds=1.8, message=f"Fetching discography for {verified_name}")
    
    results = fetch_discography_by_format(verified_name, filter_choice)
    
    print(f"\n=======================================================")
    print(f" PYCOGS DISCOGRAPHY: {verified_name.upper()}")
    print(f" Total Entries Found: {len(results)}")
    print(f"=======================================================\n")
    
    if not results:
        print("No entries match the selected filter criteria.\n")
    else:
        for item in results:
            year = item.get("year", "N/A")
            title = item.get("title", "Unknown Title")
            formats = ", ".join(item.get("format", [])) if isinstance(item.get("format"), list) else item.get("format", "N/A")
            item_id = item.get("id")
            
            display_title = title.split(" - ", 1)[-1] if " - " in title else title
            
            print(f" • [{year}] {display_title}")
            print(f"   └── Formats: {formats} | Master ID: {item_id}\n")

    print("=" * 55)
    again = input("Search for another artist? (Y/n): ").strip().lower()
    if again in ["n", "no", "q", "quit", "exit"]:
        return False
        
    print("\n" + "=" * 55 + "\n")
    return True

def main():
    show_banner()
    
    try:
        keep_running = True
        while keep_running:
            keep_running = run_app()
            
        print("\nThank you for using Pycogs! Goodbye!")
        print("\nhttps://github.com/themangler47/Pycogs")
    except KeyboardInterrupt:
        print("\n\n[!] Program interrupted (Ctrl+C). Exiting Pycogs... Goodbye!")
        sys.exit(0)

if __name__ == "__main__":
    main()