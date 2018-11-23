#
# Docker for the Alaya Backend Python Test
#

FROM python:3-slim-stretch

# Prevents TTY-related error messages.  Found at: https://github.com/docker/docker/issues/4032#issuecomment-192327844
ARG DEBIAN_FRONTEND=noninteractive

# Sets up software we need from other repos.
RUN apt-get update && apt-get install -y sqlite3

RUN pip --no-cache-dir install \
    docopt \
    flask

CMD /bin/bash
