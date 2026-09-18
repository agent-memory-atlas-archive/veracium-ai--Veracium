from . import declare_site

SITE_ANSWER = declare_site("gate.answer.unverified-only")


def answer(grounded, unverified):
    if not grounded and unverified:
        raise ValueError("refuse: unverified-only support")
    return "answer"
