
server {
	server_name mini-app.wish-edu.ru;
    charset utf-8;

	location / {
        proxy_pass http://127.0.0.1:8003;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_cache_bypass $http_upgrade;
    }

    location /api {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_cache_bypass $http_upgrade;
    }


    gzip on;
    gzip_types text/plain application/javascript application/x-javascript text/javascript text/css application/json;
    gzip_proxied any;
    gzip_vary on;


}


server
        {
    if ($host = mini-app.wish-edu.ru) {
        return 301 https://$host$request_uri;
    } # managed by Certbot


		server_name mini-app.wish-edu.ru;
    listen 80;
    return 404; # managed by Certbot


}
