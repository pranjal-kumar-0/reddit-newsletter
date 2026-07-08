import requests
import datetime
import time
import os
from dotenv import load_dotenv
import io
import google.generativeai as genai
import markdown
from bs4 import BeautifulSoup
from html2image import Html2Image
from PIL import Image

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
NEWSLETTER_ROLE_ID = os.getenv("NEWSLETTER_ROLE_ID")

print(GEMINI_API_KEY)
print(DISCORD_WEBHOOK_URL)
print(NEWSLETTER_ROLE_ID)



SUBREDDIT = "vitap"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Connection': 'keep-alive'
}
IMAGE_FILENAME = "vitap_daily_news.png"

genai.configure(api_key=GEMINI_API_KEY)
# Using Gemini 2.5 Flash which natively supports multimodal (text + images)
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
        background-color: #f4f1ea;
        width: 800px;
        padding: 40px 50px;
        color: #111;
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

def fetch_stories():
    url = f"https://old.reddit.com/r/{SUBREDDIT}/top/"
    print(f"🕵️  Gathering intel from {url}...")
    
    try:
        resp = requests.get(url, headers=HEADERS)
        resp.raise_for_status()
    except Exception as e:
        print(f"❌ Failed to fetch front page: {e}")
        return [], []

    soup = BeautifulSoup(resp.text, 'html.parser')
    # Filter for standard posts (ignore ads/promoted)
    posts = [p for p in soup.select('#siteTable .thing') if 'promoted' not in p.get('class', [])][:10]
    
    if not posts:
        print("⚠️ No posts found on the page.")
        return [], []

    stories = []
    downloaded_images = []

    for idx, post in enumerate(posts, 1):
        # Extract basic post info
        title_elem = post.select_one('p.title a.title')
        title = title_elem.text.strip() if title_elem else "No Title"
        
        author_elem = post.select_one('a.author')
        author = author_elem.text.strip() if author_elem else "Unknown"
        
        score_elem = post.select_one('.score.unvoted')
        score = score_elem.text.strip() if score_elem else "0"
        
        comments_elem = post.select_one('a.comments')
        comments_url = comments_elem['href'] if comments_elem else None
        
        # Check for image URL
        data_url = post.get('data-url', '')
        img_url = data_url if data_url.endswith(('.jpg', '.png', '.jpeg', '.gif', '.webp')) else None

        body_text = ""
        comments_text = []

        # Scrape Comments Page
        if comments_url:
            if not comments_url.startswith('http'):
                comments_url = "https://old.reddit.com" + comments_url
                
            time.sleep(1) # Be nice to Reddit's servers
            try:
                c_resp = requests.get(comments_url, headers=HEADERS)
                c_soup = BeautifulSoup(c_resp.text, 'html.parser')
                
                # Extract main post text if exists
                expando = c_soup.select_one('.expando .usertext-body .md')
                if expando:
                    body_text = expando.text.strip()[:400]
                
                # Extract top 2 comments
                comments_list = c_soup.select('.commentarea .thing.comment')[:2]
                for c in comments_list:
                    c_author_elem = c.select_one('a.author')
                    c_author = c_author_elem.text.strip() if c_author_elem else "Unknown"
                    
                    c_body_elem = c.select_one('.usertext-body .md')
                    c_body = c_body_elem.text.strip() if c_body_elem else ""
                    
                    if c_body and c_body != "[deleted]":
                        comments_text.append(f"- {c_author}: {c_body[:120]}")
            except Exception as e:
                print(f"⚠️ Failed to parse comments for {title[:20]}: {e}")

        # Download image if it exists to pass to Gemini
        if img_url:
            try:
                img_r = requests.get(img_url, headers=HEADERS)
                if img_r.status_code == 200:
                    img_obj = Image.open(io.BytesIO(img_r.content)).convert('RGB')
                    downloaded_images.append(img_obj)
            except Exception as e:
                print(f"⚠️ Failed to download image {img_url}: {e}")

        # Construct Story Text
        story_blob = f"---\nTITLE: {title}\nAUTHOR: u/{author}\nUPVOTES: {score}\n"
        if body_text:
            story_blob += f"BODY TEXT: {body_text}...\n"
        if img_url:
            story_blob += f"[IMAGE ATTACHED AND SENT TO AI]\n"
        if comments_text:
            story_blob += "TOP COMMENTS:\n" + "\n".join(comments_text) + "\n"

        stories.append(story_blob)
        print(f"✅ Fetched ({idx}/10): {title[:40]}...")

    return stories, downloaded_images


def generate_newsletter_content(raw_stories, images):
    print("🧠 AI Editor is analyzing text and images to write the newspaper...")
    today = datetime.date.today().strftime("%A, %B %d, %Y")
    
    prompt = f"""
You are the Chief Editor of "VIT AP NEWS".

Today's Date: {today}

RAW DATA FROM r/vitap:
{ "".join(raw_stories) }

(Note: You also have access to images extracted from these posts provided alongside this prompt. Use their visual context to make your reporting more accurate and entertaining!)

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

- Each story: MAXIMUM 3 sentences. Include observations from the provided images if they are relevant.
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
    
    # Gemini 2.5 Flash can take a list containing the text prompt and PIL Images directly!
    payload = [prompt] + images

    try:
        response = model.generate_content(payload)
        return response.text
    except Exception as e: 
        return f"AI Error: {e}"

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
    raw_text_data, raw_images = fetch_stories()
    
    if raw_text_data:
        ai_text = generate_newsletter_content(raw_text_data, raw_images)
        generate_image_from_markdown(ai_text)
        send_image_to_discord()
    else:
        print("No news today.")