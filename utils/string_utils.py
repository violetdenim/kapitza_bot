"""
Helper functions for string processing etc.
"""

def strip_substr(text, sub_strings):
    n = len(text)
    n_old = n + 1
    while n < n_old:
        for substr in sub_strings:
            text = text.strip(substr)
        n, n_old = len(text), n
    return text

def drop_ending(some_text, endings='.!?'):
    p = len(some_text) - 1
    while p >= 0 and some_text == ' ':
        p -= 1
    if p < 0 or some_text[p] in endings:
        return some_text[:p+1]
    while p >= 0 and some_text[p] not in endings:
        p -= 1
    if p < 0:
        return ""
    return some_text[:p+1]

