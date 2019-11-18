#!/bin/bash
SA_NAME=wopr
export TOKEN=$(kubectl get secrets -n wopr -o jsonpath="{.items[?(@.metadata.annotations['kubernetes\.io/service-account\.name']=='$SA_NAME')].data.token}"|base64 --decode)

echo ""
echo $TOKEN
echo ""
