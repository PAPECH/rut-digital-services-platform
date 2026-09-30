server
        {
		server_name bots.wish-edu.ru;
        charset utf-8;

	location / {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

}


server
        {
    if ($host = bots.wish-edu.ru) {
        return 301 https://$host$request_uri;
    } # managed by Certbot


		server_name bots.wish-edu.ru;
    listen 80;
    return 404; # managed by Certbot


}
