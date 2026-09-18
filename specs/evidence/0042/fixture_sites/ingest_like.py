from . import declare_site

SITE_QUARANTINE = declare_site("ingest.quarantine.third-party")


def admit(record):
    with SITE_QUARANTINE.consult():
        if record.get("author") == "third_party":
            return SITE_QUARANTINE.fire(False)        # quarantine
    return True
