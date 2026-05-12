Configuration
=============

The bot is configured entirely through **environment variables**. No config
files are required. When running locally, variables are loaded from a
``.env`` file via ``python-dotenv``. In Docker and Kubernetes the same
variables are injected through ``env_file`` / ``envFrom`` respectively.

Required Variables
------------------

These must be set or the bot will exit with a clear error at startup.

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Variable
     - Description
   * - ``DISCORD_TOKEN``
     - Bot token from the Discord Developer Portal.
   * - ``BUG_CHANNEL_ID``
     - Numeric Discord channel ID where the bot listens for ``!bug``.
   * - ``TRELLO_API_KEY``
     - Trello API key from the Power-Ups admin page.
   * - ``TRELLO_TOKEN``
     - Trello authorisation token with read/write scope.
   * - ``TRELLO_LIST_ID``
     - ID of the Trello list where cards are created.

Optional Variables
------------------

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Variable
     - Default
     - Description
   * - ``COMMAND_PREFIX``
     - ``!``
     - Prefix character(s) for Discord commands.
   * - ``CARD_TITLE_PREFIX``
     - ``Bug:``
     - String prepended to every Trello card title.
   * - ``LOG_LEVEL``
     - ``INFO``
     - Python logging level (``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``).

Example ``.env`` File
---------------------

.. literalinclude:: ../.env.example
   :language: bash
   :caption: .env.example
