sudo mkdir -p /etc/nginx/ssl/media-cloud
sudo chmod 700 /etc/nginx/ssl/media-cloud
# upload the ssl certificates
# add config file
vim /etc/nginx/conf.d/media-cloud-nginx.conf
# reload nginx and check
sudo nginx -t
sudo systemctl reload nginx