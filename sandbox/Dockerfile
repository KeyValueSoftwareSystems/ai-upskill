# The image every run of the agent's code starts from (Session 5, stage 2 on).
#
# Python and the four libraries the agent's code is allowed to use: pandas for tables, matplotlib for charts,
# Pillow for pictures, numpy under all three. Nothing is installed at run time: the sandbox has no network, so what
# is not in this image is not there. `uv run launchkit setup` builds it once, which needs the internet.

FROM python:3.12-slim

RUN pip install --no-cache-dir pandas==2.2.3 matplotlib==3.9.2 pillow==11.0.0 numpy==2.1.3

# The container's root disk is read-only when it runs, and its user is not root, so the libraries' caches go to /tmp,
# the one writable place outside /work.
ENV MPLCONFIGDIR=/tmp HOME=/tmp PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

WORKDIR /work
