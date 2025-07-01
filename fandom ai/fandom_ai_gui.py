import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
import threading
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse
import os
import json
import openai
import pathlib

# Built-in fandoms for quick selection
FANDOMS = {
    "Bee Swarm Simulator": "https://bee-swarm-simulator.fandom.com/wiki/Codes",
    "Minecraft": "https://minecraft.fandom.com/wiki/Minecraft_Wiki",
    "Roblox": "https://roblox.fandom.com/wiki/Roblox_Wiki",
    "Pokémon": "https://pokemon.fandom.com/wiki/Pokémon_Wiki",
    "Fortnite": "https://fortnite.fandom.com/wiki/Fortnite_Wiki"
}

# --- New: Settings for model selection and API key ---
class Settings:
    def __init__(self):
        self.model = 'Open Source'
        self.api_key = ''

settings = Settings()

CONFIG_PATH = os.path.join(pathlib.Path.home(), "fandom_ai_config.json")

# --- Config management ---
def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_config(config):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f)
    except Exception:
        pass

def get_all_fandom_pages(base_url):
    parsed = urlparse(base_url)
    root = f"{parsed.scheme}://{parsed.netloc}"
    allpages_url = root + "/wiki/Special:AllPages"
    resp = requests.get(allpages_url)
    if resp.status_code != 200:
        return []
    soup = BeautifulSoup(resp.text, 'html.parser')
    links = soup.select('ul.mw-allpages-chunk li a')
    return [root + link['href'] for link in links if link.has_attr('href')]

def fetch_fandom_page(url):
    resp = requests.get(url)
    if resp.status_code != 200:
        return None
    soup = BeautifulSoup(resp.text, 'html.parser')
    content = soup.find('div', {'class': 'mw-parser-output'})
    if not content:
        return None
    return content.get_text(separator=' ', strip=True)

def scan_all_pages(base_url, search_term, output_box):
    output_box.insert(tk.END, f"\nScanning all pages for '{search_term}'...\n")
    pages = get_all_fandom_pages(base_url)
    best_match = None
    best_score = 0
    for url in pages:
        try:
            text = fetch_fandom_page(url)
            if not text:
                continue
            score = text.lower().count(search_term.lower())
            if score > best_score:
                best_score = score
                best_match = (url, text[:500])
        except Exception:
            continue
    if best_match:
        output_box.insert(tk.END, f"Best match: {best_match[0]}\nPreview: {best_match[1]}...\n")
    else:
        output_box.insert(tk.END, "No relevant article found.\n")

def ask_question(text, question, output_box):
    output_box.insert(tk.END, "Local AI is not available. Please use an API model.\n")

def summarize_text(text, output_box):
    output_box.insert(tk.END, "Local AI is not available. Please use an API model.\n")

def list_sections(text, output_box):
    output_box.insert(tk.END, "Sections on this page:\n")
    for line in text.splitlines():
        if re.match(r"^=+[^=]+=+$", line.strip()):
            output_box.insert(tk.END, f"- {line.strip().strip('=').strip()}\n")

def list_links(url, output_box):
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text, 'html.parser')
    links = soup.select('div.mw-parser-output a[href^="/wiki/"]')
    output_box.insert(tk.END, "Links on this page:\n")
    for link in links:
        output_box.insert(tk.END, f"- {link.get('href')}\n")

def summarize_section(text, section, output_box):
    output_box.insert(tk.END, "Local AI is not available. Please use an API model.\n")

def extract_infobox(url, output_box):
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text, 'html.parser')
    infobox = soup.find('table', {'class': 'infobox'})
    if not infobox:
        output_box.insert(tk.END, "No infobox found on this page.\n")
        return
    output_box.insert(tk.END, "Infobox data:\n")
    for row in infobox.find_all('tr'):
        th = row.find('th')
        td = row.find('td')
        if th and td:
            output_box.insert(tk.END, f"- {th.get_text(strip=True)}: {td.get_text(strip=True)}\n")

def gpt35_turbo_chat(messages, api_key):
    if not openai:
        raise ImportError("openai package not installed. Please install openai.")
    openai.api_key = api_key
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages,
        max_tokens=512,
        temperature=0.7
    )
    return response.choices[0].message['content']

# --- GUI update ---
def run_gui():
    config = load_config()
    root = tk.Tk()
    root.title("Fandom AI Chat (Open Source, GPT-3.5 Turbo, Gemini, Claude)")
    root.geometry("1100x800")

    # --- Sidebar for page list ---
    sidebar = tk.Frame(root, width=250, bg="#f0f0f0")
    sidebar.pack(side=tk.LEFT, fill=tk.Y)
    tk.Label(sidebar, text="Fandom Pages", bg="#f0f0f0", font=("Arial", 12, "bold")).pack(pady=5)
    page_listbox = tk.Listbox(sidebar, width=38, height=40)
    page_listbox.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)
    page_scroll = tk.Scrollbar(sidebar, orient=tk.VERTICAL, command=page_listbox.yview)
    page_listbox.config(yscrollcommand=page_scroll.set)
    page_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    # --- Main area ---
    main_frame = tk.Frame(root)
    main_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    tk.Label(main_frame, text="Select a Fandom:").pack()
    fandom_var = tk.StringVar(value=list(FANDOMS.keys())[0])
    fandom_menu = ttk.Combobox(main_frame, textvariable=fandom_var, values=list(FANDOMS.keys()), state="readonly", width=40)
    fandom_menu.pack()

    tk.Label(main_frame, text="Or enter a Fandom Wiki URL:").pack()
    url_entry = tk.Entry(main_frame, width=80)
    url_entry.pack()

    # Model selector (now with more AIs)
    tk.Label(main_frame, text="Model:").pack()
    model_var = tk.StringVar(value="GPT-3.5 Turbo")
    model_menu = ttk.Combobox(main_frame, textvariable=model_var, values=["GPT-3.5 Turbo", "Gemini Pro", "Claude 3"], state="readonly", width=20)
    model_menu.pack()

    # API key entries for each AI
    tk.Label(main_frame, text="OpenAI API Key (for GPT-3.5 Turbo, required):").pack()
    openai_key_var = tk.StringVar(value=config.get("openai_api_key", ""))
    openai_key_entry = tk.Entry(main_frame, width=60, show="*", textvariable=openai_key_var)
    openai_key_entry.pack()

    tk.Label(main_frame, text="Gemini API Key (for Gemini Pro, required):").pack()
    gemini_key_var = tk.StringVar(value=config.get("gemini_api_key", ""))
    gemini_key_entry = tk.Entry(main_frame, width=60, show="*", textvariable=gemini_key_var)
    gemini_key_entry.pack()

    tk.Label(main_frame, text="Claude API Key (for Claude 3, required):").pack()
    claude_key_var = tk.StringVar(value=config.get("claude_api_key", ""))
    claude_key_entry = tk.Entry(main_frame, width=60, show="*", textvariable=claude_key_var)
    claude_key_entry.pack()

    # Info label for API key requirement
    tk.Label(main_frame, text="API key required for all models. No local AI available.", fg="red", font=("Arial", 10, "bold")).pack(pady=(5, 10))

    # Add Get API Key button
    def open_payment_link():
        import webbrowser
        webbrowser.open("https://docs.google.com/document/d/1lBcQgSoednp8mwv1-KSPcjxXeRSf7TrcaXuLE8dRJmE/edit?tab=t.0")
    tk.Button(main_frame, text="Get your API key", command=open_payment_link, bg="#4CAF50", fg="white", font=("Arial", 11, "bold")).pack(pady=5)

    # --- New Features ---
    # Dark mode toggle
    dark_mode = [False]
    def toggle_dark_mode():
        if not dark_mode[0]:
            root.configure(bg="#222")
            main_frame.configure(bg="#222")
            sidebar.configure(bg="#222")
            output_box.configure(bg="#222", fg="#fff", insertbackground="#fff")
            loading_label.configure(bg="#222", fg="#0af")
            chat_entry.configure(bg="#333", fg="#fff", insertbackground="#fff")
        else:
            root.configure(bg=None)
            main_frame.configure(bg=None)
            sidebar.configure(bg="#f0f0f0")
            output_box.configure(bg=None, fg=None, insertbackground=None)
            loading_label.configure(bg=None, fg="blue")
            chat_entry.configure(bg=None, fg=None, insertbackground=None)
        dark_mode[0] = not dark_mode[0]
    tk.Button(main_frame, text="Toggle Dark Mode", command=toggle_dark_mode, font=("Arial", 10)).pack(pady=2)

    # Clear chat button
    def clear_chat():
        output_box.config(state=tk.NORMAL)
        output_box.delete(1.0, tk.END)
        output_box.config(state=tk.DISABLED)
    tk.Button(main_frame, text="Clear Chat", command=clear_chat, font=("Arial", 10)).pack(pady=2)

    # Copy last AI response button
    last_ai_response = [""]
    def print_chat(role, text):
        output_box.config(state=tk.NORMAL)
        output_box.insert(tk.END, f"{role}: {text}\n\n")
        output_box.see(tk.END)
        output_box.config(state=tk.DISABLED)
        if role not in ("You", "System", "[Page Loaded]", "[Error]"):
            last_ai_response[0] = text
    def copy_last_response():
        root.clipboard_clear()
        root.clipboard_append(last_ai_response[0])
    tk.Button(main_frame, text="Copy Last AI Response", command=copy_last_response, font=("Arial", 10)).pack(pady=2)

    # Loading indicator
    loading_var = tk.StringVar(value="")
    loading_label = tk.Label(main_frame, textvariable=loading_var, fg="blue")
    loading_label.pack()

    # Chat-style output
    output_box = scrolledtext.ScrolledText(main_frame, width=90, height=28, wrap=tk.WORD, state=tk.DISABLED, font=("Consolas", 11))
    output_box.pack(pady=5)

    # Chat input
    tk.Label(main_frame, text="Ask anything about the Fandom (e.g. 'find the bee page', 'summarize this wiki', 'what is a Windy Bee?'): ").pack()
    chat_entry = tk.Entry(main_frame, width=80, font=("Arial", 12))
    chat_entry.pack()

    # --- Helper functions ---
    def print_chat(role, text):
        output_box.config(state=tk.NORMAL)
        output_box.insert(tk.END, f"{role}: {text}\n\n")
        output_box.see(tk.END)
        output_box.config(state=tk.DISABLED)

    def set_loading(msg):
        loading_var.set(msg)
        root.update_idletasks()

    def get_fandom_url():
        return url_entry.get().strip() or FANDOMS[fandom_var.get()]

    def openai_chat(messages, api_key):
        openai.api_key = api_key
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=600,
                temperature=0.7
            )
            return response.choices[0].message['content']
        except Exception as e:
            return f"[OpenAI Error] {e}"

    import requests as _requests

    def gemini_chat(messages, api_key):
        # Google Gemini API (generative-language API)
        try:
            url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=" + api_key
            data = {
                "contents": [{"parts": [{"text": m['content']} for m in messages if m['role'] == 'user']}]

            }
            resp = _requests.post(url, json=data)
            if resp.status_code == 200:
                out = resp.json()
                return out['candidates'][0]['content']['parts'][0]['text']
            return f"[Gemini API error: {resp.text}]"
        except Exception as e:
            return f"[Gemini API error: {e}]"

    def claude_chat(messages, api_key):
        # Anthropic Claude API (v2023-06-01)
        try:
            url = "https://api.anthropic.com/v1/messages"
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            prompt = "\n\n".join([m['content'] for m in messages if m['role'] == 'user'])
            data = {
                "model": "claude-3-opus-20240229",
                "max_tokens": 600,
                "messages": [{"role": "user", "content": prompt}]
            }
            resp = _requests.post(url, headers=headers, json=data)
            if resp.status_code == 200:
                out = resp.json()
                return out['content'][0]['text']
            return f"[Claude API error: {resp.text}]"
        except Exception as e:
            return f"[Claude API error: {e}]"

    def handle_natural_language(query, base_url, model_choice, api_key):
        print_chat("You", query)
        q = query.lower().strip()
        # --- Conversational intent detection ---
        greetings = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening"]
        farewells = ["bye", "goodbye", "see you", "later", "cya"]
        thanks = ["thanks", "thank you", "thx", "appreciate it"]
        if any(g in q for g in greetings):
            if model_choice == "GPT-3.5 Turbo" and api_key:
                messages = [
                    {"role": "system", "content": "You are a friendly Fandom wiki assistant who can also chat casually."},
                    {"role": "user", "content": query}
                ]
                answer = openai_chat(messages, api_key)
                print_chat("ChatGPT", answer)
            else:
                print_chat("AI", "Hello! How can I help you with Fandom wikis today?")
            return
        if any(f in q for f in farewells):
            if model_choice == "GPT-3.5 Turbo" and api_key:
                messages = [
                    {"role": "system", "content": "You are a friendly Fandom wiki assistant who can also chat casually."},
                    {"role": "user", "content": query}
                ]
                answer = openai_chat(messages, api_key)
                print_chat("ChatGPT", answer)
            else:
                print_chat("AI", "Goodbye! If you have more Fandom questions, just ask.")
            return
        if any(t in q for t in thanks):
            if model_choice == "GPT-3.5 Turbo" and api_key:
                messages = [
                    {"role": "system", "content": "You are a friendly Fandom wiki assistant who can also chat casually."},
                    {"role": "user", "content": query}
                ]
                answer = openai_chat(messages, api_key)
                print_chat("ChatGPT", answer)
            else:
                print_chat("AI", "You're welcome! Let me know if you need anything else.")
            return
        # --- Fandom Q&A and search logic ---
        if model_choice == "GPT-3.5 Turbo" and api_key:
            # For full Fandom access, scan all pages for best match if needed
            if 'find' in q or 'page' in q:
                match = re.search(r'find (the )?(?P<term>.+?) page', query, re.IGNORECASE)
                if match:
                    search_term = match.group('term').strip()
                    print_chat("System", f"Searching all pages for '{search_term}'...")
                    try:
                        pages = get_all_fandom_pages(base_url)
                        best_url, best_text = None, None
                        best_score = 0
                        for page_url in pages:
                            try:
                                text = fetch_fandom_page(page_url)
                                if not text:
                                    continue
                                score = text.lower().count(search_term.lower())
                                if score > best_score:
                                    best_score = score
                                    best_url = page_url
                                    best_text = text[:2000]
                            except Exception:
                                continue
                        if best_url:
                            prompt = f"You are an expert on Fandom wikis. The user asked: '{query}'. Here is the best matching page content from {best_url}:\n{best_text}\nPlease answer the user's request as helpfully as possible."
                            messages = [
                                {"role": "system", "content": "You are a helpful assistant for Fandom wikis."},
                                {"role": "user", "content": prompt}
                            ]
                            answer = openai_chat(messages, api_key)
                            print_chat("ChatGPT", answer)
                        else:
                            print_chat("ChatGPT", "No relevant article found.")
                    except Exception as e:
                        print_chat("ChatGPT", f"[OpenAI error: {e}]")
                    return
            # For other queries, just fetch main page and send to GPT-3.5
            try:
                text = fetch_fandom_page(base_url)
                if not text:
                    print_chat("ChatGPT", "Failed to load the main page for this Fandom.")
                    return
                prompt = f"You are an expert on Fandom wikis. The user asked: '{query}'. Here is the main page content:\n{text[:2000]}\nPlease answer the user's request as helpfully as possible."
                messages = [
                    {"role": "system", "content": "You are a helpful assistant for Fandom wikis."},
                    {"role": "user", "content": prompt}
                ]
                answer = openai_chat(messages, api_key)
                print_chat("ChatGPT", answer)
            except Exception as e:
                print_chat("ChatGPT", f"[OpenAI error: {e}]")
            return
        elif model_choice == "Gemini Pro" and api_key:
            try:
                text = fetch_fandom_page(base_url)
                prompt = f"You are an expert on Fandom wikis. The user asked: '{query}'. Here is the main page content:\n{text[:2000]}\nPlease answer the user's request as helpfully as possible."
                messages = [
                    {"role": "user", "content": prompt}
                ]
                answer = gemini_chat(messages, api_key)
                print_chat("Gemini", answer)
            except Exception as e:
                print_chat("Gemini", f"[Gemini error: {e}]")
            return
        elif model_choice == "Claude 3" and api_key:
            try:
                text = fetch_fandom_page(base_url)
                prompt = f"You are an expert on Fandom wikis. The user asked: '{query}'. Here is the main page content:\n{text[:2000]}\nPlease answer the user's request as helpfully as possible."
                messages = [
                    {"role": "user", "content": prompt}
                ]
                answer = claude_chat(messages, api_key)
                print_chat("Claude", answer)
            except Exception as e:
                print_chat("Claude", f"[Claude error: {e}]")
            return

    # --- Page browser logic ---
    def load_page_list():
        set_loading("Loading Fandom pages...")
        page_listbox.delete(0, tk.END)
        try:
            pages = get_all_fandom_pages(get_fandom_url())
            for url in pages:
                title = url.split("/wiki/")[-1].replace("_", " ")
                page_listbox.insert(tk.END, f"{title}")
        except Exception as e:
            page_listbox.insert(tk.END, f"[Error loading pages: {e}]")
        set_loading("")

    def on_page_select(event=None):
        idx = page_listbox.curselection()
        if not idx:
            return
        title = page_listbox.get(idx[0])
        fandom_url = get_fandom_url()
        # Find the real URL
        parsed = urlparse(fandom_url)
        root_url = f"{parsed.scheme}://{parsed.netloc}"
        page_url = root_url + "/wiki/" + title.replace(" ", "_")
        set_loading(f"Loading page: {title} ...")
        try:
            text = fetch_fandom_page(page_url)
            if text:
                print_chat("[Page Loaded]", f"{title}\n{text[:1000]}...\n(Page loaded. You can now ask questions about this page.)")
            else:
                print_chat("[Error]", f"Could not load page: {title}")
        except Exception as e:
            print_chat("[Error]", f"Could not load page: {title} ({e})")
        set_loading("")

    page_listbox.bind('<<ListboxSelect>>', on_page_select)

    # --- Hotkey: Ctrl+I to focus chat ---
    def focus_chat(event=None):
        root.deiconify()
        root.lift()
        root.focus_force()
        chat_entry.focus_set()
        return "break"
    root.bind_all('<Control-i>', focus_chat)

    # --- Chat logic ---
    def on_enter(event=None):
        query = chat_entry.get().strip()
        if not query:
            return
        chat_entry.delete(0, tk.END)
        base_url = get_fandom_url()
        model_choice = model_var.get()
        if model_choice == "GPT-3.5 Turbo":
            api_key = openai_key_var.get().strip()
        elif model_choice == "Gemini Pro":
            api_key = gemini_key_var.get().strip()
        elif model_choice == "Claude 3":
            api_key = claude_key_var.get().strip()
        else:
            api_key = ""
        if not api_key:
            print_chat("System", "API key required. Please enter your key or buy access.")
            return
        set_loading("Thinking...")
        def run_query():
            try:
                handle_natural_language(query, base_url, model_choice, api_key)
            except Exception as e:
                print_chat("[Error]", str(e))
            set_loading("")
        threading.Thread(target=run_query).start()

    chat_entry.bind('<Return>', on_enter)
    tk.Button(main_frame, text="Send", command=on_enter, font=("Arial", 11, "bold")).pack(pady=5)
    tk.Button(main_frame, text="Load Fandom Pages", command=lambda: threading.Thread(target=load_page_list).start()).pack(pady=2)

    # Auto-load page list on fandom change
    def on_fandom_change(event=None):
        threading.Thread(target=load_page_list).start()
    fandom_menu.bind('<<ComboboxSelected>>', on_fandom_change)

    root.after(100, load_page_list)
    chat_entry.focus_set()
    root.mainloop()

if __name__ == "__main__":
    run_gui()
