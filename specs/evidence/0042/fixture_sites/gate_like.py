from . import declare_site

SITE_ANSWER = declare_site("gate.answer.unverified-only")


def answer(grounded, unverified):
    with SITE_ANSWER.consult():
        if not grounded and unverified:
            raise SITE_ANSWER.fire(ValueError("refuse: unverified-only support"))
    return "answer"
