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

* No database required
* No web server or inbound webhooks
* Outbound connections only (Discord gateway + Trello REST API)

Quick Start
-----------

.. code-block:: bash

   # Clone & set up
   git clone https://github.com/YOUR_ORG/arcascian-bugbot.git
   cd arcascian-bugbot
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt

   # Configure
   cp .env.example .env
   # Edit .env with your real credentials

   # Run
   python bot.py

Indices and Tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
