import base64
import json
import os
import time
import requests
import re
from html import unescape
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
# NOTE: this file is imported as a *top-level* module named ``main``
# (``utils/fb_scraper`` is put on ``sys.path`` by ``utils/fb_scraper_worker.py``
# and ``facebook_ui.py`` does ``from main import ...``), so the sibling scraper
# modules must be imported absolutely - a relative import (``from .x import y``)
# raises "attempted relative import with no known parent package".
from comment_scraper import (fetch_comments, fetch_replies,
                             fb_json, GRAPHQL, PROXIES)
from post_scraper import (fetch_posts as fetch_page_posts,
                          extract_media as extract_page_media,
                          parse_fb_response as parse_page_response)
from group_post_scraper_v2 import fetch_posts as fetch_group_posts
from single_post_image import fetch_all_images


def extract_user_id_from_url(url, cookies=None):
    """Extract Facebook User ID from a profile URL"""
    # First, try to extract ID directly from URL
    url_patterns = [
        r'profile\.php\?id=(\d+)',
        r'/profile/(\d+)',
        r'id=(\d+)'
    ]
    
    for pattern in url_patterns:
        match = re.search(pattern, url)
        if match:
            user_id = match.group(1)
            print(f"  ✅ Found User ID in URL: {user_id}")
            return user_id
    
    # If no ID in URL, fetch the page and search in HTML
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept-Language": "en-US,en;q=0.9"
    }
    
    try:
        print(f"  No ID in URL, fetching page: {url}")
        response = requests.get(url, headers=headers, cookies=cookies, proxies=PROXIES, timeout=20)
        html = response.text
        
        # Try multiple patterns to find user ID in HTML
        patterns = [
            r'fb://profile/(\d+)',           # BEST signal
            r'"profile_owner":"(\d+)"',
            r'"userID":"(\d+)"',
            r'owner_id=(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                user_id = match.group(1)
                print(f"  ✅ Found User ID: {user_id}")
                return user_id
        
        print("  ❌ User ID not found (profile may be private or login wall)")
        return None
    
    except Exception as e:
        print(f"  ❌ Error fetching URL: {e}")
        return None


def extract_group_id_from_url(url, cookies=None):
    """Extract Facebook Group ID from a group URL"""
    # First, try to extract ID directly from URL
    url_patterns = [
        r'/groups/(\d+)',
        r'group_id=(\d+)',
        r'gid=(\d+)'
    ]
    
    for pattern in url_patterns:
        match = re.search(pattern, url)
        if match:
            group_id = match.group(1)
            print(f"  ✅ Found Group ID in URL: {group_id}")
            return group_id
    
    # If no ID in URL, fetch the page and search in HTML
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept-Language": "en-US,en;q=0.9"
    }
    
    try:
        print(f"  No ID in URL, fetching group page: {url}")
        response = requests.get(url, headers=headers, cookies=cookies, proxies=PROXIES, timeout=20)
        html = response.text
        
        # Try multiple patterns to find group ID in HTML
        patterns = [
            r'fb://group/(\d+)',              # BEST signal
            r'fb://group/\?id=(\d+)',         # iOS URL format
            r'"group_id":"(\d+)"',
            r'"groupID":"(\d+)"'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                group_id = match.group(1)
                print(f"  ✅ Found Group ID: {group_id}")
                return group_id
        
        print("  ❌ Group ID not found (group may be private or login wall)")
        return None
    
    except Exception as e:
        print(f"  ❌ Error fetching URL: {e}")
        return None


def extract_post_id_from_url(url, cookies=None):
    """Extract Facebook Post ID from a post URL"""
    
    # First, try to extract post ID directly from URL patterns (no fetch needed)
    url_patterns = [
        r'/groups/[^/]+/posts/(\d+)',           # /groups/MemeAddiction/posts/4471339869798423
        r'/posts/(\d+)',                         # /posts/123456
    ]
    
    for pattern in url_patterns:
        match = re.search(pattern, url)
        if match:
            post_id = match.group(1)
            print(f"  ✅ Found Post ID in URL: {post_id}")
            return post_id
    
    # If no direct pattern match, fetch the page and extract from HTML
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept-Language": "en-US,en;q=0.9"
    }
    
    try:
        print(f"  No direct ID in URL, fetching post: {url}")
        response = requests.get(url, headers=headers, cookies=cookies, proxies=PROXIES, timeout=20)
        html = response.text
        
        post_id = None
        
        # Method 1: Try storyID (works with authenticated requests)
        if cookies:
            story_id_match = re.search(r'"storyID":"([^"]+)"', html)
            if story_id_match:
                story_id_encoded = story_id_match.group(1)
                try:
                    # Decode base64 storyID
                    story_id_decoded = base64.b64decode(story_id_encoded).decode('utf-8')
                    print(f"  📝 Decoded storyID: {story_id_decoded}")
                    
                    # Extract post ID (last segment after splitting by ':')
                    # Format: S:_USER_ID:POST_ID:POST_ID or similar
                    parts = story_id_decoded.split(':')
                    if len(parts) >= 2:
                        post_id = parts[-1]  # Last part is the post ID
                        print(f"  ✅ Found Post ID from storyID: {post_id}")
                        return post_id
                except Exception as e:
                    print(f"  ⚠️ Could not decode storyID: {e}")
        
        # Method 2: Extract og:url meta tag (fallback for unauthenticated or if storyID fails)
        og_url_match = re.search(
            r'<meta property="og:url" content="([^"]+)"',
            html
        )
        
        if og_url_match:
            og_url = unescape(og_url_match.group(1))
            
            # Case 1: /posts/POST_ID/ (group posts) or /posts/.../POST_ID/ (user posts)
            m = re.search(r'/posts/(?:[^/]+/)?(\d+)', og_url)
            
            # Case 2: permalink.php?story_fbid=POST_ID
            if not m:
                m = re.search(r'story_fbid=(\d+)', og_url)
            
            if m:
                post_id = m.group(1)
        
        if post_id:
            print(f"  ✅ Found Post ID from og:url: {post_id}")
            return post_id
        
        print("  ❌ Post ID not found in URL")
        return None
    
    except Exception as e:
        print(f"  ❌ Error fetching URL: {e}")
        return None


def convert_post_id_to_feedback_id(post_id):
    """Convert post_id to feedback_id using base64 encoding"""
    feedback_id = base64.b64encode(f"feedback:{post_id}".encode()).decode()
    return feedback_id


def fetch_comments_for_post(post_id, cookies=None):
    """Fetch all comments and replies for a given post_id"""
    feedback_id = convert_post_id_to_feedback_id(post_id)
    print(f"  Fetching comments for post {post_id}...")
    print(f"  Using feedback_id: {feedback_id}")
    
    all_data = []
    comments, post_info = fetch_comments(feedback_id, cookies=cookies)
    
    for c in comments:
        print(f"    🗨️ {c.get('text', '')[:50]}...")
        c["replies"] = fetch_replies(c, cookies=cookies)
        
        for r in c["replies"]:
            print(f"       ↳ {r.get('text', '')[:50]}...")
        
        # Remove internal fields before appending
        c_clean = {k: v for k, v in c.items() if not k.startswith('_')}
        all_data.append(c_clean)
    
    print(f"  ✓ Found {len(all_data)} comments")
    return all_data, post_info


def export_comments_to_xlsx(folder_path, post_id, post_data, comments_data):
    """Export comments (with author names and replies) to an Excel (.xlsx) file"""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font
    except ImportError:
        print("  ⚠️ openpyxl not installed - skipping XLSX export (pip install openpyxl)")
        return
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Comments"
    
    # Header row
    headers = [
        "post_id", "post_message", "comment_id", "comment_author",
        "comment_text", "comment_reaction_count", "reply_author",
        "reply_text", "reply_reaction_count"
    ]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    
    post_message = post_data.get("message") or ""
    
    for idx, c in enumerate(comments_data, 1):
        if not c.get("replies"):
            ws.append([
                post_id, post_message, idx, c.get("author", ""),
                c.get("text", ""), c.get("reaction_count", ""),
                "", "", ""
            ])
        else:
            for r in c["replies"]:
                ws.append([
                    post_id, post_message, idx, c.get("author", ""),
                    c.get("text", ""), c.get("reaction_count", ""),
                    r.get("author", ""), r.get("text", ""),
                    r.get("reaction_count", "")
                ])
    
    # Auto-fit column widths (approximate)
    for col_cells in ws.columns:
        width = max(len(str(cell.value or "")) for cell in col_cells)
        ws.column_dimensions[col_cells[0].column_letter].width = min(max(width + 2, 10), 60)
    
    xlsx_path = os.path.join(folder_path, f"{post_id}.xlsx")
    os.makedirs(folder_path, exist_ok=True)
    wb.save(xlsx_path)
    print(f"  📊 Saved to {xlsx_path}")


def save_post_data(post_type, post_id, post_data, comments_data):
    """Save post and comments data in organized folder structure"""
    # For simple_post type, save directly under post_id (no intermediate name folder)
    if post_type == "simple_post":
        folder_path = os.path.join(post_type, post_id)
    else:
        # For page_post and group_post, use name folder structure
        # Extract page/group name from post_data
        name = post_data.get('page_name') or post_data.get('group_name')
        
        # Sanitize folder name
        if name:
            name_folder = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).strip()
            if not name_folder:
                name_folder = "Unknown"
        else:
            name_folder = "Unknown"
        
        # Create folder structure: [post_type]/[page_name or group_name]/[post_id]/
        folder_path = os.path.join(post_type, name_folder, post_id)
    
    os.makedirs(folder_path, exist_ok=True)
    
    # Combine post and comments in single file
    combined_data = {
        **post_data,
        "comments": comments_data
    }
    
    # Save as {post_id}.json
    output_file = os.path.join(folder_path, f"{post_id}.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(combined_data, f, ensure_ascii=False, indent=2)
    print(f"  💾 Saved to {output_file}")
    
    # Also save as Excel (.xlsx) with author names
    export_comments_to_xlsx(folder_path, post_id, post_data, comments_data)


def display_menu():
    """Display the main menu"""
    print("\n" + "="*60)
    print("   📘 FACEBOOK SCRAPER")
    print("="*60)
    print("\nChoose what to scrape:")
    print("  1. Single Post by URL/ID (full comment section - no post count needed)")
    print("  2. Page Posts (posts + comments from a page)")
    print("  3. Group Posts (posts + comments from a group)")
    print("  4. Exit")
    print("="*60)


def download_post_images(media_id, post_id, image_folder=None):
    """Fetch ALL images of a post and save them into image_folder (default simple_post/{post_id})"""
    if image_folder is None:
        image_folder = os.path.join("simple_post", post_id)
    os.makedirs(image_folder, exist_ok=True)

    import single_post_image

    def custom_fetch(node_id, p_id):
        current_node = node_id
        visited = set()
        image_count = 0

        while current_node and current_node not in visited:
            print(f"\n➡ Fetching node: {current_node}")
            visited.add(current_node)

            payload = single_post_image.build_payload(current_node, p_id)
            r = requests.post(single_post_image.GRAPHQL_URL, headers=single_post_image.HEADERS, data=payload)

            cleaned_blocks = single_post_image.process_raw_graphql(r.text)
            if not cleaned_blocks:
                break

            # Extract image
            image_url = None
            for block in cleaned_blocks:
                if "currMedia" in block:
                    image_url = block["currMedia"].get("image", {}).get("uri")
                    break

            if image_url:
                image_count += 1
                filename = f"{post_id}.jpg" if image_count == 1 else f"{post_id}_{image_count}.jpg"
                filepath = os.path.join(image_folder, filename)
                try:
                    r_img = requests.get(image_url, proxies=single_post_image.PROXIES, timeout=30)
                    r_img.raise_for_status()
                    with open(filepath, "wb") as f:
                        f.write(r_img.content)
                    print(f"📥 Saved {filename}")
                except Exception as e:
                    print(f"❌ Failed to download: {e}")

            # Get next node
            next_node = None
            for block in cleaned_blocks:
                if "nextMediaAfterNodeId" in block and block["nextMediaAfterNodeId"]:
                    node_id_next = block["nextMediaAfterNodeId"].get("id")
                    if node_id_next:
                        next_node = node_id_next
                        break

            if next_node:
                current_node = next_node
            else:
                print("✅ No more images.")
                break

    custom_fetch(media_id, post_id)
    print(f"  ✅ Images saved to {image_folder}")


def scrape_simple_post():
    """Scrape comments from a single post by URL or ID - no post count needed"""
    print("\n--- SIMPLE POST SCRAPER ---")
    print("Works with ANY post URL (group, page, profile, pfbid, permalink...) -")
    print("it scrapes that post's full comment section regardless of how old/new it is.")
    print("\nChoose input method:")
    print("  1. Enter Post URL (scrapes its whole comment section)")
    print("  2. Enter Post ID directly")
    
    input_choice = input("Your choice (1 or 2): ").strip()
    
    post_id = None
    
    if input_choice == "1":
        post_url = input("Enter Post URL: ").strip()
        if not post_url:
            print("❌ Invalid URL")
            return
        
        # Preferred path: direct single-post fetch by URL.
        # Works for ANY post (5th, 100th, whatever) - no "how many posts" prompt.
        post, comments, post_info = fetch_single_post_by_url(post_url)
        
        if post and post.get("post_id"):
            post_id = post["post_id"]
            
            # Save data
            save_post_data("simple_post", post_id, {**post, "type": "simple_post", "post_info": post_info}, comments)
            
            # Fetch images if media_id is available
            if post_info and post_info.get("media_id"):
                print(f"\n📸 Fetching images for media_id: {post_info['media_id']}")
                try:
                    download_post_images(post_info["media_id"], post_id)
                except Exception as e:
                    print(f"  ⚠️ Error fetching images: {e}")
            
            print(f"\n✅ Done! Saved to simple_post/{post_id}/")
            return
        
        # Fallback: old flow (extract ID from URL then fetch by ID)
        print("\n  ℹ️ Direct URL fetch failed, trying ID extraction fallback...")
        post_id = extract_post_id_from_url(post_url)
        if not post_id:
            print("❌ Could not extract Post ID from URL")
            return
    
    elif input_choice == "2":
        post_id = input("Enter Post ID: ").strip()
        if not post_id:
            print("❌ Invalid post ID")
            return
    
    else:
        print("❌ Invalid choice")
        return
    
    print(f"\nFetching comments for post {post_id}...")
    comments, post_info = fetch_comments_for_post(post_id)
    
    # Save data
    post_data = {
        "post_id": post_id,
        "type": "simple_post",
        "post_info": post_info
    }
    
    save_post_data("simple_post", post_id, post_data, comments)
    
    # Fetch images if media_id is available
    if post_info and post_info.get("media_id"):
        print(f"\n📸 Fetching images for media_id: {post_info['media_id']}")
        try:
            download_post_images(post_info["media_id"], post_id)
        except Exception as e:
            print(f"  ⚠️ Error fetching images: {e}")
    else:
        print("  ℹ️ No media_id found, skipping image download")
    
    print(f"\n✅ Done! Saved to simple_post/{post_id}/")


def scrape_page_posts():
    """Scrape posts and comments from a page"""
    print("\n--- PAGE POST SCRAPER ---")
    print("\nChoose input method:")
    print("  1. Enter Page URL (auto-extract ID)")
    print("  2. Enter Page/User ID directly")
    
    input_choice = input("Your choice (1 or 2): ").strip()
    
    page_id = None
    
    if input_choice == "1":
        page_url = input("Enter Page URL: ").strip()
        if not page_url:
            print("❌ Invalid URL")
            return
        
        # Extract user ID from URL
        page_id = extract_user_id_from_url(page_url)
        if not page_id:
            print("❌ Could not extract User ID from URL")
            return
    
    elif input_choice == "2":
        page_id = input("Enter Page/User ID: ").strip()
        if not page_id:
            print("❌ Invalid page ID")
            return
    
    else:
        print("❌ Invalid choice")
        return
    
    try:
        count = int(input("How many posts to fetch? ").strip())
    except ValueError:
        print("❌ Invalid number")
        return
    
    # Update the USER_ID in post_scraper
    import post_scraper
    post_scraper.USER_ID = page_id
    post_scraper.BASE_HEADERS["referer"] = f"https://www.facebook.com/profile.php?id={page_id}"
    
    print(f"\nFetching {count} posts from page {page_id}...")
    posts = fetch_page_posts(count)
    
    print(f"\n✓ Found {len(posts)} posts. Now fetching comments...")
    
    # Fetch comments for each post
    for i, post in enumerate(posts, 1):
        post_id = post.get("post_id")
        if not post_id:
            print(f"\n[{i}/{len(posts)}] ⚠️ Skipping post with no ID")
            continue
        
        print(f"\n[{i}/{len(posts)}] Processing post {post_id}...")
        
        try:
            comments, _ = fetch_comments_for_post(post_id)
            save_post_data("page_post", post_id, post, comments)
            time.sleep(1)  # Be nice to the server
        except Exception as e:
            print(f"  ❌ Error fetching comments: {e}")
            # Save post data even if comments fail
            save_post_data("page_post", post_id, post, [])
    
    print(f"\n✅ Done! Saved {len(posts)} posts to page_post/")


def scrape_group_posts():
    """Scrape posts and comments from a group"""
    print("\n--- GROUP POST SCRAPER ---")
    print("\nChoose input method:")
    print("  1. Enter Group URL (auto-extract ID)")
    print("  2. Enter Group ID directly")
    
    input_choice = input("Your choice (1 or 2): ").strip()
    
    group_id = None
    
    if input_choice == "1":
        group_url = input("Enter Group URL: ").strip()
        if not group_url:
            print("❌ Invalid URL")
            return
        
        # Extract group ID from URL
        group_id = extract_group_id_from_url(group_url)
        if not group_id:
            print("❌ Could not extract Group ID from URL")
            return
    
    elif input_choice == "2":
        group_id = input("Enter Group ID: ").strip()
        if not group_id:
            print("❌ Invalid group ID")
            return
    
    else:
        print("❌ Invalid choice")
        return
    
    try:
        count = int(input("How many posts to fetch? ").strip())
    except ValueError:
        print("❌ Invalid number")
        return
    
    # Update the GROUP_ID in group_post_scraper_v2
    import group_post_scraper_v2
    group_post_scraper_v2.GROUP_ID = group_id
    group_post_scraper_v2.HEADERS["referer"] = f"https://www.facebook.com/groups/{group_id}/"
    
    print(f"\nFetching {count} posts from group {group_id}...")
    posts = fetch_group_posts(count)
    
    print(f"\n✓ Found {len(posts)} posts. Now fetching comments...")
    
    # Fetch comments for each post
    for i, post in enumerate(posts, 1):
        post_id = post.get("post_id")
        if not post_id:
            print(f"\n[{i}/{len(posts)}] ⚠️ Skipping post with no ID")
            continue
        
        print(f"\n[{i}/{len(posts)}] Processing post {post_id}...")
        
        try:
            comments, _ = fetch_comments_for_post(post_id)
            save_post_data("group_post", post_id, post, comments)
            time.sleep(1)  # Be nice to the server
        except Exception as e:
            print(f"  ❌ Error fetching comments: {e}")
            # Save post data even if comments fail
            save_post_data("group_post", post_id, post, [])
    
    print(f"\n✅ Done! Saved {len(posts)} posts to group_post/")

    # =====================================================================
# NEW: Direct single-post fetch by URL (no "how many posts" prompt)
# =====================================================================

import re as _re_post
from urllib.parse import urlparse as _urlparse, parse_qs as _parse_qs


def extract_post_id_and_group_from_url(url):
    """
    Extract (post_id, group_id) from any FB post URL.

    Handles:
      - /groups/{gid}/posts/{pid}
      - /groups/{gid}/permalink/{pid}
      - /{page}/posts/{pid}
      - /permalink.php?story_fbid=...&id=...
      - /photo?fbid=...
      - pfbid... style IDs
    """
    if not url:
        return None, None

    url = url.strip().replace("m.facebook.com", "www.facebook.com") \
                     .replace("web.facebook.com", "www.facebook.com")

    # Query-string permalink
    if "permalink.php" in url or "story.php" in url:
        qs = _parse_qs(_urlparse(url).query)
        post_id  = (qs.get("story_fbid") or qs.get("fbid") or [None])[0]
        group_id = (qs.get("id") or [None])[0]
        return post_id, group_id

    # Photo permalink
    if "/photo" in url and "fbid=" in url:
        qs = _parse_qs(_urlparse(url).query)
        return (qs.get("fbid") or [None])[0], None

    # /groups/{gid}/posts/{pid}
    m = _re_post.search(r"/groups/([^/]+)/posts/([A-Za-z0-9]+)", url)
    if m:
        return m.group(2), m.group(1)

    # /groups/{gid}/permalink/{pid}
    m = _re_post.search(r"/groups/([^/]+)/permalink/([A-Za-z0-9]+)", url)
    if m:
        return m.group(2), m.group(1)

    # /{page}/posts/{pid}
    m = _re_post.search(r"/([^/]+)/posts/([A-Za-z0-9]+)", url)
    if m:
        return m.group(2), None

    # /posts/{pid}
    m = _re_post.search(r"/posts/([A-Za-z0-9]+)", url)
    if m:
        return m.group(1), None

    # /permalink/{pid}
    m = _re_post.search(r"/permalink/([A-Za-z0-9]+)", url)
    if m:
        return m.group(1), None

    return None, None


def fetch_single_post_by_url(url, cookies=None):
    """
    Fetch a single Facebook post directly by URL.

    Returns:
        (post_dict, comments_list, post_info) or (None, [], None) on failure.

    Strategy:
      1. Parse post_id + group_id from URL.
      2. Ask group scraper (v2) for the post node via its single-post query.
      3. Extract post metadata + media using group scraper's helpers.
      4. Fetch comments using comment_scraper.fetch_comments().
    """
    from group_post_scraper_v2 import (
        fetch_post_by_id,
        extract_post_data,
        GROUP_NAME,
    )
    from comment_scraper import fetch_comments as _fetch_comments, fetch_replies as _fetch_replies

    post_id, group_id = extract_post_id_and_group_from_url(url)
    if not post_id:
        print(f"  ❌ Could not extract post ID from URL: {url}")
        return None, [], None

    print(f"  🔎 Direct fetch: post_id={post_id}  group_id={group_id or 'n/a'}")

    # Ask group scraper for the raw story node
    node = fetch_post_by_id(post_id, group_id=group_id, cookies=cookies)
    if not node:
        print(f"  ❌ group_post_scraper_v2.fetch_post_by_id() returned no node")
        return None, [], None

    # Reuse existing extract_post_data()
    post = extract_post_data(node, GROUP_NAME)
    if not post:
        print(f"  ❌ extract_post_data() returned None")
        return None, [], None

    # Fetch comments using the same code path as simple_post
    import base64
    feedback_id = base64.b64encode(f"feedback:{post_id}".encode()).decode()

    print(f"  💬 Fetching comments for feedback_id={feedback_id}")
    raw_comments, post_info = _fetch_comments(feedback_id, cookies=cookies)

    comments = []
    for c in raw_comments:
        c["replies"] = _fetch_replies(c, cookies=cookies)
        c_clean = {k: v for k, v in c.items() if not k.startswith("_")}
        comments.append(c_clean)

    print(f"  ✓ Post fetched: {post_id}  ({len(comments)} comments)")
    return post, comments, post_info

def main():
    """Main function - GUI-like menu"""
    while True:
        display_menu()
        
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == "1":
            scrape_simple_post()
        elif choice == "2":
            scrape_page_posts()
        elif choice == "3":
            scrape_group_posts()
        elif choice == "4":
            print("\n👋 Goodbye!")
            break
        else:
            print("\n❌ Invalid choice. Please enter 1, 2, 3, or 4.")
        
        # Ask if user wants to continue
        if choice in ["1", "2", "3"]:
            continue_choice = input("\nPress Enter to return to menu (or 'q' to quit): ").strip().lower()
            if continue_choice == 'q':
                print("\n👋 Goodbye!")
                break


if __name__ == "__main__":
    main()
1