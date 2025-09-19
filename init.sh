#!/bin/bash

source common.sh

source ${AZURE_ENV}/bin/activate

if [ -e ${SECRETS_FILE} ]; then
	source ${SECRETS_FILE}
fi

if az account get-access-token --output none 2>/dev/null; then
	echo "Using existing token; expiry: $(az account get-access-token --query "expiresOn" --output tsv)"
else
	az login --use-device-code
fi
