#!/usr/bin/env python3
"""Safely append submitted, embedded photos to the BUET83 Gallery page."""
import base64
import json
import re
from pathlib import Path

ROOT = Path(".")
GALLERY = ROOT / "gallery.html"
PAYLOAD_DIR = ROOT / "gallery_photo_updates"

def main():
    payloads = sorted(PAYLOAD_DIR.glob("*.json"))
    if not payloads:
        print("No Gallery photo payloads found.")
        return

    html = GALLERY.read_text(encoding="utf-8")
    changed = False

    for payload_path in payloads:
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        photo_id = payload["photo_id"]
        caption = payload["caption"]
        category = payload.get("category", "friends")
        batch_label = payload.get("batch_label", "New submission")
        parts = payload.get("image_base64_parts")
        if parts:
            image_b64 = "".join((ROOT / part).read_text(encoding="ascii").strip() for part in parts)
        else:
            image_b64 = payload["image_base64"]

        if category not in {"early", "friends", "reunions"}:
            raise ValueError(f"Unsupported category: {category}")

        match = re.fullmatch(r"BUET83-(\d{3})", photo_id)
        if not match:
            raise ValueError(f"Invalid permanent ID: {photo_id}")

        # Verify JPEG or WebP bytes before inserting the data URI.
        image_bytes = base64.b64decode(image_b64, validate=True)
        if image_bytes.startswith(bytes.fromhex("FFD8FF")):
            image_mime = "image/jpeg"
        elif image_bytes.startswith(b"RIFF") and image_bytes[8:12] == b"WEBP":
            image_mime = "image/webp"
        else:
            raise ValueError(f"{photo_id} is not a supported JPEG or WebP image.")

        ids = [int(n) for n in re.findall(r'data-id="BUET83-(\d{3})"', html)]
        expected = max(ids, default=0) + 1
        supplied = int(match.group(1))

        if photo_id in html:
            print(f"{photo_id} already exists; skipping duplicate.")
            payload_path.unlink()
            for part in payload.get("image_base64_parts", []):
                (ROOT / part).unlink(missing_ok=True)
            continue
        if supplied != expected:
            raise ValueError(
                f"Expected next permanent ID BUET83-{expected:03d}, got {photo_id}."
            )

        data_uri = f"data:{image_mime};base64," + image_b64
        safe_caption = (caption.replace("&", "&amp;").replace("<", "&lt;")
                               .replace(">", "&gt;").replace('"', "&quot;"))
        card = f"""
<article class="gi reveal" data-cat="{category}" data-id="{photo_id}" onclick="openLightbox(this)">
      <img class="gi-img" src="{data_uri}" alt="{photo_id} — {safe_caption}" loading="lazy">
      <div class="gi-info"><div class="gi-meta"><span class="gi-id">{photo_id}</span><span class="gi-batch">{batch_label}</span></div>
      <div class="gi-caption">{safe_caption}</div></div>
    </article>"""

        # Insert after the highest existing photo card, preserving the rest of the page.
        anchor_id = f'data-id="BUET83-{expected - 1:03d}"'
        anchor = html.find(anchor_id)
        if anchor < 0:
            raise ValueError(f"Could not find previous photo card {anchor_id}.")
        close = html.find("</article>", anchor)
        if close < 0:
            raise ValueError("Could not find end of previous photo card.")
        close += len("</article>")
        html = html[:close] + "\n" + card + html[close:]

        # Update visible total text.
        html, n1 = re.subn(
            r'(<span class="phs-n">)\d+(</span><span class="phs-l">Photos</span>)',
            rf'\g<1>{supplied}\2', html, count=1
        )
        html, n2 = re.subn(r'\b53 photographs\b', f'{supplied} photographs', html, count=1)
        html, n3 = re.subn(r'Showing 53 photographs', f'Showing {supplied} photographs', html, count=1)
        if n1 != 1 or n2 != 1 or n3 != 1:
            raise ValueError("Could not safely update all Gallery photo counts.")

        payload_path.unlink()
        for part in payload.get("image_base64_parts", []):
            (ROOT / part).unlink(missing_ok=True)
        changed = True
        print(f"Appended {photo_id}.")

    if changed:
        GALLERY.write_text(html, encoding="utf-8")
        print("Updated gallery.html.")
    else:
        print("No Gallery changes required.")

if __name__ == "__main__":
    main()
