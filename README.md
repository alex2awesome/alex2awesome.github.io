# personal-website

## Template workflow

This site now uses Jinja2 templates to keep shared snippets (like the contact block) in sync.

1. Install the dependency once: `python3 -m pip install --user jinja2`
2. Edit template sources in `templates/`, e.g. `templates/index.html.j2`
3. Render static pages with `python3 render_templates.py`

The script overwrites `index.html`, `data-vis.html`, and any other entries you add to `TEMPLATE_OUTPUTS` in `render_templates.py`.
