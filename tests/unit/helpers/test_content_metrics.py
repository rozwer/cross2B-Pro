"""Tests for ContentMetrics class."""

import pytest

from apps.worker.helpers import ContentMetrics


class TestTextMetrics:
    """text_metrics tests."""

    def test_japanese_text(self):
        """Japanese text."""
        metrics = ContentMetrics()
        result = metrics.text_metrics("これはテストです。", lang="ja")

        # 9 chars total (8 Japanese + 1 period)
        assert result.char_count == 9
        # Japanese characters count as 1 word each (8 Japanese chars)
        assert result.word_count == 8

    def test_english_text(self):
        """English text."""
        metrics = ContentMetrics()
        result = metrics.text_metrics("This is a test.", lang="en")

        assert result.word_count == 4

    def test_mixed_text(self):
        """Mixed Japanese/English text."""
        metrics = ContentMetrics()
        result = metrics.text_metrics("SEO対策について解説", lang="ja")

        # SEO (1 word) + 8 Japanese chars = 9
        assert result.word_count == 9

    def test_paragraph_count(self):
        """Paragraph count."""
        metrics = ContentMetrics()
        content = "段落1\n\n段落2\n\n段落3"
        result = metrics.text_metrics(content)

        assert result.paragraph_count == 3

    def test_paragraph_count_single(self):
        """Single paragraph."""
        metrics = ContentMetrics()
        content = "これは一つの段落です"
        result = metrics.text_metrics(content)

        assert result.paragraph_count == 1

    def test_sentence_count_japanese(self):
        """Sentence count (Japanese)."""
        metrics = ContentMetrics()
        content = "文1です。文2です。文3です。"
        result = metrics.text_metrics(content)

        assert result.sentence_count == 3

    def test_sentence_count_english(self):
        """Sentence count (English)."""
        metrics = ContentMetrics()
        content = "Sentence one. Sentence two! Sentence three?"
        result = metrics.text_metrics(content, lang="en")

        assert result.sentence_count == 3

    def test_empty_text(self):
        """Empty text."""
        metrics = ContentMetrics()
        result = metrics.text_metrics("")

        assert result.char_count == 0
        assert result.word_count == 0
        assert result.paragraph_count == 0
        assert result.sentence_count == 0


class TestMarkdownMetrics:
    """markdown_metrics tests."""

    def test_heading_counts(self):
        """Heading counts."""
        metrics = ContentMetrics()
        content = """
# Title
## Section 1
### Subsection 1.1
## Section 2
### Subsection 2.1
#### Deep section
"""
        result = metrics.markdown_metrics(content)

        assert result.h1_count == 1
        assert result.h2_count == 2
        assert result.h3_count == 2
        assert result.h4_count == 1

    def test_list_count(self):
        """List count."""
        metrics = ContentMetrics()
        content = """
- item 1
- item 2
* item 3
"""
        result = metrics.markdown_metrics(content)

        assert result.list_count == 3

    def test_code_block_count(self):
        """Code block count."""
        metrics = ContentMetrics()
        content = """
```python
code here
```

```
more code
```
"""
        result = metrics.markdown_metrics(content)

        assert result.code_block_count == 2

    def test_link_count(self):
        """Link count."""
        metrics = ContentMetrics()
        content = "[link1](url1) and [link2](url2)"
        result = metrics.markdown_metrics(content)

        assert result.link_count == 2

    def test_image_count(self):
        """Image count."""
        metrics = ContentMetrics()
        content = "![alt1](img1.png) and ![alt2](img2.png)"
        result = metrics.markdown_metrics(content)

        assert result.image_count == 2

    def test_empty_content(self):
        """Empty content."""
        metrics = ContentMetrics()
        result = metrics.markdown_metrics("")

        assert result.h1_count == 0
        assert result.h2_count == 0
        assert result.list_count == 0


class TestKeywordDensity:
    """keyword_density tests."""

    def test_basic_density(self):
        """Basic density calculation."""
        metrics = ContentMetrics()
        # 10 words, 1 occurrence = 10%
        content = "SEO word word word word word word word word word"
        density = metrics.keyword_density(content, "SEO", lang="en")

        assert 9.0 <= density <= 11.0  # ~10%

    def test_zero_density(self):
        """No keyword."""
        metrics = ContentMetrics()
        content = "no keyword here"
        density = metrics.keyword_density(content, "SEO", lang="en")

        assert density == 0.0

    def test_case_insensitive(self):
        """Case insensitive."""
        metrics = ContentMetrics()
        content = "seo SEO Seo"
        density = metrics.keyword_density(content, "SEO", lang="en")

        assert density > 0

    def test_empty_text(self):
        """Empty text returns 0."""
        metrics = ContentMetrics()
        density = metrics.keyword_density("", "SEO")

        assert density == 0.0


class TestCompareContent:
    """compare_content tests."""

    def test_word_diff(self):
        """Word diff."""
        metrics = ContentMetrics()
        original = "one two three"
        modified = "one two three four five"
        result = metrics.compare_content(original, modified, lang="en")

        assert result["word_diff"] == 2

    def test_word_ratio(self):
        """Word ratio."""
        metrics = ContentMetrics()
        original = "one two"
        modified = "one two three four"
        result = metrics.compare_content(original, modified, lang="en")

        assert result["word_ratio"] == 2.0

    def test_h2_diff(self):
        """H2 section diff."""
        metrics = ContentMetrics()
        original = "## Section 1"
        modified = "## Section 1\n## Section 2"
        result = metrics.compare_content(original, modified)

        assert result["h2_diff"] == 1

    def test_h3_diff(self):
        """H3 section diff."""
        metrics = ContentMetrics()
        original = "### Sub 1"
        modified = "### Sub 1\n### Sub 2\n### Sub 3"
        result = metrics.compare_content(original, modified)

        assert result["h3_diff"] == 2

    def test_empty_original(self):
        """Empty original."""
        metrics = ContentMetrics()
        result = metrics.compare_content("", "some content", lang="en")

        assert result["word_ratio"] > 0


class TestEstimateReadingTime:
    """estimate_reading_time tests."""

    def test_short_text(self):
        """Short text."""
        metrics = ContentMetrics()
        # 400 Japanese chars = 1 minute at 400 wpm
        text = "あ" * 400
        time_min = metrics.estimate_reading_time(text, lang="ja", wpm=400)

        assert time_min == 1

    def test_longer_text(self):
        """Longer text."""
        metrics = ContentMetrics()
        # 800 Japanese chars = 2 minutes at 400 wpm
        text = "あ" * 800
        time_min = metrics.estimate_reading_time(text, lang="ja", wpm=400)

        assert time_min == 2

    def test_rounds_up(self):
        """Rounds up partial minutes."""
        metrics = ContentMetrics()
        # 401 chars at 400 wpm = 1.0025 min -> rounds to 2
        text = "あ" * 401
        time_min = metrics.estimate_reading_time(text, lang="ja", wpm=400)

        assert time_min == 2

    def test_empty_text(self):
        """Empty text."""
        metrics = ContentMetrics()
        time_min = metrics.estimate_reading_time("")

        assert time_min == 0
