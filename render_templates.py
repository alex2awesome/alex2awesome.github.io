#!/usr/bin/env python3
"""
Render Jinja2 templates in ./templates into static HTML files at the project root.
"""

from pathlib import Path

try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
except ImportError as exc:  # pragma: no cover - graceful CLI failure
    raise SystemExit(
        "Jinja2 is required. Install it with `python3 -m pip install --user jinja2`."
    ) from exc


BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"

TEMPLATE_OUTPUTS = {
    "index.html.j2": BASE_DIR / "index.html",
    "data-vis.html.j2": BASE_DIR / "data-vis.html",
    "research.html.j2": BASE_DIR / "research.html",
    "music.html.j2": BASE_DIR / "music.html",
    "talks.html.j2": BASE_DIR / "talks.html",
}


def main() -> None:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    for template_name, output_path in TEMPLATE_OUTPUTS.items():
        template = env.get_template(template_name)
        rendered = template.render()
        output_path.write_text(rendered, encoding="utf-8")


if __name__ == "__main__":
    main()
