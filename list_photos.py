"""
Write app/photos.json: the list of photo paths the web app loads.
Run again after sync.py adds new photos.

Usage:  python list_photos.py
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
PHOTO_DIR = os.path.join(HERE, "photos")
OUT = os.path.join(HERE, "app", "photos.json")
EXTS = (".jpg", ".jpeg", ".png", ".webp")

AUTHORS_FILE = os.path.join(HERE, "authors.json")
HIDE_CAPTION = {"t.me/realybad", "источник скрыт"}
with open(AUTHORS_FILE, encoding="utf-8") as f:
    authors = json.load(f)  # {post_id: author}, written by sync.py

files = sorted(f for f in os.listdir(PHOTO_DIR) if f.lower().endswith(EXTS))
entries = []
for f in files:
    m = re.match(r"post(\d+)_", f)  # files are named post<id>_<hash>.<ext>
    author = authors.get(m.group(1)) if m else None
    if author in HIDE_CAPTION:  # own posts and hidden sources get no caption on the poster
        author = None
    entries.append({"path": f"../photos/{f}", "author": author})  # path relative to app/index.html
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(entries, f, ensure_ascii=False, indent=1)
missing = sum(1 for e in entries if not e["author"])
print(f"{len(entries)} photos ({missing} without author) -> {OUT}")
