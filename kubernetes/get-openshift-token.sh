#!/bin/bash
TOKEN_NAME=$1
ENCODED_TOKEN=`oc get secrets/$TOKEN_NAME -o jsonpath="{.data.token}"`
export TOKEN=$(echo $ENCODED_TOKEN | base64 --decode)

echo ""
echo $TOKEN
echo ""