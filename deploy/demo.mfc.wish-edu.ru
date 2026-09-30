
server {
    server_name demo.mfc.wish-edu.ru;

    location / {
        proxy_pass http://localhost:7702;
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
