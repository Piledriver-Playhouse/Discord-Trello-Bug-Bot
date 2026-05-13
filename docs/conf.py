# -- Sphinx Configuration ---------------------------------------------------
# Full documentation: https://www.sphinx-doc.org/en/master/usage/configuration.html

"""
Sphinx configuration for Discord Trello Bug Bot documentation.

This file is executed by Sphinx to build the project's HTML documentation.
It uses the Furo theme for a clean, modern look and includes the
``autodoc``, ``napoleon``, and ``myst_parser`` extensions to pull
docstrings from ``bot.py`` and render Markdown sources alongside
reStructuredText.
"""

import os
import sys

# -- Path setup --------------------------------------------------------------
# Add the project root so autodoc can import ``bot.py``.
# Because bot.py validates env vars at import time we mock them here.

_MOCK_ENV = {
    "DISCORD_TOKEN": "DOCS_BUILD_PLACEHOLDER",
    "BUG_CHANNEL_ID": "000000000000000000",
    "TRELLO_API_KEY": "DOCS_BUILD_PLACEHOLDER",
    "TRELLO_TOKEN": "DOCS_BUILD_PLACEHOLDER",
    "TRELLO_LIST_ID": "DOCS_BUILD_PLACEHOLDER",
    "TRELLO_DONE_LIST_ID": "DOCS_BUILD_PLACEHOLDER",
    "WEBHOOK_HOST": "0.0.0.0",
    "WEBHOOK_PORT": "8080",
}
for key, value in _MOCK_ENV.items():
    os.environ.setdefault(key, value)

sys.path.insert(0, os.path.abspath(".."))

# -- Project information -----------------------------------------------------

project = "Discord Trello Bug Bot"
copyright = "2026, Piledriver Playhouse"
author = "Piledriver Playhouse"
release = "1.1.1"

# -- General configuration ---------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",        # Pull docstrings from Python modules
    "sphinx.ext.napoleon",       # Support Google/NumPy style docstrings
    "sphinx.ext.viewcode",       # Add [source] links next to documented objects
    "sphinx.ext.intersphinx",    # Cross-reference external Sphinx docs
    "myst_parser",               # Allow Markdown (.md) sources alongside .rst
]

# Markdown file support (in addition to .rst)
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

# Master document (Sphinx looks for this as the root of the toctree)
master_doc = "index"

# Patterns to exclude when looking for source files
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- Autodoc configuration ---------------------------------------------------

# Document both the class docstring and __init__ docstring
autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
}

# -- Napoleon configuration --------------------------------------------------

napoleon_google_docstring = True
napoleon_numpy_docstring = False

# -- Intersphinx configuration -----------------------------------------------

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "aiohttp": ("https://docs.aiohttp.org/en/stable/", None),
    "discord": ("https://discordpy.readthedocs.io/en/stable/", None),
}

# -- MyST-Parser configuration -----------------------------------------------

# Enable useful Markdown extensions for documentation authors.
myst_enable_extensions = [
    "colon_fence",       # ::: directive fences
    "deflist",           # definition lists
    "fieldlist",         # field lists
    "tasklist",          # - [x] task lists
]

# -- HTML output options ------------------------------------------------------

html_theme = "furo"                  # Modern, responsive Sphinx theme
html_title = "Discord Trello Bug Bot"
html_static_path = ["_static"]

# Furo theme options
html_theme_options = {
    "light_css_variables": {
        "color-brand-primary": "#5865F2",     # Discord blurple
        "color-brand-content": "#5865F2",
    },
    "dark_css_variables": {
        "color-brand-primary": "#7289DA",
        "color-brand-content": "#7289DA",
    },
    "sidebar_hide_name": False,
    "navigation_with_keys": True,
}
