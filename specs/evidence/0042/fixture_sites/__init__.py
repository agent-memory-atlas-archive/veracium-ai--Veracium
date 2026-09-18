"""A FIXTURE instrumentation package (not product code — a draft spec authorises none): three
modules with `declare_site(id)` calls at decision sites, one of which is never imported, so the
A-0-ter derivations have something to scan, register and reconcile."""
_REGISTRY: dict[str, dict] = {}


def declare_site(site_id: str) -> str:
    """The import-time record: registering is what happens when the module holding the call LOADS."""
    import inspect
    fr = inspect.stack()[1]
    _REGISTRY[site_id] = {"module": fr.filename.rsplit("/", 1)[-1], "line": fr.lineno}
    return site_id


def registry() -> dict[str, dict]:
    return dict(_REGISTRY)
