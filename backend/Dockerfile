# ── Build stage ───────────────────────────────────────────────────────────────
# Dependencies are resolved into a self-contained virtualenv here and copied
# into the runtime image below. Nothing in requirements.txt carries a C
# extension — every pin resolves to a manylinux wheel except pywebpush, which
# is pure Python — so this stage needs no compiler toolchain. Keeping the
# install in its own stage leaves pip's metadata and any future build-time
# apt package out of the shipped image.
FROM python:3.11.10-slim-bookworm AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.11.10-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv

COPY . ./backend/

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Create the upload tree in the image, owned by the runtime user. Docker seeds
# a fresh named volume from the image's directory (contents and ownership), so
# without this the volume mounts as root-owned and the non-root process cannot
# write proofs or homework into it. Hosts with an ephemeral filesystem (Render)
# use object storage instead and never touch this tree.
RUN mkdir -p /app/uploads/shop /app/uploads/proofs /app/uploads/homework

# CockroachDB Cloud's CA cert (public, vendored at backend/certs/root.crt).
# libpq looks in ~/.postgresql/root.crt by default, so sslmode=verify-full
# works without an sslrootcert query param. Unused when the database is
# Supabase, whose pooler is happy with plain sslmode=require.
RUN useradd -m -u 1000 appuser \
    && mkdir -p /home/appuser/.postgresql \
    && cp /app/backend/certs/root.crt /home/appuser/.postgresql/root.crt \
    && chown -R appuser /app /home/appuser/.postgresql
USER appuser

# Documentation only, and the port the entrypoint falls back to. Render injects
# its own PORT and the entrypoint binds that instead.
EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
