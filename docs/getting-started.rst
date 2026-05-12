Getting Started
===============

This guide walks you through creating the Discord bot, configuring Trello,
and running the bot locally for the first time.

Prerequisites
-------------

* **Python 3.12+**
* A **Discord** account with permission to add bots to a server
* A **Trello** account with at least one board

Discord Setup
-------------

1. Go to the `Discord Developer Portal <https://discord.com/developers/applications>`_.
2. Click **New Application** and give it a name (e.g. ``Bug Bot``).
3. Navigate to **Bot** in the sidebar and click **Add Bot**.
4. Copy the **Bot Token** — this is your ``DISCORD_TOKEN``.
5. Under *Privileged Gateway Intents*, **enable Message Content Intent**.
6. Go to **OAuth2 → URL Generator**:

   * *Scopes*: select **bot**
   * *Bot Permissions*: select **View Channels**, **Read Message History**,
     **Send Messages**, and **Add Reactions**
   * Copy the generated URL and open it to invite the bot to your server.

Getting the Channel ID
^^^^^^^^^^^^^^^^^^^^^^

1. Open Discord **Settings → Advanced** and enable **Developer Mode**.
2. Right-click the target channel → **Copy Channel ID**.
3. This value is your ``BUG_CHANNEL_ID``.

Trello Setup
------------

Get your API Key
^^^^^^^^^^^^^^^^

1. Visit `Trello Power-Ups Admin <https://trello.com/power-ups/admin>`_.
2. Create a new Power-Up (or use an existing one).
3. Copy the **API Key** → ``TRELLO_API_KEY``.

Generate a Token
^^^^^^^^^^^^^^^^

On the same API Key page, click the link to generate a token, or visit::

   https://trello.com/1/authorize?expiration=never&scope=read,write&response_type=token&key=YOUR_API_KEY

Authorise and copy the token → ``TRELLO_TOKEN``.

Create a Board and List
^^^^^^^^^^^^^^^^^^^^^^^

1. Create or open a Trello board.
2. Add a list called **Bugs** (or any name you prefer).

Get the List ID
^^^^^^^^^^^^^^^

**Method A — Board JSON (easiest):**

1. Open the board in a browser.
2. Append ``.json`` to the URL, e.g.
   ``https://trello.com/b/ABC123/my-board.json``
3. Search for ``"name":"Bugs"`` and copy the adjacent ``"id"`` value.

**Method B — Trello API:**

.. code-block:: bash

   curl "https://api.trello.com/1/boards/BOARD_ID/lists?key=KEY&token=TOKEN" \
     | python -m json.tool

Find the list named "Bugs" and copy its ``id`` → ``TRELLO_LIST_ID``.

Local Installation
------------------

.. code-block:: bash

   # Create and activate a virtual environment
   python -m venv .venv
   source .venv/bin/activate   # Linux / macOS
   # .venv\Scripts\activate    # Windows

   # Install runtime dependencies
   pip install -r requirements.txt

   # Copy and edit the environment file
   cp .env.example .env
   # Fill in your real credentials

   # Start the bot
   python -m bugbot.main

The bot uses `python-dotenv <https://pypi.org/project/python-dotenv/>`_ to
load ``.env`` automatically when running locally.
