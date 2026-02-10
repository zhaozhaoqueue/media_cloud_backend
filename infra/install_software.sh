# CentOS 7.6
## update os
yum clean all
yum makecache fast
yum update -y
reboot

## basic tools
yum install -y \
  vim curl wget git unzip \
  ca-certificates \
  yum-utils

## Install PG15
### disable pg
yum-config-manager --disable pgdg12
### install
yum install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-7-x86_64/pgdg-redhat-repo-latest.noarch.rpm
yum install -y postgresql15-server
### initialize the database and enable automatic start
/usr/pgsql-15/bin/postgresql-15-setup initdb
systemctl enable postgresql-15
systemctl start postgresql-15
### check status
systemctl status postgresql-15


## Install Docker
yum-config-manager \
  --add-repo \
  https://download.docker.com/linux/centos/docker-ce.repo
yum install -y \
  docker-ce \
  docker-ce-cli \
  containerd.io \
  docker-compose-plugin
systemctl enable --now docker
docker ps

## Install Nginx
yum install -y nginx
systemctl enable --now nginx
setsebool -P httpd_can_network_connect on