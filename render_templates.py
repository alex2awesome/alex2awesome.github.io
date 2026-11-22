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

The blog is rendered from Markdown files with YAML front matter (title, subtitle, date) in
_blog/posts/<slug>.md. Each becomes blog/<slug>.html, listed on blog/index.html and in
blog/feed.xml. Everything in blog/ is generated.

Posts are normally written and published from the editor at /admin/ on the website
(admin/index.html). It runs this very file in the browser (Pyodide), so the blog functions below
must keep working without the `cryptography` package and without the wishlist's private file, and
`render_blog` must depend on nothing but _blog/posts, templates/blog, templates/includes and CNAME.
Drafts never touch this repository: the editor keeps them in a private one.

The sources sit in an underscore directory because GitHub Pages builds this repository with
Jekyll, which would otherwise convert each .md into a second, unstyled copy of the post.
"""

import base64
import datetime as dt
import hashlib
import json
import re
import unicodedata
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

BLOG_SRC_DIR = BASE_DIR / "_blog"
BLOG_POSTS_DIR = BLOG_SRC_DIR / "posts"      # committed: published posts
BLOG_OUT_DIR = BASE_DIR / "blog"             # generated: index.html, <slug>.html, feed.xml
BLOG_ASSETS_DIR = BASE_DIR / "assets" / "blog"   # images used in posts
BLOG_INDEX_TEMPLATE = "blog/index.html.j2"
BLOG_POST_TEMPLATE = "blog/post.html.j2"
BLOG_FEED_TEMPLATE = "blog/feed.xml.j2"
BLOG_RESERVED_SLUGS = {"index", "feed"}      # blog/index.html and blog/feed.xml
SITE_AUTHOR = "Alexander Spangher"

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
        paper.setdefault("tweet", "")       # announcement tweet, shown next to the paper link
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


class BlogError(ValueError):
    """A post that cannot be read or rendered. The message is written for the person editing it."""


def site_url() -> str:
    """https://<custom domain>, read from CNAME. Used for absolute links in the feed and share tags."""
    cname = BASE_DIR / "CNAME"
    host = cname.read_text(encoding="utf-8").strip() if cname.exists() else ""
    return f"https://{host}" if host else ""


def slugify(text: str) -> str:
    """'Don't Panic: Naïve Planning' -> 'dont-panic-naive-planning'. Mirrored in admin/index.html."""
    text = unicodedata.normalize("NFKD", str(text))
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).lower()
    text = re.sub(r"['’]", "", text)
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text[:80].strip("-")


_FRONT_MATTER = re.compile(r"\A---[ \t]*\r?\n(.*?)^---[ \t]*$\r?\n?", re.DOTALL | re.MULTILINE)


def split_front_matter(text: str) -> tuple:
    """Split a post file into (front matter dict, Markdown body)."""
    match = _FRONT_MATTER.match(text)
    if not match:
        return {}, text
    try:
        meta = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as exc:
        raise BlogError(f"the front matter is not valid YAML: {exc}") from exc
    if not isinstance(meta, dict):
        raise BlogError("the front matter must be `key: value` lines")
    return meta, text[match.end():].lstrip("\n")


def join_front_matter(meta: dict, body: str) -> str:
    head = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True, default_flow_style=False, width=1000)
    return f"---\n{head.strip()}\n---\n\n{body.strip()}\n"


def parse_date(value):
    """A front matter date as datetime.date, or None when it is absent."""
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return dt.date.fromisoformat(value.strip())
        except ValueError as exc:
            raise BlogError(f"the date {value!r} should look like 2026-11-22") from exc
    return None


def typographic(text: str) -> str:
    """Curly quotes and real dashes for titles and subtitles, as `smarty` does for the post body."""
    text = str(text)
    text = re.sub(r"(?<=\w)'(?=\w)", "\u2019", text)             # don't
    text = re.sub(r'"(?=\w)', "\u201c", text).replace('"', "\u201d")
    text = re.sub(r"(?<!\w)'(?=\w)", "\u2018", text).replace("'", "\u2019")
    text = re.sub(r"(?<=\s)--(?=\s)", "\u2013", text)
    return text.replace("...", "\u2026")


def figures_extension():
    """A Markdown extension: a paragraph that starts with an image becomes a <figure>.

        ![Alt text](/assets/blog/chart.png){width=60%}
        The line under the image is its caption, and may use *Markdown*.

    `{width=...}` (written by the editor when an image is resized) becomes the figure's width,
    so the caption wraps with the image. An image with text on the same line stays inline.
    """
    import xml.etree.ElementTree as etree

    from markdown.extensions import Extension
    from markdown.treeprocessors import Treeprocessor

    def image_of(node):
        """The <img> that `node` is, or that a link wraps on its own."""
        if node.tag == "img":
            return node
        alone = node.tag == "a" and len(node) == 1 and not (node.text or "").strip() and not (node[0].tail or "").strip()
        return node[0] if alone and node[0].tag == "img" else None

    def as_figure(paragraph):
        if (paragraph.text or "").strip() or not len(paragraph):
            return None
        first, rest = paragraph[0], list(paragraph)[1:]
        image = image_of(first)
        if image is None:
            return None
        tail = first.tail or ""
        if not tail.strip() and rest and rest[0].tag == "br":      # two spaces at the end of the image's line
            tail, rest = "\n" + (rest[0].tail or ""), rest[1:]
        has_caption = bool(tail.strip() or rest)
        gap = tail[: len(tail) - len(tail.lstrip())]
        if has_caption and "\n" not in gap:
            return None                                             # text on the image's own line: an inline image
        if any(node.tag == "img" for child in rest for node in child.iter()):
            return None                                             # several images in a row: left as written

        figure = etree.Element("figure", dict(paragraph.attrib))
        width = re.fullmatch(r"(\d{1,4})(%|px)?", image.get("width", "").strip())
        if width:
            del image.attrib["width"]
            figure.set("style", f"width: {width.group(1)}{width.group(2) or 'px'}")
        figure.text = "\n"
        first.tail = "\n"
        figure.append(first)
        if has_caption:
            caption = etree.SubElement(figure, "figcaption")
            caption.text = tail.lstrip()
            caption.extend(rest)
            caption.tail = "\n"
        return figure

    class Figures(Treeprocessor):
        def run(self, root):
            for parent in list(root.iter()):
                for index, child in enumerate(list(parent)):
                    figure = as_figure(child) if child.tag == "p" else None
                    if figure is not None:
                        figure.tail = child.tail
                        parent[index] = figure

    class FiguresExtension(Extension):
        def extendMarkdown(self, md):
            # After attr_list (8) has moved {width=...} onto the image and smarty (6) has run.
            md.treeprocessors.register(Figures(md), "figures", 3)

    return FiguresExtension()


def render_markdown(text: str) -> str:
    try:
        import markdown
    except ImportError as exc:  # pragma: no cover - graceful CLI failure
        raise SystemExit(
            "The `markdown` package is required to render blog posts: "
            "`python3 -m pip install --user markdown pygments`."
        ) from exc

    # extra: tables, fenced code, footnotes, attribute lists. smarty: curly quotes and dashes.
    # toc: ids on headings, so sections can be linked to. figures: images with captions.
    extensions = ["extra", "sane_lists", "smarty", "toc", figures_extension()]
    configs = {}
    try:
        import pygments  # noqa: F401  (optional: colours for fenced code blocks)
    except ImportError:
        pass
    else:
        extensions.append("codehilite")
        configs["codehilite"] = {"guess_lang": False, "css_class": "codehilite"}
    return markdown.markdown(text, extensions=extensions, extension_configs=configs, output_format="html")


def build_post(meta: dict, body: str, slug: str) -> dict:
    """The dict the blog templates read. `html` is filled in by whoever needs the rendered body."""
    date = parse_date(meta.get("date"))
    return {
        "slug": slug,
        "title": str(meta.get("title") or "").strip(),
        "subtitle": str(meta.get("subtitle") or "").strip(),
        "date": date,
        "date_iso": date.isoformat() if date else "",
        "date_display": f"{date:%B} {date.day}, {date.year}" if date else "",
        "url": f"/blog/{slug}.html",
        "meta": meta,
        "body": body,
        "html": "",
    }


def read_post(path: Path) -> dict:
    try:
        meta, body = split_front_matter(path.read_text(encoding="utf-8"))
        return build_post(meta, body, path.stem)
    except BlogError as exc:
        raise BlogError(f"{path.relative_to(BASE_DIR)}: {exc}") from exc


def load_published_posts() -> list:
    """Every post in _blog/posts, newest first, with its body rendered to HTML."""
    posts = []
    for path in sorted(BLOG_POSTS_DIR.glob("*.md")):
        post = read_post(path)
        where = path.relative_to(BASE_DIR)
        for field in ("title", "date"):
            if not post[field]:
                raise BlogError(f"{where}: the front matter is missing '{field}'")
        if slugify(post["slug"]) != post["slug"] or post["slug"] in BLOG_RESERVED_SLUGS:
            raise BlogError(f"{where}: the file name becomes the post's URL, so it must look like my-post-title.md")
        post["html"] = render_markdown(post["body"])
        posts.append(post)
    posts.sort(key=lambda post: (post["date"], post["slug"]), reverse=True)
    return posts


def render_post_page(env: Environment, post: dict, preview: bool = False) -> str:
    return env.get_template(BLOG_POST_TEMPLATE).render(post=post, site_url=site_url(), preview=preview)


def render_blog(env: Environment) -> list:
    """Write blog/ from the published posts and remove pages of posts that no longer exist."""
    posts = load_published_posts()
    base = site_url()
    outputs = {"index.html": env.get_template(BLOG_INDEX_TEMPLATE).render(posts=posts, site_url=base)}
    for post in posts:
        outputs[f"{post['slug']}.html"] = render_post_page(env, post)
        # Feed readers show the post away from this site, so its root-relative links need the domain.
        post["feed_html"] = re.sub(r'(\s(?:src|href)=")/(?!/)', rf"\g<1>{base}/", post["html"])
    if posts:
        outputs["feed.xml"] = env.get_template(BLOG_FEED_TEMPLATE).render(
            posts=posts, site_url=base, author=SITE_AUTHOR
        )

    BLOG_OUT_DIR.mkdir(exist_ok=True)
    for name, text in outputs.items():
        (BLOG_OUT_DIR / name).write_text(text, encoding="utf-8")
    # blog/ holds nothing but generated pages, so a page that was not just written belongs to a
    # post that has been unpublished or renamed.
    for stale in [*BLOG_OUT_DIR.glob("*.html"), *BLOG_OUT_DIR.glob("*.xml")]:
        if stale.name not in outputs:
            stale.unlink()
    return posts


def build_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["typo"] = typographic
    return env


def main() -> None:
    env = build_env()
    context = load_papers()
    context["wishlist"] = load_wishlist(env)

    for template_name, output_path in TEMPLATE_OUTPUTS.items():
        template = env.get_template(template_name)
        rendered = template.render(**context)
        output_path.write_text(rendered, encoding="utf-8")

    try:
        render_blog(env)
    except BlogError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
