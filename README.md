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

It has a title, subtitle, date and URL field, a Markdown body, and a live preview. Typing saves automatically. The blog page links to it ("Editor", at the bottom).

- **Publish** makes one commit in this repository: the post's Markdown in `_blog/posts/`, the re-rendered `blog/` pages, and any new images in `assets/blog/`. GitHub Pages shows it about a minute later. On a published post the button becomes **Publish changes**.
- **Unpublish** turns the post back into a draft and removes its page.
- **Delete draft** / **Discard changes** removes the draft (it stays in the drafts repository's history).
- **History** lists every version of the open post: each publish, and each save of its draft. Click one to read the post as it was; **Restore this version** makes it the text you are editing (the date and URL stay as they are). The list starts with one save per five minutes; "Show every save" lists them all.

A published post is edited like a draft: open it, change it (the changes save as a draft and are not live), then **Publish changes**.

Drag the line between two columns to make one wider and the other narrower (the list of posts, the writing, the preview, the comments). Double-click a line to put it back. The widths are remembered in that browser. On a narrow screen the widths are fixed.

### Images

- Drop an image file on the text (it goes after the paragraph you drop it on) or on the preview (a line shows the gap it will land in), paste one, or use **Add image**. It shows at once and uploads in the background.
- In the preview, click an image to select it. Drag a corner to resize it; double-click a corner to go back to the image's own size. Type under it for a caption. Backspace removes it.
- All of that is ordinary text in the Markdown, so it can be typed by hand too (and has to be on a narrow screen, where the preview is hidden):

      ![Alt text](/assets/blog/chart-1a2b3c4d.png){width=60%}
      The line under an image is its caption. It can use *Markdown*.

  An image on a line of its own becomes a `<figure>`; `width` is a share of the text column. An image with text on the same line stays inline.

After publishing from the browser (or inviting someone, which changes `admin/keys.json`), this repository on your laptop is behind: run `git pull` before your next local commit.

GitHub Pages tells browsers to keep each page for ten minutes. The editor waits until a publish is really on the website and then refreshes its own browser's copies of the blog pages, so you see the change at once. A reader who opened the blog in the last ten minutes sees the older copy until then (or until they reload).

### Working with other people

- **People** (top bar) is where you invite someone. Type their name, create a GitHub access token for them (the sheet links to the right GitHub page: only the repository `blog-shared`, Contents read and write) and paste it. The editor gives you a link to send them. Opening the link signs them in; they need no GitHub account and never see the token. "Show invitation" brings the link back later.
- **Share** moves the open draft, its images and its comments from `blog-drafts` to `blog-shared`, which is the only place invited people can open. **Stop sharing** moves it back. Publishing a shared draft removes it from there.
- An invited person sees the shared drafts and nothing else. They can edit the title, subtitle and text, add images, comment, and use History. They cannot publish, start or delete a draft, or change the date or URL.
- **Editing together.** Everyone's editor looks for other people's saves every 15 seconds and works them into the text, also while you are typing. Two people changing different words, even in one sentence, both keep their changes. If both change the same words, both versions are kept as two paragraphs and the person who saved second is told. It is not letter-by-letter live typing: that needs a server, and the site has none.
- **Comments.** Select words in the preview and press the Comment button that appears, or select them in the writing box and press **Comment** (Cmd/Ctrl+Alt+M). Cards stand in a column beside the preview, level with the words they are about. Reply, Resolve, and "Show resolved" work as in Google Docs. A comment whose words are later rewritten stays in the column, marked "No longer in the text". With nothing selected, Comment makes a note on the whole post. Comments work on your private drafts too.
- **History** says who made each save of a shared draft.

What to know about the arrangement:

- GitHub records everything an invited person does under **your** account, in `blog-shared` only. Their name on saves and comments is the one you typed when inviting them.
- **Remove** in People withdraws the invitation's passphrase. To end the access itself, also delete that person's token on GitHub (Settings, Developer settings, Fine-grained tokens): someone who kept the invitation could otherwise still recover the token from this repository's history.
- An invited person stays signed in on their browser until they press Sign out.
- Publishing puts their words and images on your site. Raw HTML in a post, and SVG images, can carry scripts that run there, so invite people you trust and look through History before publishing something others have edited.

### Signing in

The page is static, so there is no server to check a password. The key is always a GitHub access token; what differs is where it is kept.

**Your own browser.** Paste a token once and choose a password:

1. On GitHub: Settings, Developer settings, Personal access tokens, Fine-grained tokens, Generate new token.
   Repository access: only `alex2awesome.github.io`, `blog-drafts` and `blog-shared`. Repository permissions: Contents, Read and write.
2. Open `/admin/`, choose "Sign in with a GitHub token", paste the token, choose a password.

The token is stored only in that browser, encrypted with the password, and is sent only to api.github.com. After that the editor asks for the password. To cut off a lost device, revoke the token on GitHub. When the token expires, press Lock, then "Use a different token".

**Any other device, with a passphrase.** In People, under "Your other devices", set a passphrase. The editor then puts a copy of your token, encrypted under that passphrase, into `admin/keys.json`, and on any device you open `/admin/` and type the passphrase. Nothing is kept on that device.

- `admin/keys.json` is public, like everything in this repository, and so is every past version of it. The passphrase is the only thing protecting that copy of the token, and whoever guesses it can do everything the editor can. Use the suggested one (kept in a password manager), or at least 16 characters nobody could guess.
- Changing or removing the passphrase does not take old copies out of the repository's history. If a passphrase may have leaked, replace the token on GitHub.
- When your token expires or is replaced, set the passphrase again (it holds a copy of the token it was set with).

**Invited people** sign in with the passphrase in their invitation link. It works the same way: `admin/keys.json` holds their token, encrypted under a generated passphrase (100 random bits). The file holds no names; who is invited is listed in `people.json` in the private `blog-drafts` repository.

### Where things live

| Where | What |
|-------|------|
| `alex2awesome/blog-drafts` (private repository) | drafts in `drafts/<id>.md`, their images in `images/`, their comments in `comments/<id>.json`; every save is a commit. Also `people.json`: who is invited |
| `alex2awesome/blog-shared` (private repository) | the same three folders, for drafts that are shared. Invited people's tokens open this repository only |
| `admin/keys.json` | the tokens that passphrases unlock, each encrypted (PBKDF2-SHA256, AES-256-GCM); written by People |
| `_blog/posts/<slug>.md` | published posts: Markdown with `title`, `subtitle`, `date`, `slug`, `id` front matter |
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
- A post keeps one `id` for life: the name of its file in the drafts repository. Publishing removes that file and records the id in the post's front matter; the next edit recreates the same file. History is that file's commits plus the commits of the published post, so nothing a save ever held is lost. (A post published before ids existed gets one the next time it is edited.)
- Post sources sit in an underscore directory because GitHub Pages builds this repository with Jekyll, which skips such directories. Anywhere else, Jekyll would turn each `.md` into a second, unstyled copy of the post.
- Supported in posts: standard Markdown, tables, footnotes (`[^1]`), fenced code with syntax colours, images with captions (above), and raw HTML (for embeds). Scripts and embedded players do not run in the preview; they do on the published page.
- A comment is tied to the words it quotes in the Markdown, plus a little of the text before and after them. The preview finds those words again each time it is redrawn, so comments follow their text as the post changes around them.
- Saving a draft that someone else has saved in the meantime does a three-way merge (their version, yours, and the one you both started from), by line and then by word. Every version before and after is in History.
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
