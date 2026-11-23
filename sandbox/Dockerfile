# The image every sandbox the agent's code runs in starts from (Session 5). OpenSandbox adds its own execd program
# to each sandbox when it starts it.
#
# Python and the four libraries the agent's code is allowed to use: pandas for tables, matplotlib for charts,
# Pillow for pictures, numpy under all three. Nothing is installed at run time: the sandbox has no network, so what
# is not in this image is not there. `uv run launchkit setup` builds it once, which needs the internet.

FROM python:3.12-slim

RUN pip install --no-cache-dir pandas==2.2.3 matplotlib==3.9.2 pillow==11.0.0 numpy==2.1.3

# The code runs as the host's own user, not root, so the libraries' caches go to /tmp.
ENV MPLCONFIGDIR=/tmp HOME=/tmp PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

WORKDIR /work
