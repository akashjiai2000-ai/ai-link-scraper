from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
import json

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return "MarkDocx-Level API Scraper is awake!"

@app.route('/scrape-link', methods=['POST'])
def scrape_link():
    data = request.get_json()
    url = data.get('url', '')

    if not url or ('chatgpt.com' not in url and 'gemini.google.com' not in url and 'g.co/gemini' not in url):
        return jsonify({"error": "Invalid URL."}), 400

    # Ultimate Browser Spoofing Headers to bypass standard Google bot-blocks
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1"
    }

    formatted_conversations = []

    try:
        # --- 1. CHATGPT HIDDEN API BYPASS ---
        if 'chatgpt.com' in url:
            # Extract the unique Share ID from the URL
            match = re.search(r'/share/([a-zA-Z0-9-]+)', url)
            if not match:
                return jsonify({"error": "Could not find ChatGPT Share ID in the link."}), 400
            
            share_id = match.group(1)
            
            # Hit the hidden backend API directly to bypass the HTML Cloudflare screen!
            api_url = f"https://chatgpt.com/backend-api/shared_conversations/{share_id}"
            
            res = requests.get(api_url, headers=headers, timeout=10)
            res.raise_for_status()
            
            # The API returns a perfect JSON dictionary
            json_data = res.json()
            mapping = json_data.get('mapping', {})
            
            current_prompt = "AI Response"
            
            # Loop through all messages in the conversation
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

        # --- 2. GEMINI DEEP REGEX BYPASS ---
        elif 'gemini.google.com' in url or 'g.co/gemini' in url:
            res = requests.get(url, headers=headers, timeout=10)
            res.raise_for_status()
            html = res.text
            
            # Grab all massive strings hidden in Google's JavaScript arrays
            strings = re.findall(r'"((?:\\.|[^"\\])*)"', html)
            
            current_prompt = "Gemini Response"
            for s in strings:
                try:
                    clean_s = json.loads('"' + s + '"')
                except:
                    clean_s = s.replace('\\n', '\n').replace('\\"', '"')
                    
                # Look for long Markdown structures (AI Responses)
                if len(clean_s) > 100 and '\n\n' in clean_s and ('**' in clean_s or '*' in clean_s or '`' in clean_s):
                    formatted_conversations.append({
                        "snippet": f"✨ {current_prompt}",
                        "text": clean_s
                    })
                    current_prompt = "Gemini Response" 
                # Look for shorter strings without code (User Prompts)
                elif 5 < len(clean_s) < 200 and '{' not in clean_s and '[' not in clean_s:
                    if '\\u' not in s and '_' not in clean_s: 
                        current_prompt = clean_s[:60].replace('\n', ' ') + "..."

        # If it STILL failed, tell us exactly what error code the server threw
        if not formatted_conversations:
            return jsonify({"error": f"Bot protection blocked the request. Try exporting to Word directly from the AI."}), 403

        # Prepare for the Blogger checkboxes
        for i, conv in enumerate(formatted_conversations):
            conv["id"] = i

        return jsonify({"conversations": formatted_conversations})

    except Exception as e:
        print("Scraping error:", str(e))
        return jsonify({"error": f"API Error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
