import sqlite3
from pathlib import Path

def check_missing_videos(input_file):
    """Check which URLs from input file are not in database"""

    db_path = Path(__file__).parent / "data" / "processed.db"

    # Read input URLs
    with open(input_file, 'r', encoding='utf-8') as f:
        input_urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]

    print(f"Total URLs in input file: {len(input_urls)}")

    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check which URLs are processed
    processed = []
    missing = []

    for url in input_urls:
        import hashlib
        url_hash = hashlib.md5(url.encode()).hexdigest()
        cursor.execute('SELECT url, overlay_text, speech_text FROM processed_videos WHERE url_hash = ?', (url_hash,))
        result = cursor.fetchone()

        if result:
            processed.append({
                'url': result[0],
                'has_ocr': bool(result[1]),
                'has_speech': bool(result[2])
            })
        else:
            missing.append(url)

    conn.close()

    # Report
    print(f"\n{'='*80}")
    print(f"PROCESSING REPORT")
    print(f"{'='*80}")
    print(f"✅ Processed: {len(processed)}")
    print(f"❌ Missing: {len(missing)}")

    # Check incomplete processing
    incomplete = [p for p in processed if not p['has_ocr'] or not p['has_speech']]
    if incomplete:
        print(f"⚠️  Incomplete (missing OCR or speech): {len(incomplete)}")

    # Save missing URLs to file
    if missing:
        missing_file = Path(__file__).parent / "data" / "missing_urls.txt"
        with open(missing_file, 'w', encoding='utf-8') as f:
            for url in missing:
                f.write(url + '\n')
        print(f"\n❌ Missing URLs saved to: {missing_file}")
        print(f"\nFirst 10 missing URLs:")
        for url in missing[:10]:
            print(f"  • {url}")

    # Save incomplete URLs to file
    if incomplete:
        incomplete_file = Path(__file__).parent / "data" / "incomplete_urls.txt"
        with open(incomplete_file, 'w', encoding='utf-8') as f:
            for item in incomplete:
                f.write(item['url'] + '\n')
        print(f"\n⚠️  Incomplete URLs saved to: {incomplete_file}")
        print(f"\nFirst 10 incomplete URLs:")
        for item in incomplete[:10]:
            ocr_status = "✓" if item['has_ocr'] else "✗"
            speech_status = "✓" if item['has_speech'] else "✗"
            print(f"  • OCR:{ocr_status} Speech:{speech_status} - {item['url'][:60]}...")

    print(f"\n{'='*80}")

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python check_missing.py <input_file.txt>")
        print("\nExample: python check_missing.py urls.txt")
        sys.exit(1)

    input_file = sys.argv[1]

    if not Path(input_file).exists():
        print(f"Error: File not found: {input_file}")
        sys.exit(1)

    check_missing_videos(input_file)
