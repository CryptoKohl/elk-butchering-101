# Shared by the http (8090) and https (8443) servers in nginx.conf.
root /usr/share/nginx/html;
index index.html;
client_max_body_size 20m;
location /api/ { proxy_pass http://127.0.0.1:8091; proxy_read_timeout 300s; }
location ^~ /uploads/ { location ~ \.json$ { deny all; } }
location ^~ /photos/2026-elk/raw/ { deny all; }
location ~ /\. { deny all; }
location ~ \.(py|yaml|conf|inc|md)$ { deny all; }
location ~ \.(json|csv|webmanifest)$ { add_header Cache-Control "no-cache"; }
location = /sw.js { add_header Cache-Control "no-cache"; }
# The home CA's public certificate, for the one-time phone setup (setup.html).
location = /elk-ca.crt { alias /etc/nginx/ca/elk-ca.crt; types { } default_type application/x-x509-ca-cert; }
location = /elk-ca.cer { alias /etc/nginx/ca/elk-ca.cer; types { } default_type application/x-x509-ca-cert; }
