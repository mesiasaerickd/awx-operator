# Rebuild the upstream ansible-operator binary from the exact v1.42.3 source commit.
# Only development builds use this candidate; the runtime image stays unchanged.
FROM golang:1.26.9 AS patched-ansible-operator
RUN git clone https://github.com/operator-framework/ansible-operator-plugins.git /src
WORKDIR /src
RUN git checkout --detach 292a56a4877c8093037c0533f3ef3c7a6bbd78e2 && \
    go get golang.org/x/net@v0.60.0 golang.org/x/text@v0.42.0 google.golang.org/grpc@v1.83.2 && \
    go mod tidy && \
    CGO_ENABLED=0 go build -trimpath -o /out/ansible-operator ./cmd/ansible-operator

FROM quay.io/operator-framework/ansible-operator:v1.42.3

USER root
COPY --from=patched-ansible-operator /out/ansible-operator /usr/local/bin/ansible-operator
RUN microdnf update -y && \
    microdnf install -y openssl

# Development security candidate: update installed Python distributions in place.
# Do not ignore dependency conflicts; CI verifies resolver consistency.
# Bootstrap pip from a dedicated build stage. Keep pip installed because
# the inherited pip-api 0.0.34 distribution declares a dependency on pip.
# Check runtime Python dependency consistency before accepting the image.
COPY --from=python:3.12-slim /usr/local/lib/python3.12/site-packages/pip/ /tmp/bootstrap-pip/pip/
RUN PYTHONPATH=/tmp/bootstrap-pip python3 -m pip install --no-cache-dir \
    'pip==25.3' \
    'pyasn1==0.6.4' \
    'urllib3==2.8.0' \
    'virtualenv==21.7.13' \
    'cryptography==50.0.0' && \
    python3 -m pip check && \
    rm -rf /tmp/bootstrap-pip


USER 1001

ARG DEFAULT_AWX_VERSION
ARG OPERATOR_VERSION
ENV DEFAULT_AWX_VERSION=${DEFAULT_AWX_VERSION}
ENV OPERATOR_VERSION=${OPERATOR_VERSION}

COPY requirements.yml ${HOME}/requirements.yml
RUN ansible-galaxy collection install -r ${HOME}/requirements.yml \
 && chmod -R ug+rwx ${HOME}/.ansible

COPY watches.yaml ${HOME}/watches.yaml
COPY roles/ ${HOME}/roles/
COPY playbooks/ ${HOME}/playbooks/

ENTRYPOINT ["/tini", "--", "/usr/local/bin/ansible-operator", "run", \
    "--watches-file=./watches.yaml", \
    "--reconcile-period=0s" \
    ]
