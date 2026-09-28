from __future__ import annotations
import html
import re
import unicodedata
from functools import lru_cache
from typing import Iterable
POSITIVE_TERMS = {'amazing', 'attentive', 'awesome', 'beautiful', 'best', 'clean', 'clear', 'clearly', 'comfortable', 'cozy', 'delicious', 'excellent', 'exceptional', 'fast', 'fantastic', 'fresh', 'friendly', 'good', 'great', 'helpful', 'high quality', 'highly recommend', 'hospitality', 'impressed', 'love', 'loved', 'lovely', 'nice', 'no wait', 'not bad', 'outstanding', 'perfect', 'pleasant', 'polite', 'professional', 'quick service', 'reasonable', 'recommend', 'recommended', 'satisfied', 'served quickly', 'super', 'tasty', 'tender', 'welcoming', 'wonderful', 'worth it', 'worth the money', 'ausgezeichnet', 'aufmerksam', 'freundlich', 'gemütlich', 'gut', 'hervorragend', 'keine wartezeit', 'lecker', 'nicht schlecht', 'perfekt', 'professionell', 'sauber', 'schnell bedient', 'schön', 'super', 'verständlich', 'willkommen', 'zufrieden', 'جيد', 'جميل', 'رائع', 'لذيذ', 'ليس سيئا', 'ليس سيئاً', 'ممتاز', 'نظيف', 'واضح', 'ودود', 'محترم', 'مريح', 'طازج', 'أنصح'}
NEGATIVE_TERMS = {'awful', 'bad', 'bland', 'cold food', 'confusing', 'declined', 'dirty', 'disappointing', 'disappointed', 'difficult', 'dry', 'expensive', 'horrible', 'ignored', 'inattentive', 'long wait', 'not clean', 'not delicious', 'not fresh', 'not friendly', 'not good', 'overpriced', 'poor', 'poor quality', 'problem', 'problems', 'rude', 'slow', 'slow service', 'tasteless', 'terrible', 'tough', 'uncomfortable', 'unfriendly', 'unpleasant', 'unprofessional', 'quality declined', 'unappealing', 'uninspired service', 'unclear', 'speaks quietly', 'difficult parking', 'worst', 'worse', 'enttäuschend', 'geschmacklos', 'langsam', 'nicht freundlich', 'nicht frisch', 'nicht gut', 'nicht lecker', 'schlecht', 'schmutzig', 'teuer', 'unaufmerksam', 'unfreundlich', 'ungemütlich', 'unprofessionell', 'qualität nachgelassen', 'unappetitlich', 'uninspirierter service', 'unklar', 'spricht leise', 'schwierige parksituation', 'schlechte qualität', 'problem', 'سيئ', 'سيء', 'غالي', 'بطيء', 'بارد', 'متسخ', 'غير احترافي', 'غير طازج', 'غير مريح', 'غير نظيف', 'مشكلة', 'مشاكل', 'الجودة تراجعت', 'غير شهي', 'الخدمة غير ملهمة', 'غير واضح', 'يتحدث بصوت منخفض', 'مواقف صعبة', 'جودة سيئة'}
NEGATIVE_TERMS.update({"nachgelassen", "تراجعت", "annoying", "burnt", "unclearly", "didn't taste good", "didn t taste good", "did not taste good", "isn't tasty", "isn t tasty", "is not tasty", "wasn't good", "wasn t good", "not particularly tasty", "waited too long", "waited a very long time", "wait a very long time", "very long wait", "sehr lange gewartet", "lange wartezeit", "undeutlich", "ohne geschmack", "بدون طعم", "تأخير", "انتظار طويل", "غير جيد"})
NEGATIVE_TERMS.update({
    # Food safety, quality, and preparation.
    "disgusting", "spoiled", "rotten", "stale", "rancid", "raw",
    "undercooked", "overcooked", "charred", "burned", "bitter", "greasy",
    "hair in food", "hair in it", "flies", "food poisoning", "made us sick",
    "nausea", "smelled bad", "smelled disgusting", "old oil", "bone fragments",
    "tendons", "not edible", "inedible", "not enjoyable", "didn't enjoy",
    "didn t enjoy", "do not like", "don't like", "don t like", "didn't like",
    "didn t like", "not tasty", "no taste", "no flavor", "no flavour",
    "not as good", "isn't as good", "isn t as good", "nothing was right",
    "should not be offered", "shouldn't be offered", "shouldn t be offered",
    "no longer be offered", "verdorben", "vergammelt", "eklig", "ekelhaft",
    "abgestanden", "roh", "nicht durchgegart", "verkohlt", "angebrannt",
    "fettig", "haare im essen", "altes öl", "nicht gefallen",
    # Availability, accuracy, service, and hospitality.
    "empty", "unavailable", "not available", "not refilled", "never refilled",
    "hardly ever refilled", "wrong order", "wrong drink", "wrong side",
    "wrong sides", "forgotten", "forgot", "missing", "never received",
    "not received", "didn't receive", "didn t receive", "not cleared",
    "never came", "no waiter", "no one asked", "not offered", "yelled",
    "shouted", "disrespectful", "insulting", "insulted", "sexist", "racist",
    "harassed", "harasses", "not polite", "didn't greet", "didn t greet",
    "asked to leave", "refused", "forced", "cancelled", "canceled",
    "pathetic excuse", "no compensation", "kept waiting", "took forever",
    "takes forever", "unbearable", "overwhelmed", "rücksichtslos",
    "respektlos", "beleidigt", "ignoriert", "nicht angeboten", "vergessen",
    "falsches getränk", "falsche bestellung", "abgesagt",
    # Value, environment, and strong outcome language.
    "rip off", "rip-off", "overcharged", "charged twice", "incorrect payment",
    "cash only", "wouldn't recommend", "wouldn t recommend", "not recommended",
    "cannot recommend", "can't recommend", "can t recommend", "never again",
    "disaster", "unacceptable", "outrage", "outrageous", "absolutely zero",
    "throw up", "kleine portion", "zu klein", "nicht satt", "abzocke",
    "katastrophe", "inakzeptabel", "nie wieder", "keine empfehlung",
    "not nice", "doesn't resemble", "does not resemble", "didn't resemble",
    "did not resemble", "too high", "far too high", "ridiculously high",
    "payment was incorrect", "rip me off", "charged me twice", "also charged me",
    "doesn't accept card", "does not accept card", "not accept card payments",
    "limited", "very limited",
})

@lru_cache(maxsize=4096)
def clean_text(value: str | None) -> str:
    """
    Clean review text while preserving useful
    sentence / paragraph boundaries.

    Example input:

        Good food.<br>Great service.

    becomes:

        Good food.
        Great service.
    """
    if not value:
        return ''
    text = html.unescape(str(value))
    text = re.sub('<br\\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub('</p\\s*>', '\n', text, flags=re.IGNORECASE)
    text = re.sub('<[^>]+>', ' ', text)
    text = unicodedata.normalize('NFKC', text)
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub('[ \\t\\f\\v]+', ' ', text)
    text = re.sub(' *\\n *', '\n', text)
    text = re.sub('\\n{2,}', '\n', text)
    return text.strip()

@lru_cache(maxsize=8192)
def normalize_text(value: str | None) -> str:
    """
    Normalize text for matching.

    Keeps letters/numbers from Unicode languages
    including:

        English
        German
        Arabic

    while removing punctuation differences.
    """
    text = clean_text(value).lower()
    text = re.sub('[^\\w\\s]+', ' ', text, flags=re.UNICODE)
    text = re.sub('\\s+', ' ', text)
    return text.strip()

def get_analysis_text(review: dict) -> str:
    """
    Return one primary version of the review for analysis.

    Priority:

        1. Google's translated English text
        2. Original text

    This gives the analysis system a mostly common
    language while preserving original text elsewhere.
    """
    translated = clean_text(review.get('text_translated'))
    original = clean_text(review.get('text_original'))
    return translated or original

def get_text_variants(review: dict) -> list[str]:
    """
    Return every useful text version of one review.

    Usually:

        translated text
        original text

    The two versions are NOT automatically added together
    when counting mentions because that would duplicate
    the same semantic review.

    Dish/topic modules decide how the variants should
    be compared.
    """
    values: list[str] = []
    translated = clean_text(review.get('text_translated'))
    original = clean_text(review.get('text_original'))
    for value in [translated, original]:
        if value and value not in values:
            values.append(value)
    return values


def get_named_text_variants(review: dict) -> list[tuple[str, str]]:
    """Return unique review text variants with an auditable source label."""
    values: list[tuple[str, str]] = []
    seen = set()
    for name, value in (
        ("translated", clean_text(review.get("text_translated"))),
        ("original", clean_text(review.get("text_original"))),
    ):
        if value and value not in seen:
            seen.add(value)
            values.append((name, value))
    return values

def _normalized_aliases(aliases: Iterable[str]) -> list[str]:
    """
    Normalize aliases and remove duplicates.

    Longest aliases are returned first so:

        slow service

    is considered before:

        service
    """
    seen = set()
    result = []
    for alias in aliases:
        normalized = normalize_text(alias)
        if not normalized:
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    result.sort(key=lambda alias: (len(alias), len(alias.split())), reverse=True)
    return result


@lru_cache(maxsize=4)
def _normalized_sentiment_terms(sentiment: str) -> tuple[str, ...]:
    terms = POSITIVE_TERMS if sentiment == "positive" else NEGATIVE_TERMS
    return tuple(_normalized_aliases(terms))

def _phrase_pattern(normalized_phrase: str) -> str:
    """
    Build a Unicode-safe phrase pattern.

    Example:

        slow service

    becomes a pattern allowing one or more
    whitespace characters between the words.
    """
    escaped = re.escape(normalized_phrase)
    escaped = escaped.replace('\\ ', '\\s+')
    return f'(?<!\\w){escaped}(?!\\w)'

def _find_phrase_matches(text: str, phrases: Iterable[str]) -> list[dict]:
    """
    Find all candidate phrase matches.
    """
    normalized_text = normalize_text(text)
    if not normalized_text:
        return []
    candidates = []
    for phrase in _normalized_aliases(phrases):
        pattern = _phrase_pattern(phrase)
        for match in re.finditer(pattern, normalized_text, flags=re.UNICODE):
            candidates.append({'phrase': phrase, 'start': match.start(), 'end': match.end(), 'length': match.end() - match.start(), 'word_count': len(phrase.split())})
    candidates.sort(key=lambda match: (match['length'], match['word_count'], -match['start']), reverse=True)
    return candidates

def _matches_overlap(first: dict, second: dict) -> bool:
    """
    Check whether two phrase matches use
    overlapping characters.
    """
    return not (first['end'] <= second['start'] or first['start'] >= second['end'])

def _resolve_phrase_matches(candidates: list[dict]) -> list[dict]:
    """
    Keep longest / most specific phrases and prevent
    overlapping aliases from being counted twice.

    Example:

        "slow service"

    aliases:

        slow service
        service

    result:

        one mention
    """
    accepted = []
    for candidate in candidates:
        overlaps = any((_matches_overlap(candidate, existing) for existing in accepted))
        if overlaps:
            continue
        accepted.append(candidate)
    accepted.sort(key=lambda match: (match['start'], match['end']))
    return accepted

def count_alias_occurrences(text: str, aliases: Iterable[str]) -> int:
    """
    Count non-overlapping alias mentions in one text.

    Important:

    overlapping aliases are not counted twice.

    Example:

        aliases:
            service
            slow service

        text:
            The slow service was disappointing.

        result:
            1 mention
    """
    candidates = _find_phrase_matches(text, aliases)
    accepted = _resolve_phrase_matches(candidates)
    return len(accepted)

def count_alias_occurrences_in_variants(texts: list[str], aliases: Iterable[str]) -> int:
    """
    Count mentions across original/translated variants.

    We use the maximum result rather than adding them.

    Reason:

    German original:
        Das Essen war lecker.

    English translation:
        The food was delicious.

    represents ONE review concept, not two reviews.
    """
    counts = [count_alias_occurrences(text, aliases) for text in texts]
    if not counts:
        return 0
    return max(counts)

def split_sentences(text: str) -> list[str]:
    """
    Split review text into sentence-like units.

    Handles:
        punctuation
        HTML-converted line breaks
    """
    cleaned = clean_text(text)
    if not cleaned:
        return []
    sentences = re.split('(?<=[.!?])\\s+|\\n+', cleaned)
    return [sentence.strip() for sentence in sentences if sentence.strip()]

def split_clauses(text: str) -> list[str]:
    """Split contrast clauses so one aspect does not borrow another's sentiment."""
    clauses = re.split('\\s*(?:[;:]|\\bbut\\b|\\bhowever\\b|\\bwhile\\b|\\baber\\b|\\bjedoch\\b|لكن|ولكن|بينما)\\s*', clean_text(text), flags=re.IGNORECASE)
    return [clause.strip() for clause in clauses if clause.strip()]


def phrase_matches(text: str, phrases: Iterable[str]) -> list[dict]:
    """Public, non-overlapping phrase matches for audit and analyzers."""
    return _resolve_phrase_matches(_find_phrase_matches(text, phrases))

def _sentiment_matches(text: str) -> list[dict]:
    """
    Detect positive and negative sentiment phrases.

    Positive and negative phrases are evaluated together
    so overlapping expressions are handled correctly.

    Example:

        "not good"

    should count as NEGATIVE only.

    It should not also count:
        "good"
    """
    normalized_text = normalize_text(text)
    if not normalized_text:
        return []
    candidates = []
    for sentiment in ('positive', 'negative'):
        for term in _normalized_sentiment_terms(sentiment):
            pattern = _phrase_pattern(term)
            for match in re.finditer(pattern, normalized_text, flags=re.UNICODE):
                candidates.append({'sentiment': sentiment, 'term': term, 'start': match.start(), 'end': match.end(), 'length': match.end() - match.start(), 'word_count': len(term.split())})
    candidates.sort(key=lambda match: (match['length'], match['word_count'], -match['start']), reverse=True)
    accepted = []
    for candidate in candidates:
        overlaps = any((_matches_overlap(candidate, existing) for existing in accepted))
        if overlaps:
            continue
        accepted.append(candidate)
    return accepted

def sentiment_counts(text: str) -> tuple[int, int]:
    """
    Return:

        positive sentiment matches
        negative sentiment matches
    """
    matches = _sentiment_matches(text)
    positive = sum((1 for match in matches if match['sentiment'] == 'positive'))
    negative = sum((1 for match in matches if match['sentiment'] == 'negative'))
    return (positive, negative)

def sentiment_score(text: str) -> int:
    """
    Return a transparent rule-based sentiment score.

    Positive term:
        +1

    Negative term:
        -1
    """
    positive, negative = sentiment_counts(text)
    return positive - negative


def analyze_mention_sentiment(
    text: str,
    aliases: Iterable[str],
    alias_polarities: dict[str, str] | None = None,
) -> dict:
    """Explain sentiment in clauses that contain the matched subject.

    Explicit alias polarity is counted first; remaining local sentiment terms
    are then counted. Longest-phrase matching handles simple negation such as
    ``not good`` without also counting ``good``.
    """
    alias_list = list(aliases)
    polarity = {
        normalize_text(alias): value
        for alias, value in (alias_polarities or {}).items()
        if value in {"positive", "negative", "neutral"}
    }
    evidence = []
    explicit_positive = 0
    explicit_negative = 0
    for sentence in split_sentences(text):
        for clause in split_clauses(sentence):
            matches = phrase_matches(clause, alias_list)
            if not matches:
                continue
            local_matches = _sentiment_matches(clause)
            positives = {m["term"] for m in local_matches if m["sentiment"] == "positive"}
            negatives = {m["term"] for m in local_matches if m["sentiment"] == "negative"}
            normalized_clause = normalize_text(clause)
            if any(match["phrase"] in {"wait", "waiting", "waited", "wartezeit", "warten", "gewartet", "انتظار", "انتظرنا"} for match in matches) and re.search(
                r"\b(?:\d+|one|two|three|half|an)\s+(?:minutes?|hours?)\b",
                normalized_clause,
            ):
                negatives.add("explicit wait duration")
            for match in matches:
                explicit = polarity.get(match["phrase"], "neutral")
                if explicit == "positive":
                    positives.add(match["phrase"])
                    explicit_positive += 1
                elif explicit == "negative":
                    negatives.add(match["phrase"])
                    explicit_negative += 1
            evidence.append(
                {
                    "matched_clause": clause,
                    "matched_aliases": [m["phrase"] for m in matches],
                    "positive_terms": sorted(positives),
                    "negative_terms": sorted(negatives),
                }
            )
    positive_count = sum(len(row["positive_terms"]) for row in evidence)
    negative_count = sum(len(row["negative_terms"]) for row in evidence)
    sentiment = "neutral"
    if explicit_positive > explicit_negative:
        sentiment = "positive"
    elif explicit_negative > explicit_positive:
        sentiment = "negative"
    elif positive_count > negative_count:
        sentiment = "positive"
    elif negative_count > positive_count:
        sentiment = "negative"
    return {"sentiment": sentiment, "evidence": evidence}

def classify_mention_sentiment(text: str, aliases: Iterable[str], review_rating: float | int | None) -> str:
    """Classify sentiment only in clauses that mention the topic or dish."""
    del review_rating
    return analyze_mention_sentiment(text, aliases)["sentiment"]
