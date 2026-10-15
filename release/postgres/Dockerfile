# NON-PRODUCTION LAB ONLY. Preserve SCL entrypoint, POSTGRESQL_* variables and UID 26.
# CentOS Stream 9 repos do not provide upstream PostgreSQL 15.19 yet.
# ONLY PostgreSQL-family RPMs are updated from signed Rocky Linux 9 AppStream.
# Cross-vendor RPM overlays REQUIRE an independent security/support review
# before any production use. No AWX PVC may be mounted during CI.
ARG BASE_IMAGE=quay.io/sclorg/postgresql-15-c9s:latest
FROM ${BASE_IMAGE}
USER 0
RUN curl -fsSLo /etc/pki/rpm-gpg/RPM-GPG-KEY-Rocky-9 \
      https://dl.rockylinux.org/pub/rocky/RPM-GPG-KEY-Rocky-9 && \
    printf '[rocky-pg15-lab]\nname=Rocky Linux 9 AppStream (isolated PG15 packages)\nbaseurl=https://dl.rockylinux.org/pub/rocky/9/AppStream/x86_64/os/\nenabled=0\ngpgcheck=1\ngpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-Rocky-9\nmodule_hotfixes=1\n' \
      > /etc/yum.repos.d/rocky-pg15-lab.repo && \
    yum -y --refresh --enablerepo=rocky-pg15-lab install \
      'postgresql-15.19*' 'postgresql-server-15.19*' \
      'postgresql-contrib-15.19*' 'postgresql-upgrade-15.19*' \
      'postgresql-private-libs-15.19*' && \
    yum clean all && \
    rpm -q postgresql-server postgresql-contrib && \
    test "$(postgres --version | awk '{print $3}')" = "15.19" && \
    test "$(id -u postgres)" = "26" && \
    test -x /usr/bin/run-postgresql && \
    rm -f /etc/yum.repos.d/rocky-pg15-lab.repo
USER 26
