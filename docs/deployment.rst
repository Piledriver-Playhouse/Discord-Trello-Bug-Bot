Deployment
==========

The bot can be deployed locally, in Docker, or on Kubernetes / k3s.
It only makes outbound connections so no Service, Ingress, or port
exposure is required.

Docker
------

Build and Run
^^^^^^^^^^^^^

.. code-block:: bash

   # Build the image
   docker build -t arcascian-bugbot:latest .

   # Run with your .env file
   docker run --env-file .env arcascian-bugbot:latest

Docker Compose
^^^^^^^^^^^^^^

.. code-block:: bash

   docker compose up --build

The Compose file reads variables from ``.env`` in the project root and
restarts the container automatically on failure.

.. literalinclude:: ../docker-compose.yml
   :language: yaml
   :caption: docker-compose.yml

Publishing to GitHub Container Registry
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Authenticate (once)
   echo $GHCR_TOKEN | docker login ghcr.io -u YOUR_USERNAME --password-stdin

   # Build and push
   docker build -t ghcr.io/piledriver-playhouse/discord-trello-bug-bot:latest .
   docker push ghcr.io/piledriver-playhouse/discord-trello-bug-bot:latest

Kubernetes / k3s
-----------------

All manifests live in the ``k8s/`` directory.

1. Create the Namespace
^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   kubectl apply -f k8s/namespace.yaml

.. literalinclude:: ../k8s/namespace.yaml
   :language: yaml
   :caption: k8s/namespace.yaml

2. Create the Secret
^^^^^^^^^^^^^^^^^^^^^

.. warning::

   Never commit real secret values to version control. Use
   ``kubectl create secret`` or a secrets manager.

.. code-block:: bash

   kubectl -n arcascian-tools create secret generic arcascian-bugbot-secrets \
     --from-literal=DISCORD_TOKEN='...' \
     --from-literal=BUG_CHANNEL_ID='...' \
     --from-literal=TRELLO_API_KEY='...' \
     --from-literal=TRELLO_TOKEN='...' \
     --from-literal=TRELLO_LIST_ID='...'

See ``k8s/secret.example.yaml`` for the structure:

.. literalinclude:: ../k8s/secret.example.yaml
   :language: yaml
   :caption: k8s/secret.example.yaml

3. Apply the Deployment
^^^^^^^^^^^^^^^^^^^^^^^^

Apply the manifests natively:

.. code-block:: bash

   kubectl apply -f k8s/deployment.yaml

Or use a GitOps controller like **ArgoCD** to sync the ``k8s/`` directory. If your GHCR image is private, ensure you also create an ``imagePullSecret`` and reference it in the deployment manifest.

.. literalinclude:: ../k8s/deployment.yaml
   :language: yaml
   :caption: k8s/deployment.yaml

4. Verify
^^^^^^^^^

.. code-block:: bash

   # Watch logs
   kubectl -n arcascian-tools logs deploy/arcascian-bugbot -f

   # Check pod status
   kubectl -n arcascian-tools get pods
