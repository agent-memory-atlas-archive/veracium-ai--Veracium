from . import declare_site

SITE_QUARANTINE = declare_site("ingest.quarantine.third-party")


def admit(record):
    if record.get("author") == "third_party":
        return False        # quarantine
    return True
