"""
Twitter/X Upload Script

Uploads videos to Twitter/X using Twitter API (Free Tier Compatible!)

Requirements:
- Twitter Developer Account (FREE tier works!)
- TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET

Free Tier Limits:
- 500 posts per month
- Video size: max 512 MB
- Video duration: max 140 seconds
"""

import os
import sys
import time
import tweepy
from pathlib import Path
from dotenv import load_dotenv

# Configure UTF-8 encoding for console output (Windows fix)
if sys.platform == 'win32':
    import codecs
    try:
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    except Exception:
        pass

# Load environment variables
load_dotenv()

def upload_to_twitter(video_path, caption):
    """Upload video to Twitter/X using API v1.1 (media) + v2 (post)."""
    
    api_key = os.getenv('TWITTER_API_KEY', '').strip()
    api_secret = os.getenv('TWITTER_API_SECRET', '').strip()
    access_token = os.getenv('TWITTER_ACCESS_TOKEN', '').strip()
    access_secret = os.getenv('TWITTER_ACCESS_SECRET', '').strip()
    
    if not all([api_key, api_secret, access_token, access_secret]):
        raise ValueError("[twitter] Missing Twitter credentials in .env")
    
    print("[twitter] [info] Uploading to Twitter/X...")
    
    video_path_obj = Path(video_path)
    if not video_path_obj.exists():
        raise FileNotFoundError(f"[twitter] [error] Video file not found: {video_path}")
    
    file_size_mb = video_path_obj.stat().st_size / (1024 * 1024)
    print(f"[twitter] Video size: {file_size_mb:.2f} MB")
    
    try:
        # 1. Authenticate V1 (Media Upload)
        print("[twitter] Authenticating with API v1.1 (media upload)...")
        auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_secret)
        api_v1 = tweepy.API(auth)
        
        # 2. Authenticate V2 (Posting)
        print("[twitter] Authenticating with API v2 (posting)...")
        client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_secret
        )
        
        # 3. Upload Video (Chunked)
        print("[twitter] Uploading video (chunked)...")
        media = api_v1.media_upload(
            filename=str(video_path_obj),
            media_category='tweet_video',
            chunked=True 
        )
        media_id = media.media_id
        print(f"[twitter] [success] Video uploaded! Media ID: {media_id}")
        
        # 4. Wait for Processing (with Polling)
        print("[twitter] Waiting for video processing...")
        processing_start = time.time()
        while True:
            status = api_v1.get_media_upload_status(media_id)
            processing_info = getattr(status, 'processing_info', None)
            
            if not processing_info:
                # If no processing info, it might be already done or not required
                break
                
            state = processing_info.get('state')
            print(f"[twitter] Processing state: {state}")
            
            if state == 'succeeded':
                break
            if state == 'failed':
                raise Exception(f"Twitter video processing failed: {processing_info.get('error')}")
            
            check_after_secs = processing_info.get('check_after_secs', 5)
            time.sleep(check_after_secs)
            
            if time.time() - processing_start > 300: # 5 minute timeout
                print("[twitter] [warning] Processing timeout, trying to post anyway...")
                break
        
        # 5. Post Tweet (with small retry logic for 503)
        print("[twitter] Posting tweet...")
        tweet_text = caption[:280]
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = client.create_tweet(
                    text=tweet_text,
                    media_ids=[media_id]
                )
                tweet_id = response.data['id']
                tweet_url = f"https://twitter.com/i/web/status/{tweet_id}"
                print(f"[twitter] [success] Posted to Twitter!")
                print(f"[twitter] URL: {tweet_url}")
                return {'id': tweet_id, 'url': tweet_url, 'platform': 'twitter'}
            except tweepy.errors.TwitterServerError as e:
                if "503" in str(e) and attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 10
                    print(f"[twitter] [error] 503 Service Unavailable. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                raise
        
    except tweepy.errors.Unauthorized as e:
        print(f"[twitter] [error] Authentication failed: {e}")
        raise
    except tweepy.errors.Forbidden as e:
        print(f"[twitter] [error] Permission denied: {e}")
        raise
    except tweepy.errors.TooManyRequests as e:
        print(f"[twitter] [error] Rate limit exceeded: {e}")
        raise
    except Exception as e:
        print(f"[twitter] [error] Unexpected error: {e}")
        raise

if __name__ == '__main__':
    # Test block
    video_file = Path('output/final_video.mp4')
    if video_file.exists():
        upload_to_twitter(video_file, "Test Upload #TwitterAPI")
    else:
        print("[twitter] No test video found.")
