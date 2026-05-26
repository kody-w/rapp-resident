#!/usr/bin/env bash
# Deploy rapp-resident — the permanent cloud host — to Azure.
# Prereq: `az login` (as the account you want billed) + Azure Functions Core Tools v4.
# Override any value via env, e.g.:  APP=rapp-resident-kw LOCATION=eastus ./deploy.sh
set -euo pipefail

APP="${APP:-rapp-resident-$RANDOM}"          # globally-unique Function App name
RG="${RG:-rapp-resident-rg}"
LOCATION="${LOCATION:-eastus}"
STORAGE="${STORAGE:-rappresident$RANDOM}"    # 3-24 lowercase alnum, globally unique

echo "Deploying: app=$APP  rg=$RG  location=$LOCATION  storage=$STORAGE"
az account show --query "{user:user.name, sub:name}" -o table

# Everything below lives in this ONE resource group — delete the group to remove all of it.
az group create -n "$RG" -l "$LOCATION" \
  --tags purpose=rapp-resident project=rapp-commons owner=wildfeuer -o none
az storage account create -n "$STORAGE" -g "$RG" -l "$LOCATION" --sku Standard_LRS --allow-blob-public-access false -o none
# --disable-app-insights keeps the footprint minimal (no extra resource outside the group's intent)
az functionapp create -n "$APP" -g "$RG" --storage-account "$STORAGE" \
  --consumption-plan-location "$LOCATION" --runtime python --runtime-version 3.11 \
  --functions-version 4 --os-type Linux --disable-app-insights true -o none

# Public web UIs fetch this over CORS; the payload is signed data, no credentials.
az functionapp cors add -n "$APP" -g "$RG" --allowed-origins "*" -o none || true

func azure functionapp publish "$APP" --python

echo
echo "✅ deployed — everything is isolated in resource group: $RG"
az resource list -g "$RG" --query "[].{name:name, type:type}" -o table || true
echo
echo "   base   : https://$APP.azurewebsites.net/api"
echo "   health : https://$APP.azurewebsites.net/api/health"
echo "   commons: https://$APP.azurewebsites.net/api/rooms/commons/events"
echo
echo "   🧹 teardown (removes EVERYTHING above): az group delete -n $RG --yes --no-wait"
