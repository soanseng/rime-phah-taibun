"""TL <-> POJ romanization conversion utility.

Converts between TL (Tai-lo) and POJ (Pe-oe-ji) romanization systems
for Taiwanese Hokkien.
"""

import re
import unicodedata


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
    """Convert POJ Unicode diacritics to TL tone numbers.

    Args:
        text: Text with POJ diacritics (e.g. â, á, à, ā, a̍)

    Returns:
        Text with diacritics replaced by tone numbers
    """
    if not text:
        return text

    # Mapping from combining diacritical marks to tone numbers
    diacritic_to_tone = {
        "\u0301": "2",  # acute accent → tone 2
        "\u0300": "3",  # grave accent → tone 3
        "\u0302": "5",  # circumflex → tone 5
        "\u0304": "7",  # macron → tone 7
        "\u030D": "8",  # vertical line above → tone 8
    }

    # Decompose to NFD so diacritics become separate combining characters
    decomposed = unicodedata.normalize("NFD", text)

    result = []
    for char in decomposed:
        if char in diacritic_to_tone:
            result.append(diacritic_to_tone[char])
        else:
            result.append(char)

    return "".join(result)


def poj_to_tl(poj_text: str) -> str:
    """Convert POJ romanization to TL.

    Args:
        poj_text: Text in POJ romanization

    Returns:
        Text converted to TL romanization
    """
    if not poj_text:
        return poj_text
    result = poj_text

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
