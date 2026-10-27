# Mutation-Matrix: tests/test_0007_attestation_jobs.py::test_rows_json_is_its_generators_output
"""Generate specs/evidence/attestation/rows.json, the attestation matrix's one carrier (workflow and aggregator).

    $PY specs/evidence/attestation/gen_rows.py [--check]"""
import json, pathlib

SP = "`actions/setup-python` (what most users' CI runs)"
PBS = "python-build-standalone: uv, mise by default, and Rye, PDM and hatch through it"
ORG = "python.org installers"
BREW = "Homebrew `python@3.14`"
CONDA = "conda-forge `python` 3.14"
PYENV = "pyenv and asdf source builds (and mise with `python.compile=true`)"
DEAD = "the deadsnakes PPA"
DISTRO = "a distro's own Python 3.14: its DEFAULT `python3` where it reaches 3.14, or its `python3.14` package"
DOCKER = "official Docker `python:3.14` images"
ARM = "**arm64 Linux (v0.10, Q4):** python-build-standalone, and the official Docker `python:3.14` images"
LATER = "the Windows Store Python"

UV_INSTALL = "curl -LsSf https://astral.sh/uv/install.sh | sh && ~/.local/bin/uv python install 3.14"
UV_PY = "$(~/.local/bin/uv python find 3.14)"
rows = []
def row(spec_row, route, runner_image, runs_on, install, python, expect_prefix, image=None, user_add=None):
    r = {"spec_row": spec_row, "route": route, "runner_image": runner_image, "runs_on": runs_on,
         "install": install, "python": python, "expect_prefix": expect_prefix}
    if image:
        r["image"] = image
        r["user_add"] = user_add
    rows.append(r)

for img in ("ubuntu-24.04", "ubuntu-22.04", "macos-latest", "windows-latest"):
    row(SP, "setup-python", img, img, "setup-python", "python", "${RUNNER_TOOL_CACHE}/Python")
row(PBS, "uv", "ubuntu-24.04", "ubuntu-24.04", UV_INSTALL, UV_PY, "${HOME}/.local/share/uv/python")
row(PBS, "uv", "macos-latest", "macos-latest", UV_INSTALL, UV_PY, "${HOME}/.local/share/uv/python")
row(PBS, "uv", "windows-latest", "windows-latest",
    "powershell -ExecutionPolicy ByPass -c 'irm https://astral.sh/uv/install.ps1 | iex' && ~/.local/bin/uv python install 3.14",
    UV_PY, "${APPDATA}/uv/python")
row(ORG, "python.org", "macos-latest", "macos-latest",
    "curl -LsSfo py.pkg https://www.python.org/ftp/python/3.14.0/python-3.14.0-macos11.pkg && sudo installer -pkg py.pkg -target /",
    "/Library/Frameworks/Python.framework/Versions/3.14/bin/python3.14", "/Library/Frameworks/Python.framework/Versions/3.14")
row(ORG, "python.org", "windows-latest", "windows-latest",
    "curl -LsSfo py.exe https://www.python.org/ftp/python/3.14.0/python-3.14.0-amd64.exe && ./py.exe /quiet InstallAllUsers=1 PrependPath=0 TargetDir='C:\\Python314'",
    "C:/Python314/python.exe", "C:/Python314")
row(BREW, "homebrew", "macos-latest", "macos-latest", "brew install python@3.14",
    "$(brew --prefix python@3.14)/bin/python3.14", "$(brew --cellar)/python@3.14")
for img in ("ubuntu-24.04", "macos-latest", "windows-latest"):
    row(CONDA, "conda-forge", img, img, "conda create -y -p \"$HOME/attest-conda\" -c conda-forge --override-channels python=3.14",
        "$HOME/attest-conda/bin/python" if img != "windows-latest" else "$HOME/attest-conda/python.exe", "${HOME}/attest-conda")
row(PYENV, "pyenv", "ubuntu-24.04", "ubuntu-24.04",
    "sudo apt-get update -q && sudo apt-get install -yq libsqlite3-dev libssl-dev libbz2-dev libreadline-dev libffi-dev zlib1g-dev liblzma-dev && curl -fsSL https://pyenv.run | bash && ~/.pyenv/bin/pyenv install 3.14",
    "$(~/.pyenv/bin/pyenv prefix 3.14)/bin/python3.14", "${HOME}/.pyenv/versions")
for img in ("ubuntu-22.04", "ubuntu-24.04"):
    row(DEAD, "deadsnakes", img, img,
        "sudo add-apt-repository -y ppa:deadsnakes/ppa && sudo apt-get update -q && sudo apt-get install -yq python3.14 python3.14-venv",
        "/usr/bin/python3.14", "/usr")
APT = "apt-get update -q && DEBIAN_FRONTEND=noninteractive apt-get install -yq git python3 python3-venv"
for name, image, install, py, add in (
        ("ubuntu-26.04", "ubuntu:26.04", APT, "/usr/bin/python3", "useradd -m attest"),
        ("fedora-43", "fedora:43", "dnf install -yq git python3", "/usr/bin/python3", "useradd -m attest"),
        ("fedora-44", "fedora:44", "dnf install -yq git python3", "/usr/bin/python3", "useradd -m attest"),
        ("alpine-3.24", "alpine:3.24", "apk add --no-cache git python3", "/usr/bin/python3", "adduser -D attest"),
        ("rhel-9", "registry.access.redhat.com/ubi9/ubi", "dnf install -yq git python3.14", "/usr/bin/python3.14", "useradd -m attest"),
        ("rhel-10", "registry.access.redhat.com/ubi10/ubi", "dnf install -yq git python3.14", "/usr/bin/python3.14", "useradd -m attest"),
        ("amazonlinux-2023", "amazonlinux:2023", "dnf install -yq git python3.14 shadow-utils", "/usr/bin/python3.14", "useradd -m attest")):
    row(DISTRO, "distro", name, "ubuntu-24.04", install, py, "/usr", image=image, user_add=add)
for tag, add in (("3.14-bookworm", "useradd -m attest"), ("3.14-trixie", "useradd -m attest"),
                 ("3.14-alpine", "apk add --no-cache git && adduser -D attest")):
    row(DOCKER, "docker", f"python:{tag}", "ubuntu-24.04", "true" if "alpine" not in tag else "apk add --no-cache git",
        "/usr/local/bin/python3.14", "/usr/local", image=f"python:{tag}", user_add=add)
row(ARM, "uv", "ubuntu-24.04-arm", "ubuntu-24.04-arm", UV_INSTALL, UV_PY, "${HOME}/.local/share/uv/python")
for tag, add in (("3.14-bookworm", "useradd -m attest"), ("3.14-trixie", "useradd -m attest"),
                 ("3.14-alpine", "apk add --no-cache git && adduser -D attest")):
    row(ARM, "docker", f"python:{tag} (linux/arm64)", "ubuntu-24.04-arm", "true" if "alpine" not in tag else "apk add --no-cache git",
        "/usr/local/bin/python3.14", "/usr/local", image=f"python:{tag}", user_add=add)

out = {"_comment": "GENERATED by the I5 commit's row generator from 0007 §4d's route table; the workflow's matrix and "
                   "the aggregator's unavailable-row list both read this file, and a cell compares its spec_row values "
                   "with the table's first column.",
       "later": [{"spec_row": LATER, "why": "not installable non-interactively on a hosted runner (§4d LATER)"}],
       "rows": rows}
TEXT = json.dumps(out, indent=1) + "\n"
P = pathlib.Path(__file__).resolve().parent / "rows.json"

if __name__ == "__main__":
    import sys
    if sys.argv[1:] == ["--check"]:
        ok = P.exists() and P.read_text() == TEXT
        print("rows.json is current" if ok else "rows.json is STALE: run gen_rows.py")
        sys.exit(0 if ok else 1)
    P.write_text(TEXT)
    print(len(rows), "rows")
