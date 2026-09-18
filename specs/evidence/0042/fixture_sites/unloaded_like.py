from . import declare_site

SITE_FORGET = declare_site("lifecycle.forget.scope")   # this module is deliberately NEVER imported by the harness


def forget(user):
    with SITE_FORGET.consult():
        raise SITE_FORGET.fire(PermissionError("out of scope"))
