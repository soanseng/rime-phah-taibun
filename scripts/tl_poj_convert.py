"""TL <-> POJ romanization conversion utility.

Converts between TL (Tai-lo) and POJ (Pe-oe-ji) romanization systems
for Taiwanese Hokkien.
"""

import re
import unicodedata

COMBINING_TONE_TO_NUMBER = {
    "\u0301": "2",  # acute accent
    "\u0300": "3",  # grave accent
    "\u0302": "5",  # circumflex
    "\u0304": "7",  # macron
    "\u030d": "8",  # vertical line above
    "\u030b": "9",  # double acute accent
    "\u0306": "9",  # breve
}


def tl_to_poj(tl_text: str) -> str:
    """Convert TL romanization to POJ.

    Args:
        tl_text: Text in TL romanization

    Returns:
        Text converted to POJ romanization
    """
    if not tl_text:
        return tl_text
    result = tl_text
    # Order matters: longer patterns first to avoid partial matches
    result = result.replace("tsh", "chh")
    result = result.replace("ts", "ch")
    result = re.sub(r"ing\b", "eng", result)
    result = re.sub(r"ik\b", "ek", result)
    result = result.replace("ua", "oa")
    result = result.replace("ue", "oe")
    return result


def poj_diacritics_to_tone_numbers(text: str) -> str:
    """Convert POJ Unicode diacritics to syllable-final tone numbers.

    Args:
        text: Text with POJ diacritics (e.g. â, á, à, ā, a̍)

    Returns:
        Text with diacritics converted to tone numbers
    """
    if not text:
        return text

    parts = re.split(r"([-\s]+)", text)
    normalized_parts = []
    for part in parts:
        if not part or re.fullmatch(r"[-\s]+", part):
            normalized_parts.append(part)
            continue

        decomposed = unicodedata.normalize("NFD", part)
        tone = ""
        chars = []
        for char in decomposed:
            if char in COMBINING_TONE_TO_NUMBER:
                tone = COMBINING_TONE_TO_NUMBER[char]
            else:
                chars.append(char)

        base = unicodedata.normalize("NFC", "".join(chars)).replace("\u0131", "i")
        if tone and not re.search(r"[1-9]$", base):
            base += tone
        normalized_parts.append(base)

    return "".join(normalized_parts)


def poj_to_tl(poj_text: str) -> str:
    """Convert POJ romanization to TL.

    Args:
        poj_text: Text in POJ romanization

    Returns:
        Text converted to TL romanization
    """
    if not poj_text:
        return poj_text
    result = poj_diacritics_to_tone_numbers(poj_text)

    # Normalize to lowercase
    result = result.lower()

    # Convert superscript n to nn
    result = result.replace("\u207f", "nn")

    # Convert o followed by combining dot above right (U+0358) to oo
    result = result.replace("o\u0358", "oo")

    # Convert ou to oo (alternate POJ spelling)
    result = result.replace("ou", "oo")

    # Order matters: longer patterns first
    result = result.replace("chh", "tsh")
    result = result.replace("ch", "ts")
    result = re.sub(r"eng\b", "ing", result)
    result = re.sub(r"ek\b", "ik", result)
    result = result.replace("oa", "ua")
    result = result.replace("oe", "ue")
    return result
