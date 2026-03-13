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
    return "Lightning Fast API Scraper is awake!"

@app.route('/scrape-link', methods=['POST'])
def scrape_link():
    data = request.get_json()
    url = data.get('url')

    if not url or ('chatgpt.com' not in url and 'gemini.google.com' not in url and 'g.co/gemini' not in url):
        return jsonify({"error": "Invalid URL."}), 400

    # Disguise our instant request as a normal browser
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }

    try:
        # Fetch the raw HTML instantly (takes ~0.5 seconds)
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        html = res.text
        final_url = res.url
        
        formatted_conversations = []

        # --- CHATGPT FAST JSON PARSER ---
        if 'chatgpt.com' in final_url:
            soup = BeautifulSoup(html, 'html.parser')
            # ChatGPT stores the entire conversation in a hidden JSON script tag
            script = soup.find('script', id='__NEXT_DATA__')
            if script:
                try:
                    data = json.loads(script.string)
                    messages = []
                    
                    # Algorithm to deep-search the JSON tree for messages
                    def find_messages(obj):
                        if isinstance(obj, dict):
                            if 'message' in obj and isinstance(obj['message'], dict) and 'author' in obj['message']:
                                messages.append(obj['message'])
                            for k, v in obj.items():
                                find_messages(v)
                        elif isinstance(obj, list):
                            for item in obj:
                                find_messages(item)
                    
                    find_messages(data)
                    
                    current_prompt = "AI Response"
                    for msg in messages:
                        role = msg.get('author', {}).get('role')
                        parts = msg.get('content', {}).get('parts', [])
                        if not parts or not isinstance(parts[0], str): continue
                        
                        text = parts[0].strip()
                        if not text: continue
                        
                        # Match user prompts to AI responses
                        if role == 'user':
                            current_prompt = text[:60].replace('\n', ' ') + "..."
                        elif role == 'assistant':
                            formatted_conversations.append({
                                "snippet": f"👤 {current_prompt}",
                                "text": text
                            })
                            current_prompt = "AI Response"
                except Exception as e:
                    print("JSON parse error:", e)
            
            # Fast Fallback if JSON fails
            if not formatted_conversations:
                for el in soup.find_all('div', class_=re.compile(r'markdown|prose')):
                    text = el.get_text(separator='\n').strip()
                    if text:
                        formatted_conversations.append({
                            "snippet": text[:60].replace('\n', ' ') + "...",
                            "text": text
                        })

        # --- GEMINI FAST REGEX PARSER ---
        elif 'gemini.google.com' in final_url or 'g.co/gemini' in final_url:
            # Gemini hides text inside massive nested arrays. We rip out all strings.
            strings = re.findall(r'"((?:\\.|[^"\\])*)"', html)
            
            current_prompt = "Gemini Response"
            for s in strings:
                try:
                    clean_s = json.loads('"' + s + '"')
                except:
                    clean_s = s.replace('\\n', '\n').replace('\\"', '"')
                    
                # Heuristic: AI responses are long and usually contain double newlines or markdown
                if len(clean_s) > 100 and '\n\n' in clean_s and ('**' in clean_s or '*' in clean_s or '`' in clean_s):
                    formatted_conversations.append({
                        "snippet": f"✨ {current_prompt}",
                        "text": clean_s
                    })
                    current_prompt = "Gemini Response" 
                # Heuristic: User prompts are shorter and don't look like code
                elif 5 < len(clean_s) < 200 and '{' not in clean_s and '[' not in clean_s:
                    if '\\u' not in s and '_' not in clean_s: 
                        current_prompt = clean_s[:60].replace('\n', ' ') + "..."

        if not formatted_conversations:
            return jsonify({"error": "Format changed or AI blocked the request. Try another link."}), 404

        # Prepare for the Blogger checkboxes
        for i, conv in enumerate(formatted_conversations):
            conv["id"] = i

        return jsonify({"conversations": formatted_conversations})

    except Exception as e:
        print("Scraping error:", str(e))
        return jsonify({"error": f"API Error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
