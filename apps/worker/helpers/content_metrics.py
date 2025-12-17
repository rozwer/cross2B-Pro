"""Content metrics calculation utilities.

Provides metrics calculation for text and Markdown content:
- Character, word, paragraph, sentence counts
- Markdown structure analysis (headings, lists, code blocks)
- Keyword density calculation
- Content comparison metrics
- Reading time estimation

Japanese language support:
- Japanese characters (hiragana, katakana, kanji) are counted as 1 word each
- English words are counted normally
- Mixed content calculates both and sums them
"""

import math
import re

from apps.worker.helpers.schemas import MarkdownMetrics, TextMetrics

# Japanese character ranges
JA_PATTERN = re.compile(r"[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]")
EN_WORD_PATTERN = re.compile(r"[a-zA-Z]+")

# Sentence ending patterns
JA_SENTENCE_END = re.compile(r"[。！？]")
EN_SENTENCE_END = re.compile(r"[.!?](?:\s|$)")

# Paragraph pattern (blank line separation)
PARAGRAPH_PATTERN = re.compile(r"\n\s*\n")

# Markdown patterns
H1_PATTERN = re.compile(r"^#\s", re.MULTILINE)
H2_PATTERN = re.compile(r"^##\s", re.MULTILINE)
H3_PATTERN = re.compile(r"^###\s", re.MULTILINE)
H4_PATTERN = re.compile(r"^####\s", re.MULTILINE)
LIST_PATTERN = re.compile(r"^[-*]\s", re.MULTILINE)
CODE_BLOCK_PATTERN = re.compile(r"```[\s\S]*?```")
LINK_PATTERN = re.compile(r"\[([^\]]+)\]\([^)]+\)")
IMAGE_PATTERN = re.compile(r"!\[")


class ContentMetrics:
    """Content metrics calculator."""

    def text_metrics(self, text: str, lang: str = "ja") -> TextMetrics:
        """
        Calculate text metrics.

        Args:
            text: Target text
            lang: Language ("ja" for Japanese support)

        Returns:
            TextMetrics: Character count, word count, paragraph count, sentence count

        Japanese support:
            - Japanese characters (hiragana, katakana, kanji) count as 1 word each
            - English words are counted normally
            - Total is used as word_count
        """
        char_count = len(text)

        if lang == "ja":
            # Count Japanese characters as individual words
            ja_chars = len(JA_PATTERN.findall(text))
            # Count English words
            en_words = len(EN_WORD_PATTERN.findall(text))
            word_count = ja_chars + en_words
        else:
            word_count = len(text.split())

        # Paragraph count: split by blank lines
        paragraphs = PARAGRAPH_PATTERN.split(text.strip())
        paragraph_count = len([p for p in paragraphs if p.strip()])
        if paragraph_count == 0 and text.strip():
            paragraph_count = 1

        # Sentence count
        if lang == "ja":
            ja_sentences = len(JA_SENTENCE_END.findall(text))
            en_sentences = len(EN_SENTENCE_END.findall(text))
            sentence_count = ja_sentences + en_sentences
        else:
            sentence_count = len(EN_SENTENCE_END.findall(text))

        if sentence_count == 0 and text.strip():
            sentence_count = 1

        return TextMetrics(
            char_count=char_count,
            word_count=word_count,
            paragraph_count=paragraph_count,
            sentence_count=sentence_count,
        )

    def markdown_metrics(self, content: str) -> MarkdownMetrics:
        """
        Calculate Markdown metrics.

        Returns:
            MarkdownMetrics: Heading counts, list count, code block count, link count, image count

        Patterns:
            - H1: ^#\\s
            - H2: ^##\\s
            - H3: ^###\\s
            - H4: ^####\\s
            - List: ^[-*]\\s
            - Code block: ``` pairs
            - Link: \\[text\\](url)
            - Image: !\\[
        """
        h1_count = len(H1_PATTERN.findall(content))
        h2_count = len(H2_PATTERN.findall(content))
        h3_count = len(H3_PATTERN.findall(content))
        h4_count = len(H4_PATTERN.findall(content))
        list_count = len(LIST_PATTERN.findall(content))
        code_block_count = len(CODE_BLOCK_PATTERN.findall(content))
        link_count = len(LINK_PATTERN.findall(content))
        image_count = len(IMAGE_PATTERN.findall(content))

        return MarkdownMetrics(
            h1_count=h1_count,
            h2_count=h2_count,
            h3_count=h3_count,
            h4_count=h4_count,
            list_count=list_count,
            code_block_count=code_block_count,
            link_count=link_count,
            image_count=image_count,
        )

    def keyword_density(
        self,
        text: str,
        keyword: str,
        lang: str = "ja",
    ) -> float:
        """
        Calculate keyword density (%).

        Args:
            text: Target text
            keyword: Search keyword
            lang: Language

        Returns:
            float: Keyword density (0.0 to 100.0)

        Formula:
            (keyword occurrences / total words) * 100
        """
        text_lower = text.lower()
        keyword_lower = keyword.lower()

        # Get word count
        metrics = self.text_metrics(text, lang)
        total_words = metrics.word_count

        if total_words == 0:
            return 0.0

        # Count keyword occurrences (case insensitive)
        keyword_count = text_lower.count(keyword_lower)

        return (keyword_count / total_words) * 100

    def compare_content(
        self,
        original: str,
        modified: str,
        lang: str = "ja",
    ) -> dict[str, float]:
        """
        Compare two content versions.

        Args:
            original: Original content
            modified: Modified content

        Returns:
            dict: Comparison metrics
                - word_diff: Word count difference
                - word_ratio: modified/original ratio
                - h2_diff: H2 section count difference
                - h3_diff: H3 section count difference

        Usage:
            - Step7b: Pre/post polishing comparison
            - Step9: Pre/post rewrite comparison
        """
        orig_text = self.text_metrics(original, lang)
        mod_text = self.text_metrics(modified, lang)

        orig_md = self.markdown_metrics(original)
        mod_md = self.markdown_metrics(modified)

        word_diff = mod_text.word_count - orig_text.word_count

        if orig_text.word_count > 0:
            word_ratio = mod_text.word_count / orig_text.word_count
        else:
            word_ratio = float(mod_text.word_count) if mod_text.word_count > 0 else 1.0

        h2_diff = mod_md.h2_count - orig_md.h2_count
        h3_diff = mod_md.h3_count - orig_md.h3_count

        return {
            "word_diff": float(word_diff),
            "word_ratio": word_ratio,
            "h2_diff": float(h2_diff),
            "h3_diff": float(h3_diff),
        }

    def estimate_reading_time(
        self,
        text: str,
        lang: str = "ja",
        wpm: int = 400,
    ) -> int:
        """
        Estimate reading time (minutes).

        Args:
            text: Target text
            lang: Language
            wpm: Words per minute (default 400 for Japanese)

        Returns:
            int: Estimated reading time (minutes, rounded up)
        """
        metrics = self.text_metrics(text, lang)

        if metrics.word_count == 0:
            return 0

        minutes = metrics.word_count / wpm

        return math.ceil(minutes)
