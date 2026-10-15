# AWX Operator-compatible PostgreSQL 15.19 candidate, not a generic postgres:15 image.
# Preserve SCL image contracts: UID 26, data path and POSTGRESQL_* environment.
ARG BASE_IMAGE=quay.io/sclorg/postgresql-15-c9s:latest
FROM ${BASE_IMAGE}
USER 0
RUN yum -y --refresh upgrade && \
    yum clean all && \
    test "$(postgres --version | awk '{print $3}')" = "15.19" && \
    test "$(id -u postgres)" = "26" && \
    test -x /usr/bin/run-postgresql
USER 26
