"""
NAUB Chatbot NLP Engine
------------------------
Implements the TF-IDF + Cosine Similarity matching pipeline described in
Chapter 3 of the project (Sections 3.6, Phases 1-5), plus a gibberish /
nonsense-input detector that runs before any matching is attempted.
"""
import re
import string
from django.conf import settings

try:
    import nltk
    from nltk.corpus import stopwords
    from nltk.stem import PorterStemmer
    from nltk.tokenize import word_tokenize
    _NLTK_OK = True
except Exception:
    _NLTK_OK = False

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# A small built-in fallback stopword list, used if NLTK data isn't downloaded
# (keeps the engine functional even without internet access at runtime).
_FALLBACK_STOPWORDS = set("""
a an the is are was were be been being am do does did doing have has had
having i you he she it we they me him her us them my your his its our their
this that these those of in on at to for with from by as it's i'm you're
he's she's we're they're and or but if then so because while can could
should would will shall may might must about into over under again further
here there when where why how all any both each few more most other some
such no nor not only own same than too very s t just don now
""".split())

_STEMMER = PorterStemmer() if _NLTK_OK else None


def _ensure_nltk_data():
    if not _NLTK_OK:
        return False
    for pkg, path in [("punkt", "tokenizers/punkt"), ("punkt_tab", "tokenizers/punkt_tab"),
                       ("stopwords", "corpora/stopwords")]:
        try:
            nltk.data.find(path)
        except LookupError:
            try:
                nltk.download(pkg, quiet=True)
            except Exception:
                pass
    return True


_ensure_nltk_data()


def get_stopwords():
    if _NLTK_OK:
        try:
            return set(stopwords.words("english"))
        except Exception:
            pass
    return _FALLBACK_STOPWORDS


_STOPWORDS = get_stopwords()


# ---------------------------------------------------------------------------
# Synonym / acronym normalization
# ---------------------------------------------------------------------------
# Maps common abbreviations, acronyms, and alternate phrasings used by NAUB
# students to a canonical expanded form. This runs BEFORE tokenization so that
# e.g. "Dean of FCOM" and "Dean of the faculty of computing" both reduce to
# the same underlying tokens and match the same knowledge base entry.
#
# Keys are matched as whole words/phrases (case-insensitive). Add new entries
# here whenever a new acronym or alternate phrasing surfaces in real usage.
SYNONYM_MAP = {
    # Faculty acronyms / alternate names
    "fcom": "faculty of computing",
    "faculty of comp sci": "faculty of computing",
    "computing faculty": "faculty of computing",
    "fss": "faculty of social sciences",
    "faculty of socsci": "faculty of social sciences",
    "fms": "faculty of management sciences",
    "management faculty": "faculty of management sciences",
    "foh": "faculty of humanities",
    "humanities faculty": "faculty of humanities",
    "fsc": "faculty of science",
    "science faculty": "faculty of science",
    "fol": "faculty of law",
    "law faculty": "faculty of law",
    # Common role/title abbreviations
    "vc": "vice chancellor",
    "hod": "head of department",
    "reg": "registrar",
    "dvc": "deputy vice chancellor",
    # Common institutional abbreviations
    "sug": "student union government",
    "gst": "general studies",
    "utme": "jamb",
    "de": "direct entry",
    "nysc": "national youth service corps",
    "ict": "information communication technology",
    # Frequent shorthand
    "uni": "university",
    "naub": "nigerian army university biu",
    "dept": "department",
    "acct": "accounting",
    "cs": "computer science",
}

# Sort longer phrases first so multi-word keys are replaced before any
# single-word substrings inside them could be.
_SYNONYM_KEYS_SORTED = sorted(SYNONYM_MAP.keys(), key=len, reverse=True)


def expand_synonyms(text: str) -> str:
    """Replace known acronyms/abbreviations/alternate phrasings with their
    canonical expanded form using whole-word/phrase boundaries."""
    for key in _SYNONYM_KEYS_SORTED:
        pattern = r"\b" + re.escape(key) + r"\b"
        text = re.sub(pattern, SYNONYM_MAP[key], text, flags=re.IGNORECASE)
    return text


def preprocess_text(text: str) -> str:
    """
    Phase 1 - Text Pre-processing (Chapter 3, Section 3.6):
    (i) lowercase, (ii) tokenize, (iii) stop-word removal, (iv) stemming.
    """
    text = text.lower().strip()
    text = expand_synonyms(text)
    text = re.sub(r"[^\w\s']", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    if _NLTK_OK:
        try:
            tokens = word_tokenize(text)
        except Exception:
            tokens = text.split()
    else:
        tokens = text.split()

    cleaned = []
    for tok in tokens:
        if tok in _STOPWORDS or tok in string.punctuation or not tok.strip():
            continue
        if _STEMMER:
            try:
                tok = _STEMMER.stem(tok)
            except Exception:
                pass
        cleaned.append(tok)
    return " ".join(cleaned)


# ---------------------------------------------------------------------------
# Gibberish detection
# ---------------------------------------------------------------------------
_VOWELS = set("aeiou")


def is_gibberish(raw_text: str) -> bool:
    """
    Heuristic gibberish / nonsense detector that runs BEFORE TF-IDF matching.
    Flags input as gibberish if any of these hold:
      - Empty after stripping, or shorter than 2 characters
      - No vowels at all in a sufficiently long alphabetic string
      - Extremely low vowel ratio (keyboard mashing like "sdkjfh skjdf")
      - A single character repeated excessively ("aaaaaaaa", "kkkkkk")
      - No recognizable English word-like tokens (all tokens are long
        consonant clusters with no vowel breaks)
    """
    text = raw_text.strip()
    if len(text) < 2:
        return True

    letters_only = re.sub(r"[^a-zA-Z]", "", text)
    if len(letters_only) == 0:
        # Pure numbers/symbols/emojis with no letters - treat as gibberish
        # unless it's short (could be e.g. "ok" handled above) -- numbers like
        # "100 level" are handled because letters_only would include 'level'.
        return True

    lower = letters_only.lower()

    # Excessive single-character repetition, e.g. "aaaaaa", "kkkkkkkk"
    if re.fullmatch(r"(.)\1{3,}", lower):
        return True

    vowel_count = sum(1 for c in lower if c in _VOWELS)
    vowel_ratio = vowel_count / len(lower)

    if len(lower) >= 5 and vowel_ratio < 0.12:
        return True

    # Check each "word" token for unrealistic consonant runs (keyboard mash)
    tokens = re.findall(r"[a-zA-Z']+", text)
    if not tokens:
        return True

    suspicious = 0
    for tok in tokens:
        tok_l = tok.lower()
        if len(tok_l) >= 4:
            max_consonant_run = 0
            run = 0
            for c in tok_l:
                if c not in _VOWELS and c.isalpha():
                    run += 1
                    max_consonant_run = max(max_consonant_run, run)
                else:
                    run = 0
            if max_consonant_run >= 5:
                suspicious += 1

    if tokens and (suspicious / len(tokens)) > 0.5:
        return True

    return False


# ---------------------------------------------------------------------------
# TF-IDF + Cosine Similarity Matcher
# ---------------------------------------------------------------------------
class IntentMatcher:
    """
    Wraps Phases 2-4 of the algorithm: TF-IDF vectorization of the knowledge
    base + the incoming query, and Cosine Similarity matching against the
    threshold defined in settings.CHATBOT_SIMILARITY_THRESHOLD.
    """

    def __init__(self, kb_entries):
        """
        kb_entries: queryset/list of KnowledgeBaseEntry (active only), each
        with .intent_id, .question_list(), .answer
        """
        self.kb_entries = list(kb_entries)
        self.vectorizer = None
        self.kb_vectors = None
        self.flat_questions = []
        self.question_to_entry_idx = []
        self._build()

    def _build(self):
        corpus = []
        for idx, entry in enumerate(self.kb_entries):
            for q in entry.question_list():
                processed = preprocess_text(q)
                if processed:
                    corpus.append(processed)
                    self.flat_questions.append(q)
                    self.question_to_entry_idx.append(idx)

        if not corpus:
            return

        self.vectorizer = TfidfVectorizer()
        self.kb_vectors = self.vectorizer.fit_transform(corpus)

    def match(self, raw_query: str, top_n=4):
        """
        Returns dict: {status, entry, answer, similarity_score, candidates}
        status in {"answered", "clarification", "unanswered"}

        - "answered": a single confident match was found (score above threshold
          AND clearly ahead of the next-best distinct intent).
        - "clarification": multiple distinct intents scored close together
          above the threshold -- too ambiguous to guess, so candidate
          questions are returned for the user to pick from instead of risking
          a wrong answer.
        - "unanswered": nothing scored high enough to be worth showing.
        """
        threshold = getattr(settings, "CHATBOT_SIMILARITY_THRESHOLD", 0.35)
        margin = getattr(settings, "CHATBOT_CLARIFICATION_MARGIN", 0.12)

        empty = {"status": "unanswered", "entry": None, "answer": None,
                 "similarity_score": 0.0, "candidates": []}

        if self.vectorizer is None or self.kb_vectors is None:
            return empty

        processed_query = preprocess_text(raw_query)
        if not processed_query:
            return empty

        query_vector = self.vectorizer.transform([processed_query])
        similarities = cosine_similarity(query_vector, self.kb_vectors)[0]

        # Collapse to the best score per distinct KB entry (an entry can have
        # many training questions, we only care about its best-scoring one).
        best_per_entry = {}  # entry_idx -> (score, flat_question_idx)
        for flat_idx, score in enumerate(similarities):
            entry_idx = self.question_to_entry_idx[flat_idx]
            if entry_idx not in best_per_entry or score > best_per_entry[entry_idx][0]:
                best_per_entry[entry_idx] = (float(score), flat_idx)

        ranked = sorted(best_per_entry.items(), key=lambda kv: kv[1][0], reverse=True)

        if not ranked or ranked[0][1][0] < threshold:
            top_score = ranked[0][1][0] if ranked else 0.0
            return {"status": "unanswered", "entry": None, "answer": None,
                    "similarity_score": round(top_score, 4), "candidates": []}

        best_entry_idx, (best_score, best_flat_idx) = ranked[0]
        second_score = ranked[1][1][0] if len(ranked) > 1 else 0.0

        if (best_score - second_score) >= margin:
            entry = self.kb_entries[best_entry_idx]
            return {
                "status": "answered",
                "entry": entry,
                "answer": entry.answer,
                "similarity_score": round(best_score, 4),
                "candidates": [],
            }

        # Ambiguous: gather the top-N distinct-intent candidates above threshold
        # (or close enough to be plausible) to present as clickable options.
        candidates = []
        for entry_idx, (score, flat_idx) in ranked[:top_n]:
            if score < (threshold - 0.05):
                continue
            entry = self.kb_entries[entry_idx]
            candidates.append({
                "intent_id": entry.intent_id,
                "question": self.flat_questions[flat_idx],
                "score": round(score, 4),
            })

        if len(candidates) < 2:
            # Not actually ambiguous after filtering -- fall back to the best answer.
            entry = self.kb_entries[best_entry_idx]
            return {
                "status": "answered",
                "entry": entry,
                "answer": entry.answer,
                "similarity_score": round(best_score, 4),
                "candidates": [],
            }

        return {
            "status": "clarification",
            "entry": None,
            "answer": None,
            "similarity_score": round(best_score, 4),
            "candidates": candidates,
        }


_matcher_cache = {"matcher": None, "version": None}


def get_matcher(force_rebuild=False):
    """
    Returns a cached IntentMatcher, rebuilding it whenever the knowledge base
    has changed (tracked via a simple version counter based on row count +
    last updated timestamp), or when an admin saves a new/edited entry.
    """
    from chatbot.models import KnowledgeBaseEntry

    qs = KnowledgeBaseEntry.objects.filter(is_active=True).order_by("id")
    latest = qs.order_by("-updated_at").first()
    version = (qs.count(), latest.updated_at.isoformat() if latest else None)

    if force_rebuild or _matcher_cache["matcher"] is None or _matcher_cache["version"] != version:
        _matcher_cache["matcher"] = IntentMatcher(qs)
        _matcher_cache["version"] = version

    return _matcher_cache["matcher"]
