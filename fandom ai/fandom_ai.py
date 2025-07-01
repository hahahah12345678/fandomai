import requests
from bs4 import BeautifulSoup
from transformers import pipeline
import sys
import re
from urllib.parse import urlparse

# Load summarization and QA pipelines (uses small open-source models)
summarizer = pipeline('summarization', model='sshleifer/distilbart-cnn-12-6')
qa = pipeline('question-answering', model='distilbert-base-uncased-distilled-squad')

# --- New: Fandom full search ---
def get_all_fandom_pages(base_url):
    """Get all article URLs from the Fandom wiki's All Pages list."""
    # Try to find the 'All Pages' special page
    parsed = urlparse(base_url)
    root = f"{parsed.scheme}://{parsed.netloc}"
    allpages_url = root + "/wiki/Special:AllPages"
    resp = requests.get(allpages_url)
    if resp.status_code != 200:
        print("Could not fetch All Pages list.")
        return []
    soup = BeautifulSoup(resp.text, 'html.parser')
    links = soup.select('ul.mw-allpages-chunk li a')
    return [root + link['href'] for link in links if link.has_attr('href')]

def search_fandom_for_article(base_url, search_term):
    """Scan all pages for the one most relevant to the search term."""
    print(f"Searching all pages for '{search_term}' (this may take a while)...")
    pages = get_all_fandom_pages(base_url)
    best_match = None
    best_score = 0
    for url in pages:
        try:
            resp = requests.get(url, timeout=10)
            soup = BeautifulSoup(resp.text, 'html.parser')
            content = soup.find('div', {'class': 'mw-parser-output'})
            if not content:
                continue
            text = content.get_text(separator=' ', strip=True)
            score = text.lower().count(search_term.lower())
            if score > best_score:
                best_score = score
                best_match = (url, text[:500])
        except Exception:
            continue
    if best_match:
        print(f"Best match: {best_match[0]}\nPreview: {best_match[1]}...")
    else:
        print("No relevant article found.")

# --- New: List all sections on the current page ---
def list_sections(text):
    print("Sections on this page:")
    for line in text.splitlines():
        if re.match(r"^=+[^=]+=+$", line.strip()):
            print("-", line.strip().strip('=').strip())

# --- New: Extract all links from the current page ---
def list_links(url):
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text, 'html.parser')
    links = soup.select('div.mw-parser-output a[href^="/wiki/"]')
    print("Links on this page:")
    for link in links:
        print("-", link.get('href'))

# --- New: Summarize a specific section ---
def summarize_section(text, section):
    pattern = re.compile(rf"=+\s*{re.escape(section)}\s*=+(.*?)(=+[^=]+=+|$)", re.IGNORECASE | re.DOTALL)
    match = pattern.search(text)
    if match:
        section_text = match.group(1).strip()
        if section_text:
            print("Summarizing section, please wait...")
            summary = summarizer(section_text[:2000], max_length=120, min_length=30, do_sample=False)[0]['summary_text']
            print("\nSection Summary:\n" + summary)
            return
    print("Section not found or empty.")

# --- New: Extract infobox data ---
def extract_infobox(url):
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text, 'html.parser')
    infobox = soup.find('table', {'class': 'infobox'})
    if not infobox:
        print("No infobox found on this page.")
        return
    print("Infobox data:")
    for row in infobox.find_all('tr'):
        th = row.find('th')
        td = row.find('td')
        if th and td:
            print(f"- {th.get_text(strip=True)}: {td.get_text(strip=True)}")

def fetch_fandom_page(url):
    resp = requests.get(url)
    if resp.status_code != 200:
        print(f"Failed to fetch page: {resp.status_code}")
        sys.exit(1)
    soup = BeautifulSoup(resp.text, 'html.parser')
    # Get main content text
    content = soup.find('div', {'class': 'mw-parser-output'})
    if not content:
        print("Could not find main content on the page.")
        sys.exit(1)
    text = content.get_text(separator=' ', strip=True)
    return text

def main():
    print("Fandom AI (Open Source, No API Key)")
    url = input("Enter Fandom wiki URL: ").strip()
    text = fetch_fandom_page(url)
    print("\nPage loaded. Type a command:")
    print("summarize | find <term> | ask <question> | fullsearch <term> | sections | links | sumsection <section> | infobox | exit")
    while True:
        cmd = input("\n> ").strip()
        if cmd == 'exit':
            break
        elif cmd == 'summarize':
            print("Summarizing, please wait...")
            summary = summarizer(text[:2000], max_length=120, min_length=30, do_sample=False)[0]['summary_text']
            print("\nSummary:\n" + summary)
        elif cmd.startswith('find '):
            term = cmd[5:].strip().lower()
            if term in text.lower():
                print(f"Found '{term}' in the page!")
            else:
                print(f"'{term}' not found in the page.")
        elif cmd.startswith('ask '):
            question = cmd[4:].strip()
            print("Thinking...")
            answer = qa({'question': question, 'context': text[:2000]})['answer']
            print(f"\nAnswer: {answer}")
        elif cmd.startswith('fullsearch '):
            search_term = cmd[10:].strip()
            search_fandom_for_article(url, search_term)
        elif cmd == 'sections':
            list_sections(text)
        elif cmd == 'links':
            list_links(url)
        elif cmd.startswith('sumsection '):
            section = cmd[11:].strip()
            summarize_section(text, section)
        elif cmd == 'infobox':
            extract_infobox(url)
        else:
            print("Unknown command. Type one of: summarize, find <term>, ask <question>, fullsearch <term>, sections, links, sumsection <section>, infobox, exit.")

if __name__ == "__main__":
    main()
