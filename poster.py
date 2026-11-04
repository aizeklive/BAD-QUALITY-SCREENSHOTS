"""
Prototype: justified poster layout with adjustable upscaling.

- justify(): packs images into rows so every row fills the poster width exactly.
- upscale(): enlarges an image with a blend between BILINEAR (t=0, linear)
  and LANCZOS (t=1, sharp). Values in between give intermediate results.

Usage:
    python poster.py <input_dir> <output.png> [--width 3000] [--row-height 400] [--t 0.3]
Needs Pillow only.
"""
import argparse
import os

from PIL import Image

EXTS = (".jpg", ".jpeg", ".png", ".webp")


def upscale(img, scale_w, scale_h, t):
    """Resize to (scale_w, scale_h). t=0 is linear (bilinear), t=1 is Lanczos."""
    t = max(0.0, min(1.0, t))
    linear = img.resize((scale_w, scale_h), Image.Resampling.BILINEAR)
    if t == 0:
        return linear
    sharp = img.resize((scale_w, scale_h), Image.Resampling.LANCZOS)
    if t == 1:
        return sharp
    return Image.blend(linear, sharp, t)


def justify(images, poster_width, target_row_height):
    """Greedy justified rows.

    Each row gets as many images as fit at target_row_height. Then the row is
    stretched so its images fill poster_width exactly. Returns a list of rows,
    where each row is a list of (image, width, height) in pixels.
    """
    rows, row, row_aspect = [], [], 0.0
    for img in images:
        aspect = img.width / img.height
        if row and (row_aspect + aspect) * target_row_height > poster_width:
            rows.append(row)
            row, row_aspect = [], 0.0
        row.append(img)
        row_aspect += aspect
    if row:
        rows.append(row)

    placed = []
    for row in rows:
        aspect_sum = sum(i.width / i.height for i in row)
        # Height that makes this row exactly poster_width wide.
        h = round(poster_width / aspect_sum)
        items, x_used = [], 0
        for k, img in enumerate(row):
            if k < len(row) - 1:
                w = round(img.width / img.height * h)
            else:
                w = poster_width - x_used  # last image absorbs rounding error
            items.append((img, w, h))
            x_used += w
        placed.append(items)
    return placed


def build(input_dir, output, poster_width, row_height, t):
    paths = sorted(
        os.path.join(input_dir, f)
        for f in os.listdir(input_dir)
        if f.lower().endswith(EXTS)
    )
    images = [Image.open(p).convert("RGB") for p in paths]
    rows = justify(images, poster_width, row_height)

    total_h = sum(items[0][2] for items in rows)
    poster = Image.new("RGB", (poster_width, total_h), (255, 255, 255))
    y = 0
    for items in rows:
        x = 0
        for img, w, h in items:
            poster.paste(upscale(img, w, h, t), (x, y))
            x += w
        y += items[0][2]

    poster.save(output)
    print(f"{len(images)} images in {len(rows)} rows -> {output} ({poster_width}x{total_h}px, t={t})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("input_dir")
    ap.add_argument("output")
    ap.add_argument("--width", type=int, default=3000)
    ap.add_argument("--row-height", type=int, default=400)
    ap.add_argument("--t", type=float, default=0.0, help="0 = linear, 1 = Lanczos")
    a = ap.parse_args()
    build(a.input_dir, a.output, a.width, a.row_height, a.t)
