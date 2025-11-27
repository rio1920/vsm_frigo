#!/bin/bash
export UID=$(id -u)
export GID=$(id -g)
docker compose -f docker-compose.prod.yaml down && docker compose -f docker-compose.prod.yaml up --build -d