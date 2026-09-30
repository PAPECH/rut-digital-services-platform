server
        {
		server_name demo.bot.wish-edu.ru;
        charset utf-8;
		
	location / {
    proxy_pass http://127.0.0.1:7700/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
}

