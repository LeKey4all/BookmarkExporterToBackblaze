"""
Export Edge & Brave Bookmarks to Backblaze B2

How to compile to .exe:
    Install PyInstaller:
        pip install pyinstaller

    Then run:
        pyinstaller --onefile export_bookmarks.py

Replace BACKBLAZE credentials before use.

Required pip packages:
    pip install b2sdk
"""

import os
import json
import sys
import getpass
from datetime import datetime

from b2sdk.v2 import InMemoryAccountInfo, B2Api

# ------------------- CONFIGURATION -------------------

# Replace these placeholders with your actual Backblaze credentials
B2_APPLICATION_KEY_ID = 'YOUR_KEY_ID_HERE'
B2_APPLICATION_KEY = 'YOUR_APPLICATION_KEY_HERE'
B2_BUCKET_NAME = 'YOUR_BUCKET_NAME_HERE'
B2_BUCKET_PATH_JSON = 'exports/bookmarks_{date}.json'  
B2_BUCKET_PATH_HTML = 'exports/bookmarks_{date}.html'

# ------------------- BOOKMARK EXTRACTION -------------------

def get_chromium_bookmark_path(browser):
    """
    Get the path to the Bookmarks file for Edge or Brave for the current user.
    """
    local_appdata = os.environ.get('LOCALAPPDATA')
    if browser == "edge":
        path = os.path.join(local_appdata, r"Microsoft\Edge\User Data\Default\Bookmarks")
    elif browser == "brave":
        path = os.path.join(local_appdata, r"BraveSoftware\Brave-Browser\User Data\Default\Bookmarks")
    else:
        raise ValueError("Unsupported browser.")
    return path if os.path.exists(path) else None

def extract_bookmarks_from_file(bookmark_file):
    """
    Recursively extract all bookmarks (with folders) from a Chromium Bookmarks file.
    Returns a list of bookmark dicts.
    """
    with open(bookmark_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    roots = data.get('roots', {})
    all_roots = [roots.get(key) for key in ['bookmark_bar', 'other', 'synced'] if roots.get(key)]

    bookmarks = []
    for root in all_roots:
        bookmarks.extend(process_bookmark_folder(root, path=[]))
    return bookmarks

def process_bookmark_folder(node, path):
    """
    Recursively process a bookmark folder or bookmark node.
    """
    results = []
    node_type = node.get('type')
    if node_type == 'folder':
        folder_name = node.get('name', 'Unnamed Folder')
        for child in node.get('children', []):
            results.extend(process_bookmark_folder(child, path + [folder_name]))
    elif node_type == 'url':
        results.append({
            'name': node.get('name'),
            'url': node.get('url'),
            'path': path
        })
    return results

def collect_all_bookmarks():
    """
    Collect bookmarks from both Edge and Brave.
    """
    export = {
        'exported_at': datetime.utcnow().isoformat() + 'Z',
        'user': getpass.getuser(),
        'bookmarks': {}
    }
    for browser in ["edge", "brave"]:
        path = get_chromium_bookmark_path(browser)
        if path:
            bookmarks = extract_bookmarks_from_file(path)
            export['bookmarks'][browser] = bookmarks
        else:
            export['bookmarks'][browser] = []
    return export

# ------------------- EXPORT & UPLOAD -------------------

def save_bookmarks_to_json(data, out_path):
    """
    Save the collected bookmarks to a JSON file.
    """
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def save_bookmarks_to_html(data, out_path):
    """
    Export bookmarks to HTML in Netscape Bookmark File format (importable to browsers).
    """
    def html_escape(text):
        # Basic HTML escaping
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def add_bookmarks(bookmarks, f, indent=1, parent_folder=None):
        last_path = []
        for bm in bookmarks:
            # Close folders if we go up
            while last_path and (len(bm['path']) < len(last_path) or bm['path'][:len(last_path)] != last_path):
                f.write("  " * (len(last_path) + 1) + "</DL><p>\n")
                last_path.pop()
            # Open new folders if we go down
            for i, folder in enumerate(bm['path'][len(last_path):]):
                f.write("  " * (len(last_path) + i + 1) + f'<DT><H3>{html_escape(folder)}</H3>\n')
                f.write("  " * (len(last_path) + i + 2) + "<DL><p>\n")
                last_path.append(folder)
            # Write bookmark
            f.write("  " * (len(bm['path']) + 1) +
                    f'<DT><A HREF="{html_escape(bm["url"])}">{html_escape(bm["name"])}</A>\n')
        # Close all open folders
        while last_path:
            f.write("  " * (len(last_path) + 1) + "</DL><p>\n")
            last_path.pop()

    with open(out_path, "w", encoding="utf-8") as f:
        f.write('<!DOCTYPE NETSCAPE-Bookmark-file-1>\n')
        f.write('<!-- This is an automatically generated file.\n'
                '     It will be read and overwritten.\n'
                '     DO NOT EDIT! -->\n')
        f.write('<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">\n')
        f.write(f'<TITLE>Bookmarks Export - {data["user"]}</TITLE>\n')
        f.write(f'<H1>Bookmarks Export ({data["user"]}, {data["exported_at"]})</H1>\n')
        f.write('<DL><p>\n')

        for browser in ("edge", "brave"):
            f.write(f'  <DT><H3>{browser.title()} Bookmarks</H3>\n')
            f.write('  <DL><p>\n')
            # Sort bookmarks by path for correct folder handling
            bookmarks = sorted(data['bookmarks'][browser], key=lambda bm: bm['path'])
            add_bookmarks(bookmarks, f, indent=2, parent_folder=browser)
            f.write('  </DL><p>\n')

        f.write('</DL><p>\n')

def upload_to_backblaze_b2(local_file, remote_path):
    """
    Upload the given local file to Backblaze B2 at the specified path.
    """
    info = InMemoryAccountInfo()
    b2_api = B2Api(info)
    b2_api.authorize_account("production", B2_APPLICATION_KEY_ID, B2_APPLICATION_KEY)
    bucket = b2_api.get_bucket_by_name(B2_BUCKET_NAME)
    with open(local_file, 'rb') as f:
        file_size = os.path.getsize(local_file)
        bucket.upload_bytes(
            f.read(),
            remote_path,
            file_infos={"src": os.path.basename(local_file)},
            content_type="application/json"
        )
    print(f"Uploaded {local_file} to b2://{B2_BUCKET_NAME}/{remote_path}")

# ------------------- MAIN EXECUTION -------------------

def main():
    print("Exporting bookmarks from Edge and Brave...")
    export_data = collect_all_bookmarks()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_json = f"bookmarks_export_{timestamp}.json"
    out_html = f"bookmarks_export_{timestamp}.html"
    # Save both formats
    save_bookmarks_to_json(export_data, out_json)
    print(f"Bookmarks exported to {out_json}")
    save_bookmarks_to_html(export_data, out_html)
    print(f"Bookmarks exported to {out_html}")

    # Upload both files to Backblaze B2
    remote_json = B2_BUCKET_PATH_JSON.format(date=timestamp)
    remote_html = B2_BUCKET_PATH_HTML.format(date=timestamp)

    print(f"Uploading JSON to Backblaze B2 bucket '{B2_BUCKET_NAME}' at '{remote_json}'...")
    upload_to_backblaze_b2(out_json, remote_json)

    print(f"Uploading HTML to Backblaze B2 bucket '{B2_BUCKET_NAME}' at '{remote_html}'...")
    upload_to_backblaze_b2(out_html, remote_html)

    print("Done.")

if __name__ == "__main__":
    main()
