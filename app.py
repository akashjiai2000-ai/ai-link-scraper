from flask import Flask, request, jsonify
from flask_cors import CORS
from curl_cffi import requests  # <-- THIS IS THE SECRET WEAPON
from bs4 import BeautifulSoup
import re
import json

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return "Stealth API Scraper is awake!"

@app.route('/scrape-link', methods=['POST'])
def scrape_link():
    data = request.get_json()
    url = data.get('url', '')

    if not url or ('chatgpt.com' not in url and 'gemini.google.com' not in url and 'g.co/gemini' not in url):
        return jsonify({"error": "Invalid URL."}), 400

    formatted_conversations = []

    try:
        # --- 1. CHATGPT HIDDEN API + TLS IMPERSONATION ---
        if 'chatgpt.com' in url:
            match = re.search(r'/share/([a-zA-Z0-9-]+)', url)
            if not match:
                return jsonify({"error": "Could not find ChatGPT Share ID in the link."}), 400
            
            share_id = match.group(1)
            api_url = f"https://chatgpt.com/backend-api/shared_conversations/{share_id}"
            
            # The 'impersonate' flag perfectly fakes a real Google Chrome browser fingerprint!
            res = requests.get(api_url, impersonate="chrome110", timeout=15)
            res.raise_for_status()
            
            json_data = res.json()
            mapping = json_data.get('mapping', {})
            
            current_prompt = "AI Response"
            
            for node in mapping.values():
                message = node.get('message')
                if not message: continue
                
                author_role = message.get('author', {}).get('role')
                parts = message.get('content', {}).get('parts', [])
                
                if not parts or not isinstance(parts[0], str): continue
                text = parts[0].strip()
                if not text: continue
                
                if author_role == 'user':
                    current_prompt = text[:60].replace('\n', ' ') + "..."
                elif author_role == 'assistant':
                    formatted_conversations.append({
                        "snippet": f"👤 {current_prompt}",
                        "text": text
                    })
                    current_prompt = "AI Response"

        # --- 2. GEMINI DEEP REGEX + TLS IMPERSONATION ---
        elif 'gemini.google.com' in url or 'g.co/gemini' in url:
            # We use impersonation here too just to be safe from Google's bot checks
            res = requests.get(url, impersonate="chrome110", timeout=15)
            res.raise_for_status()
            html = res.text
            
            strings = re.findall(r'"((?:\\.|[^"\\])*)"', html)
            
            current_prompt = "Gemini Response"
            for s in strings:
                try:
                    clean_s = json.loads('"' + s + '"')
                except:
                    clean_s = s.replace('\\n', '\n').replace('\\"', '"')
                    
                if len(clean_s) > 100 and '\n\n' in clean_s and ('**' in clean_s or '*' in clean_s or '`' in clean_s):
                    formatted_conversations.append({
                        "snippet": f"✨ {current_prompt}",
                        "text": clean_s
                    })
                    current_prompt = "Gemini Response" 
                elif 5 < len(clean_s) < 200 and '{' not in clean_s and '[' not in clean_s:
                    if '\\u' not in s and '_' not in clean_s: 
                        current_prompt = clean_s[:60].replace('\n', ' ') + "..."

        if not formatted_conversations:
            return jsonify({"error": f"Bot protection blocked the request. Try exporting to Word directly from the AI."}), 403

        for i, conv in enumerate(formatted_conversations):
            conv["id"] = i

        return jsonify({"conversations": formatted_conversations})

    except Exception as e:
        print("Scraping error:", str(e))
        return jsonify({"error": f"API Error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
                
