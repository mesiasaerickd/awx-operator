FROM quay.io/operator-framework/ansible-operator:v1.42.3

USER root
RUN microdnf update -y && \
    microdnf install -y openssl

# Development security candidate: update installed Python distributions in place.
# Do not ignore dependency conflicts; CI verifies resolver consistency.
RUN python3 -m pip install --no-cache-dir \
    'pyasn1==0.6.4' \
    'urllib3==2.8.0' \
    'virtualenv==21.7.13' \
    'cryptography==50.0.0' && \
    python3 -m pip check

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
