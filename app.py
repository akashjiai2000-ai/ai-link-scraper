from flask import Flask, request, jsonify
from flask_cors import CORS
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re

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
            page = browser.new_page()
            page.goto(url, wait_until='networkidle', timeout=20000)

            html_content = page.content()
            soup = BeautifulSoup(html_content, 'html.parser')

            # --- CHATGPT EXTRACTION ---
            if 'chatgpt.com' in page.url:
                elements = soup.find_all('div', class_=re.compile(r'prose|markdown'))
                for el in elements:
                    text = el.get_text(separator='\n').strip()
                    if text: raw_conversations.append(text)

            # --- GEMINI EXTRACTION ---
            elif 'gemini.google.com' in page.url:
                elements = soup.find_all(['message-content', 'div'], class_=re.compile(r'model-response-text|response-container|message-content'))
                for el in elements:
                    text = el.get_text(separator='\n').strip()
                    if text: raw_conversations.append(text)

            browser.close()

        if not raw_conversations:
            return jsonify({"error": "Could not find AI text. The page might have taken too long to load."}), 404

        # Format the data into snippets for the Frontend Checkboxes!
        formatted_data = []
        for i, text in enumerate(raw_conversations):
            # Create a short preview (first 80 characters)
            snippet = text[:80].replace('\n', ' ') + ("..." if len(text) > 80 else "")
            formatted_data.append({"id": i, "snippet": snippet, "text": text})

        return jsonify({"conversations": formatted_data})

    except Exception as e:
        print("Scraping error:", str(e))
        return jsonify({"error": "Failed to load the page in the virtual browser."}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
