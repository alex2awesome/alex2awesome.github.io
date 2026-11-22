# personal-website

## Template workflow

This site uses Jinja2 templates to keep shared snippets (like the contact block) in sync, plus a data file for publications.

1. Install the dependencies once: `python3 -m pip install --user jinja2 pyyaml markdown pygments`
2. Edit template sources in `templates/`, e.g. `templates/index.html.j2`
3. Edit publications in `data/papers.yaml`. One entry per paper; `topics` groups it under the Computer Science lens and `stages` under the Computational Journalism lens; `tags: [music]` also lists it on `music.html`. The narrative in each research-category card links to papers by id with `plink(...)` in `templates/research.html.j2` and `templates/music.html.j2`.
   The card and paper-entry macros are shared in `templates/includes/research_macros.html.j2`, their styles in `assets/css/papers.css`, and the expand/collapse behaviour in `assets/js/research-cards.js`.
4. Render static pages with `python3 render_templates.py`
5. Preview locally with `python3 -m http.server 8000` and open http://localhost:8000

The script overwrites `index.html`, `research.html`, `wishlist.html`, every other entry in `TEMPLATE_OUTPUTS` in `render_templates.py`, and everything in `blog/`. Never edit those root HTML files directly; the next render will discard the changes.

## Blog

Write posts in the editor on the website: **https://www.alexander-spangher.com/admin/**

It has a title, subtitle, date and URL field, a Markdown body, and a live preview. Typing saves automatically. Paste or drop an image into the text to add it.

- **Publish** makes one commit in this repository: the post's Markdown in `_blog/posts/`, the re-rendered `blog/` pages, and any new images in `assets/blog/`. GitHub Pages shows it about a minute later. On a published post the button becomes **Publish changes**.
- **Unpublish** turns the post back into a draft and removes its page.
- **Delete draft** / **Discard changes** removes the draft (it stays in the drafts repository's history).

After publishing from the browser, this repository on your laptop is behind: run `git pull` before your next local commit.

### Signing in

The page is static, so there is no server to check a password. The key is a GitHub access token:

1. On GitHub: Settings, Developer settings, Personal access tokens, Fine-grained tokens, Generate new token.
   Repository access: only `alex2awesome.github.io` and `blog-drafts`. Repository permissions: Contents, Read and write.
2. Open `/admin/`, paste the token, choose a password.

The token is stored only in that browser, encrypted with the password, and is sent only to api.github.com. Each browser or device needs this once; after that the editor asks for the password. To cut off a lost device, revoke the token on GitHub. When the token expires, press Lock, then "Use a different token".

### Where things live

| Where | What |
|-------|------|
| `alex2awesome/blog-drafts` (private repository) | drafts in `drafts/`, their images in `images/`; every save is a commit |
| `_blog/posts/<slug>.md` | published posts: Markdown with `title`, `subtitle`, `date`, `slug` front matter |
| `assets/blog/` | images used in published posts |
| `blog/` | generated pages: `index.html`, one `<slug>.html` per post, `feed.xml`; never edit by hand |
| `templates/blog/`, `assets/css/blog.css` | how the blog looks |
| `admin/index.html` | the editor |
| `admin/vendor/pyodide/` | Python for the browser (Pyodide 314.0.8) and the packages the renderer needs |

### How it works

- The editor runs `render_templates.py` and the templates from this repository inside the browser (Pyodide), so the preview is exactly the page that gets published, and `python3 render_templates.py` on the laptop renders the same `blog/`. Keep the blog functions in that file free of anything that cannot run in a browser (see its docstring).
- Changes to the blog templates or stylesheet reach the editor once they are pushed; the next Publish re-renders every post with them.
- The file name is the post's URL (`_blog/posts/my-post.md` is served at `/blog/my-post.html`). A draft's URL follows its title until you type one or publish; after that it stays fixed, and changing it breaks links to the old address.
- A draft with no date gets the day it is published.
- Post sources sit in an underscore directory because GitHub Pages builds this repository with Jekyll, which skips such directories. Anywhere else, Jekyll would turn each `.md` into a second, unstyled copy of the post.
- Supported in posts: standard Markdown, tables, footnotes (`[^1]`), fenced code with syntax colours, and raw HTML (for embeds or `<figure>` captions). Scripts and embedded players do not run in the preview; they do on the published page.
- To test the editor without touching the site: serve this directory (`python3 -m http.server 8000`), open `http://localhost:8000/admin/`, and point `CONFIG` in `admin/index.html` at test branches.

## Wishlist page

This repository is public, so the mentorship ideas on `wishlist.html` are never stored in plain text here.

- The ideas live in `data/wishlist.private.yaml`, which is git-ignored. `data/wishlist.example.yaml` shows the schema.
- `python3 render_templates.py` renders that file through `templates/wishlist_body.html.j2`, encrypts the HTML (PBKDF2-SHA256 + AES-256-GCM, key derived from the two pledge passwords in the YAML), and writes the ciphertext to `data/wishlist.enc.json`, which is committed and embedded in `wishlist.html`. The browser decrypts it after the visitor types the two pledge words.
- On a machine without the private file, the render reuses the committed ciphertext, so the rest of the site still builds.
- The pledge words are displayed on the page, so this is a pledge and an anti-indexing measure, not secrecy. To make the ideas genuinely private, remove the two `{{ wishlist.passwords[...] }}` displays from `templates/wishlist.html.j2` and share the words directly.
- Each idea's `local:` list records where its materials live on your machine; it is never rendered.

Requires `cryptography` (`python3 -m pip install --user cryptography`) only when the private file is present.

Retired pages (the old clickable research DAG) live in `archive/`.
