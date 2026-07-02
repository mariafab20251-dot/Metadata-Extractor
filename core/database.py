import sqlite3
import hashlib
from datetime import datetime
from config import DB_PATH

class VideoDatabase:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.create_table()

    def create_table(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processed_videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url_hash TEXT UNIQUE NOT NULL,
                video_id TEXT,
                platform TEXT,
                url TEXT,
                overlay_text TEXT,
                speech_text TEXT,
                captions TEXT,
                hashtags TEXT,
                timestamp TEXT,
                transcript_word_count INTEGER DEFAULT 0,
                transcript_wpm REAL DEFAULT 0.0,
                video_duration REAL DEFAULT 0.0,
                generated_script TEXT,
                generated_word_count INTEGER DEFAULT 0,
                suggested_title TEXT,
                hashtag_1 TEXT,
                hashtag_2 TEXT
            )
        ''')
        self.conn.commit()
        # Add columns if they don't exist (for databases created before these columns)
        self._add_column_if_missing('transcript_word_count', 'INTEGER DEFAULT 0')
        self._add_column_if_missing('transcript_wpm', 'REAL DEFAULT 0.0')
        self._add_column_if_missing('video_duration', 'REAL DEFAULT 0.0')
        self._add_column_if_missing('generated_script', 'TEXT')
        self._add_column_if_missing('generated_word_count', 'INTEGER DEFAULT 0')
        self._add_column_if_missing('suggested_title', 'TEXT')
        self._add_column_if_missing('hashtag_1', 'TEXT')
        self._add_column_if_missing('hashtag_2', 'TEXT')
        # view_count added 2026-06-16 for results_clean.xlsx column
        self._add_column_if_missing('view_count', 'INTEGER DEFAULT 0')

    def _add_column_if_missing(self, col_name, col_type):
        """Add a column if it doesn't exist (ALTER TABLE IF NOT EXISTS isn't supported)"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(f"ALTER TABLE processed_videos ADD COLUMN {col_name} {col_type}")
            self.conn.commit()
        except sqlite3.OperationalError:
            pass  # Column already exists

    def get_url_hash(self, url):
        return hashlib.md5(url.encode()).hexdigest()

    def is_processed(self, url):
        url_hash = self.get_url_hash(url)
        cursor = self.conn.cursor()
        cursor.execute('SELECT id FROM processed_videos WHERE url_hash = ?', (url_hash,))
        return cursor.fetchone() is not None

    def get_processed_data(self, url):
        url_hash = self.get_url_hash(url)
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT overlay_text, speech_text, captions, hashtags,
                   transcript_word_count, transcript_wpm, video_duration,
                   generated_script, generated_word_count, suggested_title,
                   hashtag_1, hashtag_2, view_count
            FROM processed_videos
            WHERE url_hash = ?
        ''', (url_hash,))
        result = cursor.fetchone()
        if result:
            return {
                'overlay_text': result[0] or '',
                'speech_text': result[1] or '',
                'captions': result[2] or '',
                'hashtags': result[3] or '',
                'transcript_word_count': result[4] or 0,
                'transcript_wpm': result[5] or 0.0,
                'video_duration': result[6] or 0.0,
                'generated_script': result[7] or '',
                'generated_word_count': result[8] or 0,
                'suggested_title': result[9] or '',
                'hashtag_1': result[10] or '',
                'hashtag_2': result[11] or '',
                'view_count': result[12] or 0
            }
        return None

    def add_video(self, video_id, platform, url, overlay_text, speech_text,
                  captions, hashtags, transcript_word_count=0, transcript_wpm=0.0,
                  video_duration=0.0, view_count=0, generated_script='', generated_word_count=0,
                  suggested_title='', hashtag_1='', hashtag_2=''):
        url_hash = self.get_url_hash(url)
        timestamp = datetime.now().isoformat()
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO processed_videos
            (url_hash, video_id, platform, url, overlay_text, speech_text, captions, hashtags,
             timestamp, transcript_word_count, transcript_wpm, video_duration,
             view_count,
             generated_script, generated_word_count, suggested_title, hashtag_1, hashtag_2)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (url_hash, video_id, platform, url, overlay_text, speech_text,
              captions, hashtags, timestamp, transcript_word_count, transcript_wpm,
              video_duration, view_count,
              generated_script, generated_word_count, suggested_title,
              hashtag_1, hashtag_2))
        self.conn.commit()

    def mark_processed(self, url):
        url_hash = self.get_url_hash(url)
        timestamp = datetime.now().isoformat()
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO processed_videos
            (url_hash, url, timestamp)
            VALUES (?, ?, ?)
        ''', (url_hash, url, timestamp))
        self.conn.commit()

    def close(self):
        self.conn.close()
