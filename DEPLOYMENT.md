# Deploy MKP Kitchen Design Studio

## Free preview: Streamlit Community Cloud

1. Create a new GitHub repository for this app, separate from church_streamlit.
   Upload the contents of the deployment ZIP into its root (not inside a subfolder).
   The ZIP excludes customer jobs, uploads, videos, credentials and research files.
2. Sign in at https://share.streamlit.io/ using GitHub. Select **Create app**,
   the new repository and branch, and `app.py` as the main file. Choose Python 3.12.
3. In the app's advanced settings, paste these lines into **Secrets**, replacing
   the placeholder with your own long password:

   ```toml
   KITCHEN_REQUIRE_PASSWORD = "true"
   KITCHEN_APP_PASSWORD = "REPLACE_WITH_YOUR_OWN_LONG_PASSWORD"
   ```

   Optional: add `KITCHEN_VISION_API_KEY` here. Never put real secrets in GitHub.
4. Deploy. `requirements.txt` installs Python dependencies and `packages.txt`
   installs OCR, PDF and video tools. Open the service's HTTPS app address and
   sign in with the password configured in Secrets.
5. Verify room confirmation, upload a sample supplier spreadsheet, generate a
   quotation and a short video. Download important results immediately.

Free hosting uses temporary local storage. Jobs, supplier updates, and videos may
disappear on restart or redeployment. This is a preview, not the business archive.
Online checks run through the manual refresh button; an always-on daily price
worker is not available on this free setup.

## Container deployment with persistent storage

The container includes PDF reading, OCR, interactive 3D and video dependencies.
Build from this directory with `docker build -t mkp-kitchen .`.

Use a single instance with a persistent disk mounted at `/data`, writable by
UID 10001. Customer jobs, uploaded supplier updates, videos and online price
observations are stored there. Existing workspace jobs are deliberately excluded
from the image; migrate them separately over a secure connection if needed.
Back up this disk regularly, including immutable quotation revisions.

Set `KITCHEN_APP_PASSWORD` through the hosting provider's secret settings. This
is a shared owner password for the prototype, not customer accounts. The container
refuses to start without it. Use provider HTTPS with WebSocket support; never expose
the app over plain HTTP. A managed host should route to port 8501 (or its injected
PORT) and check `/_stcore/health`.

Optional: set `KITCHEN_VISION_API_KEY` through secret settings for AI reading.
Never commit passwords, keys, real customer files or `.env` files.

Start one daily scheduled command `python /app/price_watch.py` in the same
container environment with the same persistent disk. Manual price refresh remains
available in the app. Do not use multiple replicas: the current JSON storage is
designed for one instance with local file locks.

For an existing Docker server, build the image, supply secrets with a protected
environment file, and run:

```sh
docker volume create mkp-data
docker run -d --name mkp-kitchen --restart unless-stopped \
  --env-file /secure/path/mkp.env \
  -v mkp-data:/data -p 127.0.0.1:8501:8501 mkp-kitchen
```

Place an HTTPS reverse proxy in front of the loopback port. Configure the actual
domain and TLS using the server's existing proxy. Do not publish port 8501 directly.

The deployment package has not yet been published to a host. A hosting account
and an authorised destination are needed to obtain a public address.
