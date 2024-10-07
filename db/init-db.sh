#!/bin/bash
set -e

# Definir variáveis de ambiente
DB_USER=${POSTGRES_USER}
DB_PASS=${POSTGRES_PASSWORD}
DB_NAME=${POSTGRES_DB}

# Criar as extensões no banco de dados definido em POSTGRES_DB
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$DB_NAME" <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS postgis;
    CREATE EXTENSION IF NOT EXISTS pgrouting;
    CREATE EXTENSION IF NOT EXISTS hstore;
EOSQL
