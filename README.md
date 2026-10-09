# personal-website

## Template workflow

This site uses Jinja2 templates to keep shared snippets (like the contact block) in sync, plus a data file for publications.

1. Install the dependencies once: `python3 -m pip install --user jinja2 pyyaml`
2. Edit template sources in `templates/`, e.g. `templates/index.html.j2`
3. Edit publications in `data/papers.yaml`. One entry per paper; `topics` groups it under the Computer Science lens and `stages` under the Computational Journalism lens; `tags: [music]` also lists it on `music.html`. The narrative in each research-category card links to papers by id with `plink(...)` in `templates/research.html.j2` and `templates/music.html.j2`.
   The card and paper-entry macros are shared in `templates/includes/research_macros.html.j2`, their styles in `assets/css/papers.css`, and the expand/collapse behaviour in `assets/js/research-cards.js`.
4. Render static pages with `python3 render_templates.py`
5. Preview locally with `python3 -m http.server 8000` and open http://localhost:8000

The script overwrites `index.html`, `research.html`, `wishlist.html`, and every other entry in `TEMPLATE_OUTPUTS` in `render_templates.py`. Never edit those root HTML files directly; the next render will discard the changes.

## Wishlist page

This repository is public, so the mentorship ideas on `wishlist.html` are never stored in plain text here.

- The ideas live in `data/wishlist.private.yaml`, which is git-ignored. `data/wishlist.example.yaml` shows the schema.
- `python3 render_templates.py` renders that file through `templates/wishlist_body.html.j2`, encrypts the HTML (PBKDF2-SHA256 + AES-256-GCM, key derived from the two pledge passwords in the YAML), and writes the ciphertext to `data/wishlist.enc.json`, which is committed and embedded in `wishlist.html`. The browser decrypts it after the visitor types the two pledge words.
- On a machine without the private file, the render reuses the committed ciphertext, so the rest of the site still builds.
- The pledge words are displayed on the page, so this is a pledge and an anti-indexing measure, not secrecy. To make the ideas genuinely private, remove the two `{{ wishlist.passwords[...] }}` displays from `templates/wishlist.html.j2` and share the words directly.
- Each idea's `local:` list records where its materials live on your machine; it is never rendered.

Requires `cryptography` (`python3 -m pip install --user cryptography`) only when the private file is present.

Retired pages (the old clickable research DAG) live in `archive/`.
