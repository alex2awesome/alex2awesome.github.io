#!/usr/bin/env python3
"""
Render Jinja2 templates in ./templates into static HTML files at the project root.

Data passed to every template:
  papers, papers_by_id   from data/papers.yaml (used by research.html.j2)
  wishlist               the encrypted wishlist bundle (used by wishlist.html.j2)

The wishlist ideas live in data/wishlist.private.yaml, which is git-ignored because this
repository is public. On each render, if that file is present, it is rendered through
templates/wishlist_body.html.j2 and encrypted (PBKDF2-SHA256 + AES-256-GCM) with a key
derived from the two pledge passwords; the ciphertext is written to data/wishlist.enc.json
(committed) and embedded in wishlist.html. If the private file is absent (e.g. a fresh
clone), the committed ciphertext is reused as-is.
"""

import base64
import hashlib
import json
from pathlib import Path

try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
except ImportError as exc:  # pragma: no cover - graceful CLI failure
    raise SystemExit(
        "Jinja2 is required. Install it with `python3 -m pip install --user jinja2`."
    ) from exc

try:
    import yaml
except ImportError as exc:  # pragma: no cover - graceful CLI failure
    raise SystemExit(
        "PyYAML is required. Install it with `python3 -m pip install --user pyyaml`."
    ) from exc


BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
DATA_DIR = BASE_DIR / "data"
PAPERS_FILE = DATA_DIR / "papers.yaml"
WISHLIST_PRIVATE = DATA_DIR / "wishlist.private.yaml"   # git-ignored: the real ideas
WISHLIST_ENC = DATA_DIR / "wishlist.enc.json"           # committed: ciphertext only
WISHLIST_BODY_TEMPLATE = "wishlist_body.html.j2"
PBKDF2_ITERATIONS = 250_000

TEMPLATE_OUTPUTS = {
    "index.html.j2": BASE_DIR / "index.html",
    "data-vis.html.j2": BASE_DIR / "data-vis.html",
    "research.html.j2": BASE_DIR / "research.html",
    "music.html.j2": BASE_DIR / "music.html",
    "talks.html.j2": BASE_DIR / "talks.html",
    "wishlist.html.j2": BASE_DIR / "wishlist.html",
}

VALID_SECTIONS = {"first-author", "thesis", "middle-author", "in-submission"}
VALID_TOPICS = {"tacit", "planning", "discourse", "sequence", "other"}
VALID_STAGES = {"news-finding", "source-finding", "story-structuring", "story-editing", "information-ecosystem", "other"}
VALID_STATUSES = {"not-started", "scoped", "early", "halfway", "mostly-done", "active"}


def load_papers() -> dict:
    """Read data/papers.yaml and fail loudly on anything the template can't render."""
    data = yaml.safe_load(PAPERS_FILE.read_text(encoding="utf-8")) or {}
    papers = data.get("papers") or []

    by_id = {}
    for paper in papers:
        label = paper.get("id") or paper.get("title") or "<unnamed>"
        for field in ("id", "title", "section", "topics", "stages"):
            if not paper.get(field):
                raise SystemExit(f"{PAPERS_FILE.name}: paper {label!r} is missing '{field}'")
        if paper["id"] in by_id:
            raise SystemExit(f"{PAPERS_FILE.name}: duplicate paper id {paper['id']!r}")
        if paper["section"] not in VALID_SECTIONS:
            raise SystemExit(f"{PAPERS_FILE.name}: paper {label!r} has unknown section {paper['section']!r}")
        bad_topics = set(paper["topics"]) - VALID_TOPICS
        if bad_topics:
            raise SystemExit(f"{PAPERS_FILE.name}: paper {label!r} has unknown topics {sorted(bad_topics)}")
        bad_stages = set(paper["stages"]) - VALID_STAGES
        if bad_stages:
            raise SystemExit(f"{PAPERS_FILE.name}: paper {label!r} has unknown stages {sorted(bad_stages)}")
        paper.setdefault("details", [])
        paper.setdefault("badges", "")
        paper.setdefault("link", "")
        paper.setdefault("summary", "")
        paper.setdefault("notes", [])
        paper.setdefault("tags", [])        # e.g. [music]: also listed on music.html
        by_id[paper["id"]] = paper

    return {"papers": papers, "papers_by_id": by_id}


def passphrase_for(passwords) -> bytes:
    """The two pledge passwords, normalised the same way the page's JavaScript normalises them."""
    return "\n".join(p.strip().lower() for p in passwords).encode("utf-8")


def encrypt_wishlist(env: Environment) -> dict:
    """Render the private wishlist to HTML and encrypt it. Returns the bundle embedded in the page."""
    try:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    except ImportError as exc:  # pragma: no cover - graceful CLI failure
        raise SystemExit(
            "The `cryptography` package is required to encrypt the wishlist: "
            "`python3 -m pip install --user cryptography`."
        ) from exc

    data = yaml.safe_load(WISHLIST_PRIVATE.read_text(encoding="utf-8")) or {}
    passwords = data.get("passwords") or []
    if len(passwords) != 2 or not all(isinstance(p, str) and p.strip() for p in passwords):
        raise SystemExit(f"{WISHLIST_PRIVATE.name}: `passwords` must list exactly two non-empty passwords")
    for topic in data.get("topics") or []:
        for idea in topic.get("ideas") or []:
            if idea.get("status") not in VALID_STATUSES:
                raise SystemExit(
                    f"{WISHLIST_PRIVATE.name}: idea {idea.get('title')!r} has status {idea.get('status')!r}; "
                    f"expected one of {sorted(VALID_STATUSES)}"
                )

    html = env.get_template(WISHLIST_BODY_TEMPLATE).render(wishlist=data)
    plaintext = html.encode("utf-8")

    # Salt and nonce are derived from the plaintext so that re-rendering unchanged content gives
    # byte-identical output (clean git diffs). Different content gives a different salt, hence a
    # different key, so the AES-GCM nonce is never reused under one key.
    salt = hashlib.sha256(b"wishlist-salt\0" + plaintext).digest()[:16]
    nonce = hashlib.sha256(b"wishlist-nonce\0" + plaintext).digest()[:12]
    key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=PBKDF2_ITERATIONS).derive(
        passphrase_for(passwords)
    )
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, None)

    def b64(raw: bytes) -> str:
        return base64.b64encode(raw).decode("ascii")

    return {
        "kdf": "PBKDF2-SHA256",
        "iterations": PBKDF2_ITERATIONS,
        "salt": b64(salt),
        "iv": b64(nonce),
        "ciphertext": b64(ciphertext),
        # The pledge words are displayed on the page itself, so they are not secret; the point of
        # encrypting is to keep the ideas out of the public repository and out of search indexes.
        "passwords": [p.strip() for p in passwords],
        "updated": str(data.get("updated", "")),
    }


def load_wishlist(env: Environment) -> dict:
    if WISHLIST_PRIVATE.exists():
        bundle = encrypt_wishlist(env)
        WISHLIST_ENC.write_text(json.dumps(bundle, indent=1) + "\n", encoding="utf-8")
        return bundle
    if WISHLIST_ENC.exists():
        return json.loads(WISHLIST_ENC.read_text(encoding="utf-8"))
    raise SystemExit(f"Found neither {WISHLIST_PRIVATE.name} nor {WISHLIST_ENC.name} in data/.")


def main() -> None:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    context = load_papers()
    context["wishlist"] = load_wishlist(env)

    for template_name, output_path in TEMPLATE_OUTPUTS.items():
        template = env.get_template(template_name)
        rendered = template.render(**context)
        output_path.write_text(rendered, encoding="utf-8")


if __name__ == "__main__":
    main()
