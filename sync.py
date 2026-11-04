"""
Sync photos from the public preview of https://t.me/s/realybad into ./photos.

- Idempotent: re-running only downloads photos that are missing.
- Exclusions: post IDs listed in exclude.txt (one per line) are skipped.
- Each file is checked by its magic bytes, so an HTML error page is never saved as a photo.

Usage:  python sync.py          (needs Python 3, no extra packages)
"""
import hashlib
import html
import json
import os
import re
import time
import urllib.request

CHANNEL = "realybad"
CHANNEL_CREDIT = "t.me/realybad"  # credit for posts that are not forwarded
HERE = os.path.dirname(os.path.abspath(__file__))
PHOTO_DIR = os.path.join(HERE, "photos")
EXCLUDE_FILE = os.path.join(HERE, "exclude.txt")
AUTHORS_FILE = os.path.join(HERE, "authors.json")
UA = "Mozilla/5.0"
MAGIC = {b"\xff\xd8\xff": ".jpg", b"\x89PNG\r\n\x1a\n": ".png", b"RIFF": ".webp"}


def author_of(chunk):
    """Credit for one post: the forward source if the post is forwarded, else the channel.
    A forwarded post whose source hid the name gets a placeholder."""
    if "tgme_widget_message_forwarded_from" not in chunk:
        return CHANNEL_CREDIT
    m = re.search(r'tgme_widget_message_forwarded_from_name">([^<]*)<', chunk)
    name = html.unescape(m.group(1)).strip() if m else ""
    return name or "источник скрыт"


def fetch(url, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception as e:
            print(f"  retry {attempt + 1} for {url[:60]}...: {e}")
            time.sleep(2 + attempt * 2)
    return None


def crawl_manifest():
    """Walk the channel backwards via ?before=<min_id>.
    Returns (sorted (post_id, photo_url) pairs, {post_id: author})."""
    pairs = set()
    authors = {}
    before = None
    while True:
        url = f"https://t.me/s/{CHANNEL}" + (f"?before={before}" if before else "")
        page = fetch(url)
        if not page:
            break
        html = page.decode("utf-8", errors="ignore")
        ids = []
        for chunk in re.split(r'data-post="%s/' % CHANNEL, html)[1:]:
            pid = int(re.match(r"\d+", chunk).group())
            ids.append(pid)
            authors[pid] = author_of(chunk)
            for u in re.findall(r"background-image:url\(&?['\"]?(https://[^'\")&]+)", chunk):
                pairs.add((pid, u))
        if not ids or min(ids) <= 1:
            break
        before = min(ids)
        time.sleep(1)
    return sorted(pairs), authors


def load_exclude():
    if not os.path.exists(EXCLUDE_FILE):
        return set()
    with open(EXCLUDE_FILE, encoding="utf-8") as f:
        return {int(line.strip()) for line in f if line.strip().isdigit()}


def main():
    os.makedirs(PHOTO_DIR, exist_ok=True)
    excluded = load_exclude()
    pairs, authors = crawl_manifest()
    print(f"Found {len(pairs)} photo links on the channel.")
    with open(AUTHORS_FILE, "w", encoding="utf-8") as f:
        json.dump({str(k): v for k, v in authors.items()}, f, ensure_ascii=False, indent=1)
    print(f"Authors saved for {len(authors)} posts -> {AUTHORS_FILE}")
    new = failed = skipped = 0
    seen = {}
    for pid, url in pairs:
        if pid in excluded:
            skipped += 1
            continue
        # Name = post id + order within the post. Telegram CDN URLs change between requests,
        # so a hash of the URL would create duplicates on every run.
        k = seen.get(pid, 0)
        seen[pid] = k + 1
        base = os.path.join(PHOTO_DIR, f"post{pid}_{k:02d}")
        if any(os.path.exists(base + ext) for ext in MAGIC.values()):
            continue  # already downloaded
        data = fetch(url)
        ext = next((e for m, e in MAGIC.items() if data and data.startswith(m)), None)
        if ext is None:
            failed += 1
            print(f"  not an image, skipped: post {pid}")
            continue
        with open(base + ext, "wb") as f:
            f.write(data)
        new += 1
    print(f"New: {new}  failed: {failed}  excluded: {skipped}")


if __name__ == "__main__":
    main()
