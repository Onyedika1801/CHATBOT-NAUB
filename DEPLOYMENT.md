# Deploying the NAUB Enquiry Chatbot

This project can be deployed to **Render** and/or **Replit** without one
interfering with the other — each platform only reads its own config file
(`render.yaml` for Render, `.replit`/`replit.nix` for Replit), and all the
production settings (`DEBUG`, `SECRET_KEY`, `ALLOWED_HOSTS`, `DATABASE_URL`)
are driven by environment variables with safe local defaults. Running it on
your own machine with `python manage.py runserver` is completely unaffected.

---

## Option 1: Render (recommended for a real, always-on deployment)

1. Push your code to GitHub (already done).
2. Go to [render.com](https://render.com) and sign up / log in with GitHub.
3. Click **New +** → **Blueprint**, and select this repository. Render will
   read `render.yaml` automatically and set up both:
   - A free PostgreSQL database (`naub-chatbot-db`)
   - A free web service (`naub-chatbot`) running `build.sh` then
     `gunicorn naub_chatbot.wsgi:application`
4. Render auto-generates a real `SECRET_KEY`, sets `DEBUG=False`, and wires
   `DATABASE_URL` to the Postgres instance for you — no manual steps needed.
5. Wait for the build to finish (a few minutes the first time). Your app
   will be live at `https://naub-chatbot.onrender.com` (or similar).
6. Create your admin/staff account directly on the deployed database via
   Render's **Shell** tab:
   ```bash
   python manage.py createsuperuser
   ```

**Note:** Render's free tier spins the service down after ~15 minutes of
inactivity and takes ~30-60 seconds to wake up on the next request. This is
normal for free tiers and fine for a project demo.

---

## Option 2: Replit (fastest for a quick demo / panel defense)

1. Go to [replit.com](https://replit.com) and sign up / log in.
2. Click **Create Repl** → **Import from GitHub**, and paste your repo URL.
3. Replit will detect `.replit` and `replit.nix` automatically.
4. Click **Run**. The first run will:
   - Install dependencies from `requirements.txt`
   - Run migrations and load the knowledge base
   - Start the server on port 8000 (Replit maps this to a public URL
     automatically, shown in the "Webview" panel)
5. To create an admin account, open the **Shell** tab in Replit and run:
   ```bash
   python manage.py createsuperuser
   ```

**Note:** Replit's free tier keeps SQLite as the database by default (no
`DATABASE_URL` needed) since its filesystem persists while the Repl is
active. `DEBUG` also stays `True` by default here for convenience during a
demo — if you want it hardened, add a **Secret** in Replit's sidebar named
`DEBUG` with value `False`, and another named `ALLOWED_HOSTS` with your
Repl's domain (shown in the Webview address bar).

---

## Running both at once

Nothing conflicts: Render uses its own Postgres database and Replit uses its
own SQLite file, so the two deployments have entirely separate data. Both
read from the same GitHub repo, so pushing an update to `main` and
redeploying (Render redeploys automatically on push; Replit needs you to
pull/re-run) will update both.

---

## Environment variables reference

| Variable | Local default | Render | Replit |
|---|---|---|---|
| `SECRET_KEY` | insecure placeholder | auto-generated | placeholder (set a Secret to override) |
| `DEBUG` | `True` | `False` | `True` (set a Secret to override) |
| `ALLOWED_HOSTS` | `*` | `.onrender.com` | `*` (set a Secret to override) |
| `DATABASE_URL` | not set (uses SQLite) | Postgres connection string (auto-wired) | not set (uses SQLite) |
