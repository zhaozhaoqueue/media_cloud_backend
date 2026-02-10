sudo -u postgres psql

# Add user
# CREATE USER media_cloud WITH PASSWORD 'media_cloud';
# CREATE DATABASE media_cloud OWNER media_cloud;
# \q

vim /var/lib/pgsql/15/data/postgresql.conf
# listen_addresses = '*'

vim /var/lib/pgsql/15/data/pg_hba.conf
# host    all             all             172.16.0.0/12         md5

# reload pg15
sudo systemctl reload postgresql-15

