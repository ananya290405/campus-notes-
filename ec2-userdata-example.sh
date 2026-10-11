#!/bin/bash
# EC2 Launch Template -> Advanced details -> User data
# Edit the 3 values marked CHANGE-ME before pasting.
dnf install -y python3-pip git
cd /opt
git clone https://github.com/CHANGE-ME-USERNAME/campusnotes.git
cd campusnotes
pip3 install -r requirements.txt

cat > /etc/systemd/system/campusnotes.service <<'UNIT'
[Unit]
Description=CampusNotes
After=network.target

[Service]
WorkingDirectory=/opt/campusnotes
Environment=BUCKET=CHANGE-ME-BUCKET-NAME
Environment=TABLE=CampusNotes
Environment=AWS_REGION=ap-south-1
Environment=SECRET_KEY=CHANGE-ME-RANDOM-TEXT
ExecStart=/usr/local/bin/gunicorn -w 2 -b 0.0.0.0:80 app:app
Restart=always

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable --now campusnotes

# NOTE: EC2-only example with placeholders; do not use for Render deployment.
