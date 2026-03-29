import os
import time
import csv
from urllib.parse import urlparse
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

# Credentials will be read dynamically from environment variables
def get_credentials():
    load_dotenv()
    return os.getenv("LINKEDIN_EMAIL", ""), os.getenv("LINKEDIN_PASSWORD", "")

def calculate_virality_score(degree):
    """Formula: 1st=1, 2nd=3, 3rd=5"""
    d = str(degree).lower()
    if "1" in d: return 1
    if "2" in d: return 3
    if "3" in d or "out" in d: return 5
    return 5

def export_to_csv(data, filename="virality_results.csv"):
    """
    Exports data to a CSV file ready for Streamlit, Google Sheets and Kumu.io.
    """
    print(f"\n[Export] Saving data to {filename}...")
    headers = ["Author Name", "Author URL", "Author Company", "Post URL", "Post Text", 
               "Reactor Name", "Reactor URL", "Connection Degree", "Reactor Company/Headline", "Virality Score"]
               
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        
        for row in data:
            writer.writerow({
                "Author Name": row.get("target_name"),
                "Author URL": row.get("target_url"),
                "Author Company": row.get("target_company"),
                "Post URL": row.get("post_url"),
                "Post Text": (row.get("post_text", "")[:100] + "...").replace("\n", " "),
                "Reactor Name": row.get("Name"),
                "Reactor URL": row.get("Profile_URL"),
                "Connection Degree": row.get("Connection_Degree"),
                "Reactor Company/Headline": row.get("Current_Company"),
                "Virality Score": calculate_virality_score(row.get("Connection_Degree"))
            })
    print(f"-> Successfully saved {len(data)} reaction edges to {filename}.")

def main(profile_url, author_company="Unknown", limit_posts=10, limit_reactions=100, headless=True):
    email, password = get_credentials()
    if not email or not password:
         print("Error: LINKEDIN_EMAIL and LINKEDIN_PASSWORD must be in the .env file or environment.")
         return

    all_reactions_data = []
    
    # Optional: extract a basic name from the URL for display purposes
    parsed = urlparse(profile_url)
    target_name = parsed.path.strip("/").split("/")[-1].replace("-", " ").title()

    print(f"=== Starting LinkedIn Playwright Scraper for '{target_name}' ===")

    with sync_playwright() as p:
        # We use a user agent to look more like a real browser
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        # Step 1: Login
        print("[Auth] Logging into LinkedIn...")
        page.goto("https://www.linkedin.com/login")
        page.fill("input#username", email)
        page.fill("input#password", password)
        page.click("button[type='submit']")
        page.wait_for_load_state("networkidle")
        
        # Verify login was successful
        if "/feed" not in page.url and "/checkpoint" in page.url:
            print("[Auth Error] LinkedIn asked for a security checkpoint. Run this locally with headed=False once to solve CAPTCHA.")
            browser.close()
            return
            
        print("[Auth] Successfully logged in.")

        # Step 2: Navigate to user's recent activity (posts)
        # Ensure url ends cleanly
        clean_url = profile_url.rstrip("/")
        activity_url = f"{clean_url}/recent-activity/all/"
        print(f"\n[Step A+B] Navigating to {activity_url} to fetch recent posts...")
        page.goto(activity_url)
        page.wait_for_load_state("networkidle")
        time.sleep(3) # Let posts load

        # Scroll to load enough posts
        for _ in range(5):
             page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
             time.sleep(2)

        # Extract Post URLs and text
        # LinkedIn feed items have complex selectors. Finding update urns or links to the post.
        posts = []
        feed_items = page.locator("div[data-urn^='urn:li:activity']").all()
        
        for item in feed_items:
             if len(posts) >= limit_posts:
                  break
             try:
                 # Check if this item has a direct link
                 post_urn = item.get_attribute("data-urn")
                 text = item.inner_text()
                 
                 # The post direct URL format:
                 post_url = f"https://www.linkedin.com/feed/update/{post_urn}/"
                 
                 posts.append({
                      "post_urn": post_urn,
                      "post_url": post_url,
                      "text": text.replace("\n", " ")[:200]
                 })
             except Exception as e:
                 pass
                 
        print(f"-> Found {len(posts)} posts.")

        # Step 3: Extract Reactions for each Post
        for i, post in enumerate(posts):
             print(f"\n[Step C] Extracting reactions for post {i+1}/{len(posts)} ({post['post_url']})...")
             page.goto(post["post_url"])
             page.wait_for_load_state("networkidle")
             time.sleep(2)
             
             # Locate the "likes/reactions" button and click it to open modal
             # This changes often. Usually it's a button containing the reaction icons.
             try:
                 reactions_button = page.locator("button:has(img[alt*='reaction']), button[aria-label*='Reactions']").first
                 if reactions_button.count() > 0:
                      reactions_button.click()
                      page.wait_for_selector("div.artdeco-modal", timeout=5000)
                      time.sleep(2)
                      
                      # Scroll the modal
                      modal_scroll_area = page.locator("div.artdeco-modal__content")
                      collected_reactions = 0
                      retries = 0
                      
                      while collected_reactions < limit_reactions and retries < 5:
                           modal_scroll_area.evaluate("node => node.scrollTo(0, node.scrollHeight)")
                           time.sleep(1.5)
                           
                           # Extract current users
                           reactors = page.locator("li.artdeco-list__item").all()
                           collected_reactions = len(reactors)
                           retries += 1
                           
                      # Parse reactors
                      reactors = page.locator("li.artdeco-list__item").all()
                      for reactor in reactors[:limit_reactions]:
                           try:
                               name_loc = reactor.locator("span[dir='ltr']").first
                               name = name_loc.inner_text() if name_loc.count() > 0 else "Unknown Name"
                               
                               link_loc = reactor.locator("a").first
                               url = link_loc.get_attribute("href") if link_loc.count() > 0 else ""
                               if url and url.startswith("/in/"):
                                   url = f"https://www.linkedin.com{url.split('?')[0]}"
                                   
                               headline_loc = reactor.locator("div.artdeco-entity-lockup__caption").first
                               headline = headline_loc.inner_text() if headline_loc.count() > 0 else "Unknown Title"
                               
                               # Connection Degree is usually a span near the name
                               degree_loc = reactor.locator("span.artdeco-entity-lockup__badge span.visually-hidden").first
                               degree = degree_loc.inner_text() if degree_loc.count() > 0 else "3rd"
                               
                               all_reactions_data.append({
                                   "target_name": target_name,
                                   "target_url": clean_url,
                                   "target_company": author_company,
                                   "post_url": post["post_url"],
                                   "post_text": post["text"],
                                   "Name": name,
                                   "Profile_URL": url,
                                   "Connection_Degree": degree,
                                   "Current_Company": headline
                               })
                           except Exception as e:
                               continue
             except Exception as e:
                 print("Could not load reactions modal for this post or there were no reactions.")
                 
             if i < len(posts) - 1:
                  print("Enforcing safety limit: Waiting 30 seconds before next post...")
                  time.sleep(30)

        browser.close()
        
    # Export
    export_to_csv(all_reactions_data)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="LinkedIn Virality Pipeline (Playwright)")
    parser.add_argument("--url", type=str, required=True, help="Target's full LinkedIn Profile URL")
    parser.add_argument("--company", type=str, default="Unknown", help="Target's Company Name")
    parser.add_argument("--headed", action="store_true", help="Run browser in headed mode")
    
    args = parser.parse_args()
    main(args.url, author_company=args.company, headless=not args.headed)
