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

    formatted_conversations = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True, 
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
            )
            
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            # Load the shell of the page quickly
            page.goto(url, wait_until='domcontentloaded', timeout=30000)
            
            # --- CHATGPT EXTRACTION ---
            if 'chatgpt.com' in page.url:
                # SMART WAIT: Wait exactly for the chat elements to render (Max 15 seconds)
                try:
                    page.wait_for_selector('[data-message-author-role]', timeout=15000)
                except:
                    pass # If it times out, we'll still try to parse whatever is on the screen
                
                soup = BeautifulSoup(page.content(), 'html.parser')
                
                # Find all messages (both user questions and AI answers)
                chat_turns = soup.find_all(attrs={"data-message-author-role": True})
                
                current_user_prompt = "AI Response"
                
                for turn in chat_turns:
                    role = turn.get('data-message-author-role')
                    if role == 'user':
                        # Save the user's question to use as the checklist title!
                        current_user_prompt = turn.get_text(separator=' ').strip()[:60] + "..."
                    elif role == 'assistant':
                        text = turn.get_text(separator='\n').strip()
                        if text:
                            formatted_conversations.append({
                                "snippet": f"👤 {current_user_prompt}",
                                "text": text
                            })
                            current_user_prompt = "AI Response" # Reset for the next one
                
                # Backup plan if ChatGPT changes their code
                if not formatted_conversations:
                    elements = soup.find_all('div', class_=re.compile(r'markdown|prose'))
                    for el in elements:
                        text = el.get_text(separator='\n').strip()
                        if text:
                            formatted_conversations.append({
                                "snippet": text[:60].replace('\n', ' ') + "...",
                                "text": text
                            })

            # --- GEMINI EXTRACTION ---
            elif 'gemini.google.com' in page.url or 'g.co/gemini' in page.url:
                # SMART WAIT: Wait for Gemini's text box to appear
                try:
                    page.wait_for_selector('message-content, [class*="model-response"]', timeout=15000)
                except:
                    pass
                
                soup = BeautifulSoup(page.content(), 'html.parser')
                elements = soup.find_all(['message-content', 'div'], class_=re.compile(r'model-response-text|response-container|message-content'))
                
                for el in elements:
                    text = el.get_text(separator='\n').strip()
                    if text: 
                        formatted_conversations.append({
                            "snippet": text[:60].replace('\n', ' ') + "...",
                            "text": text
                        })

            browser.close()

        if not formatted_conversations:
            page_title = soup.title.string if soup.title else "Unknown Page"
            if "Just a moment" in page_title:
                return jsonify({"error": "ChatGPT security blocked the server. Try a different link."}), 403
            return jsonify({"error": f"Could not find text. Page title seen: '{page_title}'"}), 404

        # Send the neatly packaged User/AI snippets to the frontend
        for i, conv in enumerate(formatted_conversations):
            conv["id"] = i

        return jsonify({"conversations": formatted_conversations})

    except Exception as e:
        print("Scraping error:", str(e))
        return jsonify({"error": f"Browser Error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
