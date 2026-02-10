# create the directory for the backend code
mkdir -p /opt/media_cloud/backend
cd /opt/media_cloud/backend

# build the docker image and upload to the directory
## docker buildx build --platform linux/amd64 -t media_cloud_backend:0.3 \
##  --output type=docker,dest=media_cloud_backend_0.3_amd64.tar .

# upload the required files to the directory
## - flyway/sql/*.sql
## - .env.prod
## - media_cloud_backend_0.3_amd64.tar
## - docker-compose.yaml

# load the image
## docker load -i //opt/media_cloud/backend/media_cloud_backend_0.3_amd64.tar


# Init script
psql -v ON_ERROR_STOP=1 \
  -h 127.0.0.1 -p 5432 \
  -U media_cloud -d media_cloud \
  -f /opt/media_cloud/backend/flyway/sql/V1__init.sql

psql -v ON_ERROR_STOP=1 \
  -h 127.0.0.1 -p 5432 \
  -U media_cloud -d media_cloud \
  -f /opt/media_cloud/backend/flyway/sql/V2__file_upload_tokens.sql

# start the service
APP_ENV_FILE=.env.prod docker compose --env-file .env.prod up -d