from flask import Flask, request, jsonify
from flask_cors import CORS
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re
import json

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return "Invisible Browser Scraper is awake!"

@app.route('/scrape-link', methods=['POST'])
def scrape_link():
    data = request.get_json()
    url = data.get('url')

    if not url or ('chatgpt.com' not in url and 'gemini.google.com' not in url and 'g.co/gemini' not in url):
        return jsonify({"error": "Invalid URL. Please paste a ChatGPT or Gemini shared link."}), 400

    raw_conversations = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True, 
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
            )
            
            # Disguise the invisible browser as a real Google Chrome user
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            # FIX 1: Don't wait for background trackers, just wait for the core page! Max wait: 35 seconds.
            page.goto(url, wait_until='domcontentloaded', timeout=35000)
            
            # FIX 2: Wait exactly 3 seconds for the React/JS to draw the text on the screen
            page.wait_for_timeout(3000)

            html_content = page.content()
            soup = BeautifulSoup(html_content, 'html.parser')

            # --- CHATGPT EXTRACTION ---
            if 'chatgpt.com' in page.url:
                elements = soup.find_all('div', class_=re.compile(r'prose|markdown'))
                for el in elements:
                    text = el.get_text(separator='\n').strip()
                    if text: raw_conversations.append(text)
                
                # Backup Plan: Look in the hidden JSON code if the text didn't draw in time
                if not raw_conversations:
                    script = soup.find('script', id='__NEXT_DATA__')
                    if script:
                        try:
                            json_data = json.loads(script.string)
                            def find_parts(obj):
                                if isinstance(obj, dict):
                                    for k, v in obj.items():
                                        if k == 'parts' and isinstance(v, list) and len(v) > 0 and isinstance(v[0], str):
                                            raw_conversations.append(v[0])
                                        else:
                                            find_parts(v)
                                elif isinstance(obj, list):
                                    for item in obj:
                                        find_parts(item)
                            find_parts(json_data)
                        except: pass

            # --- GEMINI EXTRACTION ---
            elif 'gemini.google.com' in page.url:
                elements = soup.find_all(['message-content', 'div'], class_=re.compile(r'model-response-text|response-container|message-content'))
                for el in elements:
                    text = el.get_text(separator='\n').strip()
                    if text: raw_conversations.append(text)

            browser.close()

        if not raw_conversations:
            # FIX 3: If it fails, tell us exactly what page title the browser is looking at!
            page_title = soup.title.string if soup.title else "Unknown Page"
            if "Just a moment" in page_title:
                return jsonify({"error": "ChatGPT security blocked the server. Please try a Gemini link."}), 403
            return jsonify({"error": f"Could not find text. Page title seen: '{page_title}'"}), 404

        # Format the data into snippets for Checkboxes
        formatted_data = []
        for i, text in enumerate(raw_conversations):
            snippet = text[:80].replace('\n', ' ') + ("..." if len(text) > 80 else "")
            formatted_data.append({"id": i, "snippet": snippet, "text": text})

        return jsonify({"conversations": formatted_data})

    except Exception as e:
        print("Scraping error:", str(e))
        return jsonify({"error": f"Browser Error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
