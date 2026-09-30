
server {
    server_name rut.wish-edu.ru;

    location / {
        proxy_pass http://0.0.0.0:7902;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    gzip on;
    gzip_types text/plain application/javascript application/x-javascript text/javascript text/css application/json;
    gzip_proxied any;
    gzip_vary on;


}

server {
    if ($host = rut.wish-edu.ru) {
        return 301 https://$host$request_uri;
    } # managed by Certbot


    server_name rut.wish-edu.ru;
    listen 80;
    return 404; # managed by Certbot


}
