"""CampusNotes - notes sharing portal.

Cloud mode  : set BUCKET and TABLE env vars -> uses Amazon S3 + DynamoDB
              (credentials come from the EC2 IAM role, never from code).
Local mode  : leave them unset -> uses ./local_data so you can test on a laptop.
"""
import json
import os
import socket
import time
import uuid
from datetime import datetime

from flask import (Flask, abort, flash, redirect, render_template, request,
                   send_from_directory, url_for)
from werkzeug.utils import secure_filename

BUCKET = os.environ.get("BUCKET")
TABLE = os.environ.get("TABLE")
REGION = os.environ.get("AWS_REGION", "ap-south-1")
CLOUD = bool(BUCKET and TABLE)

ALLOWED = {"pdf", "doc", "docx", "ppt", "pptx", "txt", "png", "jpg", "jpeg", "zip"}

app = Flask(__name__)
# Render generates SECRET_KEY from render.yaml. For local testing only, use a
# process-local random key if one has not been configured.
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(32)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB upload limit

if CLOUD:
    import boto3
    s3 = boto3.client("s3", region_name=REGION)
    table = boto3.resource("dynamodb", region_name=REGION).Table(TABLE)
else:
    DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "local_data")
    FILES_DIR = os.path.join(DATA_DIR, "files")
    DB_FILE = os.path.join(DATA_DIR, "notes.json")
    os.makedirs(FILES_DIR, exist_ok=True)


# ---------- storage layer ----------
def list_notes():
    if CLOUD:
        resp = table.scan()
        items = resp.get("Items", [])
        while "LastEvaluatedKey" in resp:
            resp = table.scan(ExclusiveStartKey=resp["LastEvaluatedKey"])
            items += resp.get("Items", [])
        return items
    if not os.path.exists(DB_FILE):
        return []
    with open(DB_FILE) as fh:
        return json.load(fh)


def save_note(item, fileobj):
    if CLOUD:
        s3.upload_fileobj(
            fileobj, BUCKET, item["s3_key"],
            ExtraArgs={"ServerSideEncryption": "AES256",
                       "ContentType": fileobj.mimetype or "application/octet-stream"})
        table.put_item(Item=item)
    else:
        fileobj.save(os.path.join(FILES_DIR, os.path.basename(item["s3_key"])))
        notes = list_notes()
        notes.append(item)
        with open(DB_FILE, "w") as fh:
            json.dump(notes, fh)


def get_note(note_id):
    if CLOUD:
        return table.get_item(Key={"note_id": note_id}).get("Item")
    return next((n for n in list_notes() if n["note_id"] == note_id), None)


# ---------- helpers ----------
@app.template_filter("datefmt")
def datefmt(ts):
    return datetime.fromtimestamp(int(ts)).strftime("%d %b %Y")


def allowed(name):
    return "." in name and name.rsplit(".", 1)[1].lower() in ALLOWED


# ---------- routes ----------
@app.route("/")
def index():
    q = request.args.get("q", "").strip().lower()
    subject = request.args.get("subject", "").strip().lower()
    notes = list_notes()
    subjects = sorted({n["subject"].strip() for n in notes}, key=str.lower)
    if subject:
        notes = [n for n in notes if n["subject"].strip().lower() == subject]
    if q:
        notes = [n for n in notes
                 if q in n["title"].lower() or q in n["subject"].lower()]
    notes.sort(key=lambda n: int(n["created"]), reverse=True)
    return render_template(
        "index.html", notes=notes, subjects=subjects, q=q, subject=subject,
        host=socket.gethostname(),
        mode="Amazon S3 + DynamoDB" if CLOUD else "local disk (demo mode)")


@app.route("/upload", methods=["POST"])
def upload():
    f = request.files.get("file")
    title = request.form.get("title", "").strip()
    subject = request.form.get("subject", "").strip()
    uploader = request.form.get("uploader", "").strip()
    if not (f and f.filename and title and subject and uploader):
        flash("Fill in every field and choose a file.", "error")
        return redirect(url_for("index"))
    if not f.filename.strip():
        flash("Choose a file before uploading.", "error")
        return redirect(url_for("index"))
    if not allowed(f.filename):
        flash("That file type is not allowed. Use PDF, Office files, TXT, PNG, JPG or ZIP.", "error")
        return redirect(url_for("index"))
    note_id = str(uuid.uuid4())
    filename = secure_filename(f.filename)
    item = {
        "note_id": note_id,
        "title": title[:100],
        "subject": subject[:50],
        "uploader": uploader[:50],
        "filename": filename,
        "s3_key": f"notes/{note_id}-{filename}",
        "created": int(time.time()),
    }
    save_note(item, f)
    flash(f"Uploaded \"{item['title']}\".", "ok")
    return redirect(url_for("index"))


@app.route("/download/<note_id>")
def download(note_id):
    item = get_note(note_id)
    if not item:
        abort(404)
    if CLOUD:
        url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": BUCKET, "Key": item["s3_key"],
                    "ResponseContentDisposition":
                        f'attachment; filename="{item["filename"]}"'},
            ExpiresIn=300)  # link works for 5 minutes only
        return redirect(url)
    return send_from_directory(FILES_DIR, os.path.basename(item["s3_key"]),
                               as_attachment=True, download_name=item["filename"])


@app.errorhandler(413)
def too_large(_):
    flash("File is larger than the 10 MB limit.", "error")
    return redirect(url_for("index"))


@app.route("/health")
def health():
    return "OK", 200


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=(os.environ.get("FLASK_DEBUG") == "1" and not CLOUD),
    )
