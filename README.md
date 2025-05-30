# Export Edge & Brave Bookmarks to Backblaze B2

This script exports your bookmarks from **Microsoft Edge** and **Brave** browsers and uploads them to a Backblaze B2 bucket in both JSON and HTML formats.

---

## Features

- **Exports bookmarks** from Edge and Brave for the current user.
- **Uploads** the exports to Backblaze B2 in two formats:
  - JSON (raw bookmark data)
  - HTML (Netscape Bookmark File, importable to browsers)

---

## Getting Started

### 1. Clone the Repository

```sh
git clone https://github.com/YOUR_USERNAME/bookmarks2b2.git
cd bookmarks2b2
```

### 2. Set up a Python Virtual Environment (Recommended)

```sh
python -m venv venv
pip install b2sdk pyinstaller
```

### 3. Configure Backblaze Credentials

Open `export_bookmarks.py` and replace the placeholders at the top with your Backblaze B2 credentials:

```python
B2_APPLICATION_KEY_ID = 'YOUR_KEY_ID_HERE'
B2_APPLICATION_KEY = 'YOUR_APPLICATION_KEY_HERE'
B2_BUCKET_NAME = 'YOUR_BUCKET_NAME_HERE'
```

### 4. Run the Script

```sh
python export_bookmarks.py
```

This will create two files in your current directory:

`bookmarks_export_YYYYMMDD_HHMMSS.json`

`bookmarks_export_YYYYMMDD_HHMMSS.html`

Both files will be uploaded to your Backblaze B2 bucket.

### 5. (Optional) Compile to a Standalone Executable

If you want a standalone .exe file (for Windows):

```sh
pyinstaller --onefile export_bookmarks.py
```

The resulting .exe will be found in the dist directory.
