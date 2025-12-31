import requests
import datetime
import time
import os
import google.generativeai as genai
import markdown
from html2image import Html2Image
from PIL import Image  

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
NEWSLETTER_ROLE_ID = os.getenv("NEWSLETTER_ROLE_ID")
SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY")

SUBREDDIT = "vitap"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://www.google.com/',
    'Connection': 'keep-alive'
}
IMAGE_FILENAME = "vitap_daily_news.png"

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash') 

NEWSPAPER_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=UnifrakturMaguntia&family=Playfair+Display:wght@700;900&family=Lora:ital,wght@0,400;0,600;1,400&family=Oswald:wght@500&display=swap');

    body {
        font-family: 'Lora', serif;
        margin: 0;
        padding: 0;
        background-color: transparent; 
    }

    .container {
        display: inline-block; 
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        width: 800px;
        padding: 40px 50px;
        color: #f4f1ea;
        
        margin: 20px; 
        box-shadow: 0 0 40px rgba(255, 215, 0, 0.4), 0 0 60px rgba(255, 105, 180, 0.2);
        
        background-image: 
            radial-gradient(circle at 20% 30%, rgba(255, 215, 0, 0.1) 0%, transparent 50%),
            radial-gradient(circle at 80% 70%, rgba(255, 105, 180, 0.1) 0%, transparent 50%),
            radial-gradient(circle at 50% 50%, rgba(173, 216, 230, 0.05) 0%, transparent 50%);
        position: relative;
        overflow: hidden;
    }

    .container::before {
        content: "⭐ ✨ 🎊 🎉 ⭐ ✨ 🎊 🎉 ⭐ ✨ 🎊 🎉 ⭐ ✨ 🎊 🎉";
        position: absolute;
        top: 10px;
        left: 0;
        right: 0;
        text-align: center;
        font-size: 20px;
        opacity: 0.6;
        animation: sparkle 3s infinite;
    }

    .container::after {
        content: "🎆 🎇 🎆 🎇 🎆 🎇 🎆 🎇 🎆 🎇 🎆 🎇 🎆 🎇 🎆 🎇";
        position: absolute;
        bottom: 10px;
        left: 0;
        right: 0;
        text-align: center;
        font-size: 20px;
        opacity: 0.6;
        animation: sparkle 3s infinite 1.5s;
    }

    @keyframes sparkle {
        0%, 100% { opacity: 0.4; transform: scale(1); }
        50% { opacity: 0.8; transform: scale(1.05); }
    }

    h1 {
        font-family: 'Playfair Display', serif;
        font-size: 70px;
        text-align: center;
        margin: 40px 0 10px 0;
        background: linear-gradient(45deg, #ffd700, #ff69b4, #87ceeb, #ffd700);
        background-size: 300% 300%;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        line-height: 0.9;
        border-bottom: 4px double #ffd700;
        padding-bottom: 20px;
        text-shadow: 0 0 20px rgba(255, 215, 0, 0.5);
        animation: gradient-shift 4s ease infinite;
    }

    @keyframes gradient-shift {
        0%, 100% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
    }

    .special-banner {
        text-align: center;
        font-family: 'Playfair Display', serif;
        font-size: 28px;
        font-weight: 900;
        color: #ffd700;
        text-transform: uppercase;
        margin: 15px 0 20px 0;
        letter-spacing: 4px;
        text-shadow: 0 0 10px rgba(255, 215, 0, 0.8), 0 0 20px rgba(255, 105, 180, 0.6);
    }

    .date-line {
        text-align: center;
        font-family: 'Oswald', sans-serif;
        font-size: 13px;
        text-transform: uppercase;
        border-bottom: 2px solid #ffd700;
        margin-bottom: 30px;
        padding-bottom: 8px;
        letter-spacing: 3px;
        font-weight: bold;
        color: #87ceeb;
    }

    .columns {
        column-count: 2;
        column-gap: 40px;
        column-rule: 2px solid rgba(255, 215, 0, 0.3);
        text-align: justify;
    }

    h2 {
        font-family: 'Playfair Display', serif;
        font-size: 24px;
        font-weight: 900;
        text-transform: uppercase;
        color: #ffd700;
        margin-top: 0;
        margin-bottom: 10px;
        line-height: 1;
        break-after: avoid;
        text-shadow: 0 0 10px rgba(255, 215, 0, 0.4);
    }
    
    h2:not(:first-child) {
        margin-top: 30px;
        border-top: 2px solid #ffd700;
        padding-top: 15px;
    }

    p { 
        font-size: 15px; 
        line-height: 1.5; 
        margin-bottom: 15px; 
        color: #f4f1ea; 
    }
    
    ul { padding-left: 20px; margin-top: 0; }
    
    li { 
        font-size: 15px; 
        margin-bottom: 8px; 
        line-height: 1.4; 
        color: #f4f1ea;
    }
    
    li strong { 
        font-family: 'Oswald', sans-serif; 
        text-transform: uppercase; 
        color: #87ceeb; 
    }

    blockquote {
        border-left: 4px solid #ffd700;
        background: rgba(255, 215, 0, 0.1);
        margin: 20px 0;
        padding: 10px 15px;
        font-style: italic;
        font-family: 'Playfair Display', serif;
        font-weight: 700;
        font-size: 16px;
        break-inside: avoid;
        color: #87ceeb;
        box-shadow: 0 0 15px rgba(255, 215, 0, 0.2);
    }

    .footer {
        text-align: center;
        font-family: 'Oswald', sans-serif;
        font-size: 10px;
        margin-top: 30px;
        border-top: 1px solid #ffd700;
        padding-top: 10px;
        width: 100%;
        color: #87ceeb;
    }
</style>
"""

def get_json(url):
    try:
        resp = requests.get(url, headers=HEADERS)
        if resp.status_code == 200: return resp.json()
    except: return None

def fetch_stories():
    max_attempts = 3
    url = f"https://api.scraperapi.com/?api_key={SCRAPER_API_KEY}&url=https://reddit.com/r/{SUBREDDIT}/top.json?t=day&limit=12"
    
    for attempt in range(max_attempts):
        print(f"🕵️  Gathering intel from r/{SUBREDDIT}... (Attempt {attempt + 1}/{max_attempts})")
        data = get_json(url)
        
        if data and 'data' in data and 'children' in data['data']:
            stories = []
            for post in data['data']['children']:
                p = post['data']
                story_blob = f"---\nTITLE: {p.get('title')}\nAUTHOR: u/{p.get('author')}\nUPVOTES: {p.get('score')}\nBODY TEXT: {p.get('selftext', '')[:400]}\n"
                
                comment_url = "https://reddit.com" + p.get("permalink") + ".json?sort=top"
                proxy_url = f"https://api.scraperapi.com/?api_key={SCRAPER_API_KEY}&url={comment_url}"
                c_data = get_json(proxy_url)

                if c_data and len(c_data) > 1 and 'data' in c_data[1] and 'children' in c_data[1]['data']:
                    c_list = c_data[1]['data']['children']
                    comments_text = []
                    for c in c_list[:2]:
                        if 'data' in c and 'body' in c['data'] and c['data']['body'] != "[deleted]":
                            comments_text.append(f"- {c['data']['author']}: {c['data']['body'][:120]}")
                    if comments_text:
                        story_blob += "TOP COMMENTS:\n" + "\n".join(comments_text)
                
                stories.append(story_blob)
                time.sleep(0.5)
            
            if stories:
                return stories
            else:
                print(f"⚠️  No posts found in the last 24 hours.")
        
        if attempt < max_attempts - 1:
            print(f"⚠️  Failed to fetch data. Retrying in 2 seconds...")
            time.sleep(2)
    
    print("❌ Failed to fetch data after 3 attempts.")
    return []


def generate_newsletter_content(raw_stories):
    print("🧠 AI Editor is writing the newspaper...")
    today = datetime.date.today().strftime("%A, %B %d, %Y")
    
    prompt = f"""
You are the Chief Editor of "VIT AP NEWS".

Today's Date: {today}

RAW DATA FROM r/vitap:
{ "".join(raw_stories) }

============================
STRICT EDITORIAL RULES:
============================

1. OUTPUT **ONLY VALID MARKDOWN**.
2. DO NOT add extra sections.
3. DO NOT change the headings.
4. DO NOT rename any section titles.
5. DO NOT reorder sections.
6. DO NOT add emojis.
7. DO NOT include explanations or notes.
8. DO NOT include HTML.
9. FOLLOW the format EXACTLY as shown below.
10. DO NOT MENTION r/vitap

============================
EDITORIAL TONE:
============================

- Voice: newspaper editor who is secretly Gen Z.
- Headlines: sometimes funny, dramatic, serious, UPPERCASE.
- Body text: formal newspaper language with light Gen Z phrasing (e.g., "cooked", "locked in", "real", "skill issue", "aura", "fr").
- Brainrot level: LOW to MEDIUM. Two to three casual terms per section maximum.
- Humor should feel accidental, not meme-heavy.

============================
CONTENT RULES:
============================

- Each story: MAXIMUM 3 sentences.
- Campus briefs: one sentence per bullet.
- Student quote: must be realistic and taken from provided data.
- Weather report: metaphorical, mood-based, no real weather.
- Write clean, readable, newspaper-grade English.

============================
REQUIRED OUTPUT FORMAT:
============================

## HEADLINE OF THE DAY (DRAMATIC & UPPERCASE)
(Write a 2–3 sentence summary of the biggest story using formal tone mixed with VERY LIGHT Gen Z phrasing.)

## CAMPUS BRIEFS
* **(STORY TITLE):** (One sentence summary).
* **(STORY TITLE):** (One sentence summary).

## STUDENT VOICES
(Pick one funny or relatable comment from the data.)
> "(Quote here)" — A student suffering from skill issue

## WEATHER REPORT
(Weather forecast based on subreddit mood, written like a newspaper report. Justify the reason with)
"""

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e: return f"AI Error: {e}"

def generate_image_from_markdown(md_text):
    print("🎨 Setting type and printing image...")
    today = datetime.date.today().strftime("%A, %B %d, %Y")

    html_content = markdown.markdown(md_text, extensions=['extra'])
    
    full_html_str = f"""
    <html>
    <head>{NEWSPAPER_CSS}</head>
    <body>
        <div class="container" id="newspaper">
            <h1>VIT AP NEWS</h1>
            <div class="special-banner">🎊 New Year's Eve Special 🎊</div>
            <div class="date-line">VOL. IV • {today} • 2025 COUNTDOWN EDITION</div>
            
            <div class="columns">
                {html_content}
            </div>

        </div>
    </body>
    </html>
    """
    
    hti = Html2Image()
    hti.browser.flags = [
        '--hide-scrollbars', 
        '--force-device-scale-factor=1', 
        '--default-background-color=00000000',
        '--no-sandbox', 
        '--headless'
    ]
    
    temp_filename = "temp_screenshot.png"
    hti.screenshot(
        html_str=full_html_str,
        save_as=temp_filename,
        size=(1000, 3000) 
    )

    try:
        print("✂️  Trimming extra space...")
        img = Image.open(temp_filename)
        bbox = img.getbbox() 
        
        if bbox:
            cropped_img = img.crop(bbox)
            cropped_img.save(IMAGE_FILENAME)
            print(f"✨ Hot off the press! Saved to {IMAGE_FILENAME}")
        else:
            print("⚠️ Warning: Image was empty, saving original.")
            img.save(IMAGE_FILENAME)
            
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
            
    except Exception as e:
        print(f"⚠️ Image processing error: {e}")
        
def send_image_to_discord():
    print("🚀 Publishing Image to Discord...")
    if not os.path.exists(IMAGE_FILENAME):
        print("❌ Error: Image file not found.")
        return

    with open(IMAGE_FILENAME, "rb") as f:
        response = requests.post(
            DISCORD_WEBHOOK_URL,
            data={"content": f"<@&{NEWSLETTER_ROLE_ID}>"},
            files={"file": (IMAGE_FILENAME, f)}
        )

    if response.status_code in [200, 204]:
        print("✅ Newsletter Delivered Successfully!")
    else:
        print(f"❌ Delivery Failed: {response.status_code} - {response.text}")

if __name__ == "__main__":
    raw_data = fetch_stories()
    
    if raw_data:
        ai_text = generate_newsletter_content(raw_data)
        generate_image_from_markdown(ai_text)
        send_image_to_discord()
    else:
        print("No news today.")
