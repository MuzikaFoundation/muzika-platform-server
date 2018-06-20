from functools import wraps

from flask import request

DEFAULT_LANGUAGE = 'en'
SUPPORT_LANGUAGE = [
    'en',
    'ko'
]


def get_best_fit_language():
    """
    Checks the best fit language for user by checking 'Accept-Language' in request header, and assign the language
    into "request.lang". If no support language found, set it to "en" (English).
    """

    # get accepted language from 'Accept-Language' header.
    # we will ignore the detail area such as 'US' in 'en-US'
    accept_langs = [lang.split('-')[0] for lang in request.accept_languages.values()]
    best_fit_language = DEFAULT_LANGUAGE

    for lang in accept_langs:
        # if support language is found, set the language to it.
        # Since it assure that the accept languages are sorted by quality,
        # it will be the best fit language for user.
        if lang in SUPPORT_LANGUAGE:
            best_fit_language = lang
            break

    return best_fit_language


def lang_check(func):
    """
    Assigns best fit language to "request.lang".
    """
    @wraps(func)
    def _func(*args, **kwargs):
        request.lang = get_best_fit_language()
        return _func(*args, **kwargs)

    return _func
