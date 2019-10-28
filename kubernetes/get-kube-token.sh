#!/bin/bash
SA_NAME=wopr
export TOKEN=$(kubectl get secrets -o jsonpath="{.items[?(@.metadata.annotations['kubernetes\.io/service-account\.name']=='$SA_NAME')].data.token}"|base64 -d)

echo ""
echo $TOKEN
echo ""