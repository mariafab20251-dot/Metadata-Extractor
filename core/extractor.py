import whisper
import easyocr
from PIL import Image, ImageEnhance, ImageFilter
from moviepy import VideoFileClip
import os
import re
import warnings
from config import FRAME_INTERVAL, WHISPER_MODEL, WHISPER_MODEL_DIR, EASYOCR_MODEL_DIR

# Suppress annoying warnings
warnings.filterwarnings('ignore', category=UserWarning, module='torch')
warnings.filterwarnings('ignore', category=UserWarning, module='whisper')
warnings.filterwarnings('ignore', message='.*pin_memory.*')
warnings.filterwarnings('ignore', message='.*FP16 is not supported on CPU.*')

class MediaExtractor:
    def __init__(self):
        self.whisper_model = None
        self.ocr_reader = None

    def load_whisper(self):
        if self.whisper_model is None:
            print("🔄 Loading Whisper model...")
            # Use local model if bundled in portable package, else download
            if WHISPER_MODEL_DIR.exists() and (WHISPER_MODEL_DIR / f"{WHISPER_MODEL}.pt").exists():
                self.whisper_model = whisper.load_model(WHISPER_MODEL, download_root=str(WHISPER_MODEL_DIR))
                print(f"✅ Whisper model loaded from: {WHISPER_MODEL_DIR}")
            else:
                self.whisper_model = whisper.load_model(WHISPER_MODEL)
                print("✅ Whisper model loaded (downloaded)")

    def load_easyocr(self):
        if self.ocr_reader is None:
            # Initialize EasyOCR with English language
            # gpu=False for CPU, set to True if you have CUDA GPU
            print("🔄 Loading OCR model...")
            # Use local models if bundled, else download
            if EASYOCR_MODEL_DIR.exists() and any(EASYOCR_MODEL_DIR.glob("*.pth")):
                self.ocr_reader = easyocr.Reader(
                    ['en'], gpu=False, verbose=False,
                    model_storage_directory=str(EASYOCR_MODEL_DIR),
                )
                print(f"✅ OCR model loaded from: {EASYOCR_MODEL_DIR}")
            else:
                self.ocr_reader = easyocr.Reader(['en'], gpu=False, verbose=False)
                print("✅ OCR model loaded (downloaded)")

    def clean_ocr_text(self, text):
        """Clean and normalize OCR text"""
        if not text:
            return ""

        # Remove all special characters except basic punctuation and numbers
        text = re.sub(r'[^a-zA-Z0-9\s.,!?\'-]', ' ', text)

        # Fix multiple apostrophes
        text = re.sub(r"'{2,}", "'", text)

        # Fix spaces before apostrophes
        text = re.sub(r"\s+'", "'", text)

        # Remove excessive underscores and dashes
        text = re.sub(r'_{2,}', '', text)
        text = re.sub(r'-{2,}', '', text)

        # Remove usernames/handles (words starting with @)
        text = re.sub(r'@\w+', '', text)

        # Remove single character fragments surrounded by spaces (but not 'I' or 'A')
        text = re.sub(r'\s[b-hj-zB-HJ-Z]\s', ' ', text)

        # Normalize whitespace
        text = ' '.join(text.split())

        # Remove very short fragments (likely noise)
        if len(text) < 10:
            return ""

        # Remove if mostly non-alphabetic (noise) - but allow some numbers
        alpha_count = sum(c.isalpha() for c in text)
        if alpha_count < 15:  # At least 15 letters
            return ""

        return text.strip()

    def is_garbage_word(self, word):
        """Check if a word is likely garbage/noise"""
        # Single digit numbers are OK (1-8 list items)
        if word.isdigit():
            return False

        if len(word) <= 1:
            return True

        # Common OCR garbage words and usernames (but NOT common English words)
        garbage_list = ['ora', 'mil', 'wy', 'eel', 'ae', 'bo', 'rf', 'fag', 'fay',
                       'va', 'gj', 'Soe', 'Hal', 'pane', 'Chee', 'siaee', 'nites',
                       'Aap', 'Ti', 'Ee', 'Sg', 'NE', 'att', 'tiie', 'Ses',
                       'thebizthoughts', 'Ax']
        if word in garbage_list or word.lower() in garbage_list:
            return True

        # Very short words (2 letters) that aren't common English
        if len(word) == 2:
            common_2letter = ['is', 'it', 'at', 'to', 'in', 'on', 'or', 'an', 'as', 'be',
                             'by', 'do', 'go', 'he', 'hi', 'if', 'me', 'my', 'no', 'of',
                             'ok', 'so', 'up', 'us', 'we']
            # Don't filter if it's a common word
            if word.lower() in common_2letter:
                return False
            # Otherwise, filter uncommon 2-letter words
            return True

        # Check for mixed case in short words (like "Ee", "Al")
        if len(word) <= 2 and word[0].isupper() and (len(word) > 1 and word[1].islower() or word[1].isupper()):
            return True

        # Check for words with too many uppercase (like "Aap", "Ti")
        if len(word) >= 2:
            upper_count = sum(1 for c in word if c.isupper())
            if upper_count > len(word) * 0.6:  # More than 60% uppercase
                return True

        # Check for mixed alpha-digit in very short words only
        has_alpha = any(c.isalpha() for c in word)
        has_digit = any(c.isdigit() for c in word)
        if has_alpha and has_digit and len(word) <= 2:  # Changed from 3 to 2
            return True

        # Single uppercase letter words (I, A are OK, but other single letters are noise)
        if len(word) == 1 and word.isupper() and word not in ['I', 'A']:
            return True

        # 3-letter words with unusual patterns
        if len(word) == 3:
            # All consonants or very uncommon patterns
            vowels = set('aeiouAEIOU')
            if not any(c in vowels for c in word):
                # No vowels - likely garbage
                return True

        return False

    def clean_sentence_endings(self, sentence):
        """Remove garbage from the end of sentences"""
        words = sentence.split()

        # Work backwards and remove trailing garbage
        while len(words) >= 2:
            # Check if last 2 words look like garbage pattern
            last_two = ' '.join(words[-2:]).lower()

            # Common garbage patterns at end
            garbage_endings = ['at is', 'is at', 'at in', 'in at', 'is in', 'in is',
                              'at to', 'to at', 'is to', 'to is']

            if last_two in garbage_endings:
                # Remove last 2 words
                words = words[:-2]
            elif len(words[-1]) <= 2 and words[-1].lower() in ['at', 'is', 'in', 'to', 'an', 'or']:
                # Single trailing preposition/conjunction at end (likely garbage)
                words = words[:-1]
            else:
                break

        return ' '.join(words)

    def filter_sentences(self, text):
        """Filter out garbage sentences and garbage words from text"""
        if not text:
            return ""

        # Split into sentences (rough)
        sentences = re.split(r'[.!?]+', text)

        clean_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # Filter garbage words from the sentence
            words = sentence.split()
            clean_words = [w for w in words if not self.is_garbage_word(w)]

            # Re-check sentence validity after word filtering
            if len(clean_words) < 3:  # Too short after filtering
                continue

            # Count very short words (1-2 letters)
            short_words = sum(1 for w in clean_words if len(w) <= 2)
            short_word_ratio = short_words / len(clean_words)

            # Reject if more than 40% are very short words (likely garbage)
            if short_word_ratio > 0.4:
                continue

            # Count words with 4+ letters (likely real words)
            real_words = sum(1 for w in clean_words if len(w) >= 4)

            # Need at least 3 real words for a valid sentence
            if real_words < 3:
                continue

            # Rebuild sentence from clean words
            clean_sentence = ' '.join(clean_words)

            # Clean garbage from sentence endings
            clean_sentence = self.clean_sentence_endings(clean_sentence)

            # Final check - sentence must still have meaningful content
            if len(clean_sentence.split()) >= 3:
                clean_sentences.append(clean_sentence)

        return '. '.join(clean_sentences) if clean_sentences else ""

    def format_numbered_list(self, text):
        """Format numbered lists properly with line breaks"""
        if not text:
            return text

        # Detect CTA patterns (call to action)
        cta_patterns = [
            r'(follow me)', r'(subscribe)', r'(like and subscribe)',
            r'(hit the bell)', r'(turn on notifications)', r'(advise you to follow)',
            r'(check out)', r'(link in bio)', r'(comment below)'
        ]

        cta_text = ""
        for pattern in cta_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Extract everything from the CTA onwards
                cta_start = match.start()
                # Find the sentence containing CTA
                # Look for sentence before CTA
                before_cta = text[:cta_start].rstrip()
                sentences = re.split(r'[.!?]\s+', before_cta)
                if sentences:
                    # Last complete sentence before CTA
                    last_sentence_end = before_cta.rfind(sentences[-1])
                    if last_sentence_end > 0:
                        cta_text = text[last_sentence_end + len(sentences[-1]):].strip()
                        text = text[:last_sentence_end + len(sentences[-1])].strip()
                        # Clean up CTA
                        cta_text = re.sub(r'^\.\s*', '', cta_text)  # Remove leading period
                        break

        # Find all numbers in the text (1-20 range for list items)
        number_pattern = r'\b([1-9]|1[0-9]|20)\b\.?\s*'
        numbers_found = list(re.finditer(number_pattern, text))

        if len(numbers_found) < 2:
            # Not a numbered list, return as-is with CTA
            if cta_text:
                return f"{text}\n\n{cta_text}"
            return text

        # Extract items based on number positions
        items = []

        for i, match in enumerate(numbers_found):
            num = int(match.group(1))
            start_pos = match.end()

            # Find end position (start of next number or end of text)
            if i + 1 < len(numbers_found):
                end_pos = numbers_found[i + 1].start()
            else:
                end_pos = len(text)

            # Extract item text
            item_text = text[start_pos:end_pos].strip()

            # Clean up item text
            item_text = re.sub(r'^\d+\.?\s*', '', item_text)  # Remove any leading numbers
            item_text = re.sub(r'\s+', ' ', item_text)  # Normalize spaces
            item_text = item_text.rstrip('.,!?')  # Remove trailing punctuation

            if item_text:
                items.append((num, item_text))

        if not items:
            if cta_text:
                return f"{text}\n\n{cta_text}"
            return text

        # Extract title (everything before first number)
        first_number_pos = numbers_found[0].start()
        title = text[:first_number_pos].strip()

        # Clean up title
        title = re.sub(r'\s+', ' ', title)
        title = title.rstrip('.,!?')

        # Build formatted output
        result_lines = []

        # Add title if exists
        if title:
            result_lines.append(title)
            result_lines.append("")  # Blank line after title

        # Add numbered items
        for num, item_text in items:
            result_lines.append(f"{num}. {item_text}")

        # Add CTA with double line break
        if cta_text:
            result_lines.append("")  # Blank line
            result_lines.append(cta_text)

        return '\n'.join(result_lines)

    def normalize_for_comparison(self, text):
        """Strip text down to just words for similarity comparison"""
        # Remove all non-alphabetic characters
        text = re.sub(r'[^a-zA-Z\s]', '', text)
        # Lowercase and normalize spaces
        text = ' '.join(text.lower().split())
        return text

    def are_similar_texts(self, text1, text2, threshold=0.75):
        """Check if two texts are similar (for deduplication)"""
        if not text1 or not text2:
            return False

        # Normalize both texts to just words
        norm1 = self.normalize_for_comparison(text1)
        norm2 = self.normalize_for_comparison(text2)

        if not norm1 or not norm2:
            return False

        # Exact match after normalization
        if norm1 == norm2:
            return True

        # One contains the other (substring match)
        if norm1 in norm2 or norm2 in norm1:
            return True

        # Word-based similarity
        words1 = set(norm1.split())
        words2 = set(norm2.split())

        if not words1 or not words2:
            return False

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        similarity = intersection / union if union > 0 else 0

        return similarity >= threshold

    def preprocess_image(self, image):
        """Enhance image for better OCR"""
        # Convert to grayscale
        image = image.convert('L')

        # Increase contrast
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)

        # Sharpen
        image = image.filter(ImageFilter.SHARPEN)

        return image

    def extract_overlay_text(self, video_path, video_id):
        self.load_easyocr()
        clip = None

        try:
            clip = VideoFileClip(video_path)
            duration = int(clip.duration)

            unique_texts = []

            # Sample frames at intervals (in-memory, no disk I/O)
            for t in range(0, duration, FRAME_INTERVAL):
                try:
                    # Get frame as numpy array directly (fast, no disk I/O)
                    frame = clip.get_frame(t)
                    img = Image.fromarray(frame)
                    img = self.preprocess_image(img)

                    # Convert to numpy array for EasyOCR
                    import numpy as np
                    frame_np = np.array(img)

                    # Extract text using EasyOCR (accepts numpy arrays directly)
                    results = self.ocr_reader.readtext(frame_np)

                    # Sort results by Y-coordinate (top to bottom) for proper reading order
                    sorted_results = sorted(results, key=lambda x: x[0][0][1])

                    # Combine all detected text in proper order
                    raw_text = ' '.join([detection[1] for detection in sorted_results])
                    cleaned_text = self.clean_ocr_text(raw_text)

                    # Filter sentences to remove garbage
                    filtered_text = self.filter_sentences(cleaned_text)

                    if filtered_text:
                        # Check if this text is similar to any we already have
                        is_duplicate = False
                        for existing_text in unique_texts:
                            if self.are_similar_texts(filtered_text, existing_text):
                                is_duplicate = True
                                break

                        if not is_duplicate:
                            unique_texts.append(filtered_text)

                except Exception:
                    continue

            # Join unique texts - pick the longest/cleanest version if we have similar ones
            if unique_texts:
                # Sort by length descending - longest is usually cleanest
                unique_texts.sort(key=len, reverse=True)
                # Get the longest (cleanest) version
                result = unique_texts[0]
                # Format numbered lists with proper line breaks
                result = self.format_numbered_list(result)
            else:
                result = ""

            return result

        finally:
            if clip:
                clip.close()

    def extract_speech(self, video_path):
        self.load_whisper()

        result = self.whisper_model.transcribe(video_path)
        return result["text"].strip()
