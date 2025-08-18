#!/bin/bash

source common.sh

source ${AZURE_ENV}/bin/activate

if [ -e ${SECRETS_FILE} ]; then
	source ${SECRETS_FILE}
fi
