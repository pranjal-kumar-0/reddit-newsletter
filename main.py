import requests
import datetime
import time
import os
import google.generativeai as genai
import markdown
from html2image import Html2Image
from PIL import Image
from dotenv import load_dotenv
load_dotenv()

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
        /* We make the body transparent so we can crop easily later */
        background-color: transparent; 
    }

    .container {
        display: inline-block; 
        background-color: #f4f1ea;
        width: 800px;
        padding: 40px 50px;
        color: #111;
        
        /* Margin ensures the shadow isn't cut off */
        margin: 20px; 
        box-shadow: 0 0 30px rgba(0,0,0,0.3);
        
        background-image: linear-gradient(0deg, transparent 24%, rgba(0, 0, 0, .02) 25%, rgba(0, 0, 0, .02) 26%, transparent 27%, transparent 74%, rgba(0, 0, 0, .02) 75%, rgba(0, 0, 0, .02) 76%, transparent 77%, transparent), linear-gradient(90deg, transparent 24%, rgba(0, 0, 0, .02) 25%, rgba(0, 0, 0, .02) 26%, transparent 27%, transparent 74%, rgba(0, 0, 0, .02) 75%, rgba(0, 0, 0, .02) 76%, transparent 77%, transparent);
        background-size: 50px 50px;
    }

    h1 {
        font-family: 'Playfair Display', serif;
        font-size: 80px;
        text-align: center;
        margin: 10px 0;
        color: #111;
        line-height: 0.8;
        border-bottom: 4px double #111;
        padding-bottom: 25px;
        text-shadow: 2px 2px 0px rgba(0,0,0,0.1);
    }

    .date-line {
        text-align: center;
        font-family: 'Oswald', sans-serif;
        font-size: 13px;
        text-transform: uppercase;
        border-bottom: 1px solid #333;
        margin-bottom: 30px;
        padding-bottom: 8px;
        letter-spacing: 3px;
        font-weight: bold;
    }

    .columns {
        column-count: 2;
        column-gap: 40px;
        column-rule: 1px solid #ccc;
        text-align: justify;
    }

    h2 {
        font-family: 'Playfair Display', serif;
        font-size: 24px;
        font-weight: 900;
        text-transform: uppercase;
        color: #111;
        margin-top: 0;
        margin-bottom: 10px;
        line-height: 1;
        break-after: avoid;
    }
    
    h2:not(:first-child) {
        margin-top: 30px;
        border-top: 2px solid #111;
        padding-top: 15px;
    }

    p { font-size: 15px; line-height: 1.5; margin-bottom: 15px; color: #222; }
    ul { padding-left: 20px; margin-top: 0; }
    li { font-size: 15px; margin-bottom: 8px; line-height: 1.4; }
    li strong { font-family: 'Oswald', sans-serif; text-transform: uppercase; color: #444; }

    blockquote {
        border-left: 4px solid #111;
        background: #e8e4db;
        margin: 20px 0;
        padding: 10px 15px;
        font-style: italic;
        font-family: 'Playfair Display', serif;
        font-weight: 700;
        font-size: 16px;
        break-inside: avoid;
    }

    .footer {
        text-align: center;
        font-family: 'Oswald', sans-serif;
        font-size: 10px;
        margin-top: 30px;
        border-top: 1px solid #111;
        padding-top: 10px;
        width: 100%;
        color: #666;
    }
</style>
"""

def get_json(url):
    try:
        resp = requests.get(url, headers=HEADERS)
        if resp.status_code == 200: return resp.json()
    except: return None

def fetch_stories():
    from bs4 import BeautifulSoup

    print(f"🕵️  Gathering intel from r/{SUBREDDIT} via old.reddit.com...")

    base_url = f"https://old.reddit.com/r/{SUBREDDIT}/"
    stories = []

    try:
        resp = requests.get(base_url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            print("❌ Failed to load subreddit page.")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        posts = soup.find_all("div", class_="thing", limit=10)

        for post in posts:
            title_tag = post.find("a", class_="title")
            author = post.get("data-author", "unknown")
            score = post.get("data-score", "0")
            permalink = post.get("data-permalink")

            if not title_tag or not permalink:
                continue

            title = title_tag.text.strip()

            story_blob = (
                f"---\n"
                f"TITLE: {title}\n"
                f"AUTHOR: u/{author}\n"
                f"UPVOTES: {score}\n"
                f"BODY TEXT:\n"
            )

            comment_url = "https://old.reddit.com" + permalink

            try:
                c_resp = requests.get(comment_url, headers=HEADERS, timeout=10)
                if c_resp.status_code == 200:
                    c_soup = BeautifulSoup(c_resp.text, "html.parser")

                    comments = c_soup.find_all("div", class_="comment")
                    comments_text = []

                    for c in comments:
                        author_c = c.get("data-author")
                        body = c.find("div", class_="md")

                        if not author_c or not body:
                            continue

                        text = body.get_text(" ", strip=True)
                        if text and text != "[deleted]":
                            comments_text.append(
                                f"- {author_c}: {text[:200]}"
                            )

                    if comments_text:
                        story_blob += "TOP COMMENTS:\n" + "\n".join(comments_text)

            except Exception:
                pass

            stories.append(story_blob)
            time.sleep(1)  # polite scraping

        return stories

    except Exception as e:
        print(f"❌ Scraping error: {e}")
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
            <div class="date-line">VOL. IV • {today} • PRICE: YOUR SANITY</div>
            
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