#!/usr/bin/env python3
"""Rebuild the profile list inside souvenir.html from the profile pages in this folder.

How it works:
  1. Looks at every .html file next to this script, except the site pages listed in SKIP.
  2. A file counts as a profile if it has <div class="name"> and a subtitle line
     ("Department | BUET83") in its header.
  3. Rewrites everything between the PROFILES-START and PROFILES-END markers in souvenir.html.

Only the Python standard library is used. Run it with:  python3 build_profiles.py
"""
import glob
import html
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ALBUM = os.path.join(HERE, "souvenir.html")
SKIP = {"index.html", "news.html", "forum.html", "events.html",
        "members.html", "gallery.html", "contact.html", "souvenir.html"}
START = "// PROFILES-START"
END = "// PROFILES-END"

NAME_RE = re.compile(r'<div[^>]*class="name"[^>]*>(.*?)</div>', re.S)
SUB_RE = re.compile(r'<div[^>]*class="(?:sub|subtitle)"[^>]*>(.*?)</div>', re.S)
TAG_RE = re.compile(r"<[^>]+>")


def clean(text):
    text = TAG_RE.sub("", text)
    text = html.unescape(text).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def js_string(text):
    return text.replace("\\", "\\\\").replace("'", "\\'")


def read_profile(path):
    with open(path, encoding="utf-8", errors="replace") as handle:
        page = handle.read()
    name_match = NAME_RE.search(page)
    sub_match = SUB_RE.search(page)
    if not name_match or not sub_match:
        return None
    name = clean(name_match.group(1))
    sub = clean(sub_match.group(1))
    if not name or "BUET83" not in sub.upper():
        return None
    dept = sub.split("|")[0].strip()
    return name, dept


def main():
    entries = []
    for path in sorted(glob.glob(os.path.join(HERE, "*.html"))):
        filename = os.path.basename(path)
        if filename in SKIP:
            continue
        found = read_profile(path)
        if found is None:
            print("skipped (not a profile page): " + filename)
            continue
        name, dept = found
        if not dept:
            print("warning: no department found in " + filename)
        entries.append((name, dept, filename))

    entries.sort(key=lambda item: item[0].casefold())
    lines = ["  {name:'%s', dept:'%s', file:'%s'}" % (js_string(n), js_string(d), js_string(f))
             for n, d, f in entries]
    block = START + "\n" + ",\n".join(lines) + ("\n" if lines else "") + "  " + END

    with open(ALBUM, encoding="utf-8") as handle:
        album = handle.read()
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    if not pattern.search(album):
        print("error: markers not found in souvenir.html. Upload the updated souvenir.html first.")
        return 1
    updated = pattern.sub(lambda _m: block, album, count=1)

    print("profiles found: %d" % len(entries))
    for n, d, f in entries:
        print("  - %s | %s | %s" % (n, d, f))
    if updated == album:
        print("souvenir.html is already up to date.")
        return 0
    with open(ALBUM, "w", encoding="utf-8", newline="") as handle:
        handle.write(updated)
    print("souvenir.html updated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
