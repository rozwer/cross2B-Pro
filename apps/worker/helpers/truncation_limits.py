"""Centralized truncation and limit constants for worker activities.

Groups:
- PROMPT_*: Character limits for data sent to LLM prompts
- MAX_*: Item count limits for lists/arrays
- META_*/SEO_*/SLUG_*: SEO output constraints
"""

# --- Prompt construction limits (character counts) ---
PROMPT_EXCERPT_LIMIT = 200        # Source excerpts (step6, step7a, step11)
PROMPT_EXCERPT_MEDIUM = 500       # Medium excerpts (step4, step5, step6_5, step11)
PROMPT_ANALYSIS_LIMIT = 800       # Analysis summaries (step4)
PROMPT_CONTENT_LIMIT = 1000       # Content overview (step3b, step8)
PROMPT_RAW_OUTPUT_LIMIT = 2000    # raw_output fallback (step4, step6_5, step7a)
PROMPT_OUTLINE_LIMIT = 2000       # Outline data (step6_5)
PROMPT_META_CONTEXT_LIMIT = 2000  # Meta description generation context (step10, step11)
PROMPT_ARTICLE_LIMIT = 6000       # Article markdown preview (step11)
PROMPT_EXPANDED_LIMIT = 20000     # Full article for variation (step7a, step10)

# --- List item count limits ---
MAX_SOURCES_IN_PROMPT = 10        # Sources in prompt (step6, step6_5)
MAX_SOURCES_EXTENDED = 15         # Extended source list (step7a)
MAX_PATTERNS = 5                  # Human touch patterns (step4, step5, step6_5, step7a)
MAX_EPISODES = 3                  # Experience episodes (step4, step5, step6_5, step7a)
MAX_HOOKS = 5                     # Emotional hooks (step4, step5, step6_5, step7a)
MAX_SEARCH_QUERIES = 12           # Search queries (step5)
MAX_FALLBACK_QUERIES = 5          # Fallback queries (step5)
MAX_KEYWORDS_COOCCURRENCE = 50    # Co-occurrence keywords (step3b)
MAX_GAPS = 20                     # Differentiation gaps (step3b)
MAX_DATA_PLACEMENTS = 20          # Data placements (step6)
MAX_COMPETITORS = 10              # Competitor content items (step3b)

# --- SEO output constraints ---
META_DESCRIPTION_MAX = 160        # Meta description hard limit (step9)
META_DESCRIPTION_TRUNCATE = 155   # Truncation with "..." suffix
SEO_TITLE_MAX = 60                # SEO title limit (step12)
SLUG_MAX_LENGTH = 50              # URL slug limit (step12)
KEYWORD_DENSITY_MIN = 0.5         # Keyword density floor (step12)
KEYWORD_DENSITY_MAX = 2.5         # Keyword density ceiling (step12)
