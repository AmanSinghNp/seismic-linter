FROM python:3.11-slim

# Install git to support pip install from git if needed
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Install seismic-linter
# We assume the context sent to docker build includes the repo, 
# or we install from PyPI. For an action in the repo itself, 
# usually it installs 'from .'
COPY . /app
WORKDIR /app
RUN pip install .
RUN chmod +x /app/scripts/entrypoint.sh

ENTRYPOINT ["/app/scripts/entrypoint.sh"]
