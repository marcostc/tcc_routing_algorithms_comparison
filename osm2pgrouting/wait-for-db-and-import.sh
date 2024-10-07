#!/bin/bash
set -e

echo "DB_HOST é '$DB_HOST'"

# Esperar até que o PostgreSQL esteja disponível
until pg_isready -h "$DB_HOST" -p 5432 -U "$DB_USER"; do
  echo "Aguardando o PostgreSQL ficar disponível..."
  sleep 5
done

echo "PostgreSQL disponível - iniciando a importação com osm2pgrouting"

osm2pgrouting \
    -f /data/rio_de_janeiro_parte.osm \
    -c /data/mapconfig.xml \
    -d "$DB_NAME" \
    -U "$DB_USER" \
    -h "$DB_HOST" \
    -p 5432 \
    -W "$DB_PASS" \
    --clean

echo "Importação concluída com sucesso"
