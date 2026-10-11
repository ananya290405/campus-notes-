# CampusNotes — repaired deployment package

CampusNotes is a Flask notes-sharing portal with upload, search, subject filters, and downloads.

## Fastest free online demo: Render

This package is prepared for Render's free web service.

1. Create a GitHub account if you don't have one.
2. Create a **new private repository** named `campusnotes` (recommended while you're learning).
3. Upload the contents of this folder to the repository root (`app.py`, `templates/`, `requirements.txt`, `render.yaml`, and `Procfile`).
4. Open https://render.com/ and sign in with GitHub.
5. Choose **New + → Blueprint** (or create a Web Service manually).
6. Select your repository. If using Blueprint, Render reads `render.yaml`. If using a manual Web Service, set:
   - Runtime: Python
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn app:app`
   - Health check path: `/health`
7. Deploy and open the URL Render provides.

## Important free-tier limitation

Without `BUCKET` and `TABLE`, CampusNotes runs in local demo mode and stores uploads in `local_data/`. On a free Render web service, the filesystem is ephemeral: uploaded files and JSON metadata can be lost after a restart, redeploy, or instance replacement. This is suitable for a short demonstration, not for a persistent real notes-sharing service.

For persistent storage, configure an S3 bucket and DynamoDB table and provide `BUCKET`, `TABLE`, and `AWS_REGION` environment variables. The hosting service also needs AWS permissions. Prefer a hosting environment with an attached IAM role when possible; do not put AWS access keys in source code or commit them to GitHub.

## Local test

```bash
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows PowerShell:
# .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Then open http://127.0.0.1:5000 and visit http://127.0.0.1:5000/health.

## App behavior

- Upload limit: 10 MB per request.
- Allowed extensions: PDF, DOC/DOCX, PPT/PPTX, TXT, PNG/JPG/JPEG, ZIP.
- Search by title or subject; filter by subject.
- Local demo storage is not durable on ephemeral hosts.
- `/health` returns `OK` for deployment health checks.

## Security and academic note

Use sample materials only. The app is a student prototype and has no user login or authorization for uploads; anyone who can reach the public app can upload files. Do not use it for private/confidential notes or real personal data without adding authentication, CSRF protection, moderation, and durable storage. The S3/DynamoDB code path is not active until the AWS resources and permissions are configured.
