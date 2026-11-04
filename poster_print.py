"""
Fixed-size print poster: fills an exact page (default A2 portrait, 300 dpi).

- Rows are justified: every row spans the full page width.
- Row heights are equal, so the page is filled top to bottom with no gaps.
- Images are center-cropped to their cell (cover fit), so no white space is left.
- Upscaling uses the same linear <-> Lanczos blend as poster.py (--t).
- Output: PNG + PDF with the physical page size.

Usage:
    python poster_print.py photos out_A2 --rows 14 --t 0.5
"""
import argparse
import os

from PIL import Image, ImageFilter

from poster import EXTS, upscale

DPI = 300
SIZES_MM = {"A2": (420, 594), "A1": (594, 841), "A3": (297, 420), "A4": (210, 297)}


def page_px(size_name):
    w_mm, h_mm = SIZES_MM[size_name]
    return round(w_mm / 25.4 * DPI), round(h_mm / 25.4 * DPI)


def pack_rows(aspects, n_rows):
    """Split images into n_rows rows with roughly equal total aspect (sum of w/h).

    Greedy: a row closes when its aspect sum reaches the average target.
    Keeps the original order. Returns a list of index lists.
    """
    target = sum(aspects) / n_rows
    rows, row, acc = [], [], 0.0
    for i, a in enumerate(aspects):
        remaining_rows = n_rows - len(rows)
        remaining_items = len(aspects) - i
        # Start a new row early enough that every remaining row gets at least one image.
        if row and acc + a / 2 > target and remaining_rows > 1 and remaining_items >= remaining_rows:
            rows.append(row)
            row, acc = [], 0.0
        row.append(i)
        acc += a
    if row:
        rows.append(row)
    return rows


def cover(img, w, h, t, sharpen=0.0):
    """Center-crop img to the aspect ratio w/h, then resize to (w, h).

    sharpen: 0 = off, 1 = strong unsharp mask. Adds perceived sharpness only;
    it cannot restore detail that the small source does not have.
    """
    src_ratio = img.width / img.height
    dst_ratio = w / h
    if src_ratio > dst_ratio:
        new_w = round(img.height * dst_ratio)
        left = (img.width - new_w) // 2
        img = img.crop((left, 0, left + new_w, img.height))
    else:
        new_h = round(img.width / dst_ratio)
        top = (img.height - new_h) // 2
        img = img.crop((0, top, img.width, top + new_h))
    out = upscale(img, w, h, t)
    if sharpen > 0:
        out = out.filter(ImageFilter.UnsharpMask(radius=2, percent=int(sharpen * 200), threshold=2))
    return out


def build(input_dir, out_base, size_name, n_rows, t, sharpen=0.0):
    page_w, page_h = page_px(size_name)
    paths = sorted(
        os.path.join(input_dir, f) for f in os.listdir(input_dir) if f.lower().endswith(EXTS)
    )
    images = [Image.open(p).convert("RGB") for p in paths]
    aspects = [im.width / im.height for im in images]

    rows = pack_rows(aspects, n_rows)
    row_h = page_h // len(rows)
    page_h = row_h * len(rows)  # exact multiple, no leftover strip

    poster = Image.new("RGB", (page_w, page_h), (255, 255, 255))
    crop_losses = []
    y = 0
    for idx_list in rows:
        row_aspect = sum(aspects[i] for i in idx_list)
        x = 0
        for k, i in enumerate(idx_list):
            # Width proportional to the image's share of the row, so the row fills exactly.
            w = page_w - x if k == len(idx_list) - 1 else round(page_w * aspects[i] / row_aspect)
            cell = cover(images[i], w, row_h, t, sharpen)
            poster.paste(cell, (x, y))
            # How much of the image was cropped away (0 = none).
            kept = min(aspects[i], w / row_h) / max(aspects[i], w / row_h)
            crop_losses.append(1 - kept)
            x += w
        y += row_h

    png_path = out_base + ".png"
    pdf_path = out_base + ".pdf"
    poster.save(png_path, dpi=(DPI, DPI))
    poster.save(pdf_path, resolution=DPI)
    avg_crop = 100 * sum(crop_losses) / len(crop_losses)
    print(f"{len(images)} images, {len(rows)} rows, {size_name} {page_w}x{page_h}px @ {DPI}dpi, t={t}")
    print(f"average crop: {avg_crop:.1f}%")
    print(f"saved: {png_path}")
    print(f"saved: {pdf_path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("input_dir")
    ap.add_argument("out_base", help="output name without extension")
    ap.add_argument("--size", default="A2", choices=list(SIZES_MM))
    ap.add_argument("--rows", type=int, default=14)
    ap.add_argument("--t", type=float, default=0.5, help="0 = linear, 1 = Lanczos")
    ap.add_argument("--sharpen", type=float, default=0.0, help="0 = off, 1 = strong unsharp mask")
    a = ap.parse_args()
    build(a.input_dir, a.out_base, a.size, a.rows, a.t, a.sharpen)
