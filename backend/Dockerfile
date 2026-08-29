FROM python:3.11.10-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . ./backend/

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Create the upload tree in the image, owned by the runtime user. Docker seeds
# a fresh named volume from the image's directory (contents and ownership), so
# without this the volume mounts as root-owned and the non-root process cannot
# write proofs or homework into it.
RUN mkdir -p /app/uploads/shop /app/uploads/proofs /app/uploads/homework

# CockroachDB Cloud's CA cert (public, vendored at backend/certs/root.crt).
# libpq looks in ~/.postgresql/root.crt by default, so sslmode=verify-full
# works without an sslrootcert query param.
RUN useradd -m -u 1000 appuser \
    && mkdir -p /home/appuser/.postgresql \
    && cp /app/backend/certs/root.crt /home/appuser/.postgresql/root.crt \
    && chown -R appuser /app /home/appuser/.postgresql
USER appuser

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
