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

RUN useradd -m -u 1000 appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
