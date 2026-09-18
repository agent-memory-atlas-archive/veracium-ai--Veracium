from . import declare_site

SITE_FORGET = declare_site("lifecycle.forget.scope")   # this module is deliberately NEVER imported by the harness


def forget(user):
    raise PermissionError("out of scope")
