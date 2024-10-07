#!/bin/bash
set -e

echo "DB_HOST é '$DB_HOST'"

host="$DB_HOST"

if [ -z "$host" ]; then
  echo "Variável DB_HOST não está definida. Saindo."
  exit 1
fi

until PGPASSWORD="$DB_PASS" psql -h "$host" -U "$DB_USER" -d "$DB_NAME" -c '\q'; do
  >&2 echo "Banco de dados não está disponível ainda - aguardando"
  sleep 5
done

>&2 echo "Banco de dados está disponível - iniciando a aplicação"
exec "$@"
