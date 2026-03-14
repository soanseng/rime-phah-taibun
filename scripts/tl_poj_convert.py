"""TL <-> POJ romanization conversion utility.

Converts between TL (Tai-lo) and POJ (Pe-oe-ji) romanization systems
for Taiwanese Hokkien.
"""

import re


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
    # Order matters: longer patterns first
    result = result.replace("chh", "tsh")
    result = result.replace("ch", "ts")
    result = re.sub(r"eng\b", "ing", result)
    result = re.sub(r"ek\b", "ik", result)
    result = result.replace("oa", "ua")
    result = result.replace("oe", "ue")
    return result
