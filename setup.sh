#!/bin/bash

source common.sh

python3 -m venv ${AZURE_ENV}
source ${AZURE_ENV}/bin/activate

python3 -m pip install azure-identity aiohttp
python3 -m pip install --pre azure-ai-projects
python3 -m pip install azure-cli

if [ ! -e ${SECRETS_FILE} ]; then
	cat << 'EOF' > ${SECRETS_FILE}
#!/bin/bash
export PROJECT_ENDPOINT=
export MODEL_DEPLOYMENT_NAME=
export DEEP_RESEARCH_MODEL_DEPLOYMENT_NAME=
export BING_RESOURCE_NAME=
EOF
fi

