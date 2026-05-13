Troubleshooting
===============

Bot Does Not Respond
--------------------

* Verify the bot is **invited to the server** with the correct permissions.
* Check that ``BUG_CHANNEL_ID`` matches the channel you are posting in.
* Ensure **Message Content Intent** is enabled in the
  `Discord Developer Portal <https://discord.com/developers/applications>`_.
* Confirm the bot has *View Channels*, *Read Message History*,
  *Send Messages*, and *Add Reactions* permissions in the channel.

Trello Card Not Created
-----------------------

* Verify ``TRELLO_API_KEY`` and ``TRELLO_TOKEN`` are correct and have not
  expired.
* Verify ``TRELLO_LIST_ID`` points to a valid list on your board.
* Check the bot's stdout/stderr logs for the full error traceback.

Bot Works Locally but Not in k3s
---------------------------------

* Verify the Kubernetes Secret name matches ``bugbot-secrets``.
* Ensure **all five required** environment variables are present in the
  Secret.
* Confirm the container image in ``deployment.yaml`` matches the image you
  pushed to the registry.
* Inspect pod logs:

  .. code-block:: bash

     kubectl -n bugbot logs deploy/bugbot

``discord.py`` Privileged Intent Error
--------------------------------------

The ``message_content`` intent is classified as **privileged** by Discord.
If you see an error about intents:

1. Open the `Developer Portal <https://discord.com/developers/applications>`_.
2. Select your application → **Bot**.
3. Enable **Message Content Intent** under *Privileged Gateway Intents*.

Usage Examples
--------------

In the configured bug-report channel:

.. code-block:: text

   !bug Game crashes after selecting upgrade at the end of a floor

.. code-block:: text

   !bug Platform: Windows | Mode: Online client | Issue: Client freezes after upgrade selection

Suggested Channel Pin
^^^^^^^^^^^^^^^^^^^^^

Paste this in your bug-report channel and pin it:

   **Found a bug?**

   Use: ``!bug <describe the issue>``

   Please include platform, mode, what happened, what you expected,
   and reproduction steps if possible.

Security Notes
--------------

* **Never commit** ``.env`` — it is in ``.gitignore`` for a reason.
* **Never commit real values** in ``k8s/secret.example.yaml``.
* **Rotate credentials immediately** if your Discord token or Trello
  API key/token is exposed.
* Be careful with ``docker login`` credentials and GitHub Actions secrets
  when pushing container images.
