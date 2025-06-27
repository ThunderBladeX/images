#!/bin/bash

set -e

echo "Building the project..."

pip install -r requirements.txt

echo "Running database migrations..."
alembic upgrade head

echo "Build finished."
