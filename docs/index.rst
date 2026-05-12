Discord Trello Bug Bot
======================

A lightweight Discord bot that turns ``!bug`` messages into Trello cards —
built for private game repos where public GitHub Issues aren't desired.

.. toctree::
   :maxdepth: 2
   :caption: Contents

   getting-started
   configuration
   deployment
   api
   troubleshooting

Overview
--------

Users type ``!bug <report>`` in a designated Discord channel. The bot
creates a Trello card in a configured list with the full report text,
reporter info, and a link back to the original Discord message.

* **No database required** — stateless and lightweight.
* **Attachments Sync** — automatically uploads screenshots to Trello.
* **Discord Threads** — keeps conversations organized.
* **Web Dashboard** — real-time monitoring of logs and bot health.

Quick Start
-----------

.. code-block:: bash

   # Clone & set up
   git clone https://github.com/Piledriver-Playhouse/Discord-Trello-Bug-Bot.git
   cd Discord-Trello-Bug-Bot
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt

   # Configure
   cp .env.example .env
   # Edit .env with your real credentials

   # Run
   python -m bugbot.main

Indices and Tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
