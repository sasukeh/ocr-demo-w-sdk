#!/bin/bash

# APIM API Setup Script
# This script creates the Computer Vision API in APIM

set -e

# Configuration
RESOURCE_GROUP="rg-ocr-demo-japan-east"
APIM_NAME="ocr-demo-apim-dev"
API_ID="computer-vision-ocr"
API_DISPLAY_NAME="Computer Vision OCR"
API_PATH="ocr"
SERVICE_URL="https://cv-ocr-demo-je-primary.cognitiveservices.azure.com"

echo "=== APIM API Setup ==="
echo "Resource Group: $RESOURCE_GROUP"
echo "APIM Name: $APIM_NAME"
echo "API ID: $API_ID"
echo "Service URL: $SERVICE_URL"
echo

# Check if API already exists
echo "Checking if API exists..."
API_EXISTS=$(az apim api show --resource-group "$RESOURCE_GROUP" --service-name "$APIM_NAME" --api-id "$API_ID" --query "name" -o tsv 2>/dev/null || echo "")

if [ -n "$API_EXISTS" ]; then
    echo "API $API_ID already exists. Updating..."
else
    echo "Creating new API $API_ID..."
    
    # Create API
    az apim api create \
        --resource-group "$RESOURCE_GROUP" \
        --service-name "$APIM_NAME" \
        --api-id "$API_ID" \
        --display-name "$API_DISPLAY_NAME" \
        --path "$API_PATH" \
        --service-url "$SERVICE_URL" \
        --protocols https
    
    echo "API $API_ID created successfully."
fi

# Add OCR operation
echo "Adding OCR operation..."
az apim api operation create \
    --resource-group "$RESOURCE_GROUP" \
    --service-name "$APIM_NAME" \
    --api-id "$API_ID" \
    --operation-id "analyze-read" \
    --display-name "Analyze Document" \
    --method "POST" \
    --url-template "/formrecognizer/documentModels/prebuilt-read:analyze?api-version=2024-02-29-preview" \
    --description "OCR analysis using prebuilt read model"

echo "Operation created successfully."

# Create backend pool for load balancing
echo "Creating backend pool..."

# Create backends for each Computer Vision endpoint
ENDPOINTS=(
    "cv-ocr-demo-je-primary"
    "cv-ocr-demo-je-secondary" 
    "cv-ocr-demo-je-tertiary"
)

for endpoint in "${ENDPOINTS[@]}"; do
    BACKEND_ID="backend-$endpoint"
    BACKEND_URL="https://$endpoint.cognitiveservices.azure.com"
    
    echo "Creating backend: $BACKEND_ID"
    az apim backend create \
        --resource-group "$RESOURCE_GROUP" \
        --service-name "$APIM_NAME" \
        --backend-id "$BACKEND_ID" \
        --url "$BACKEND_URL" \
        --protocol "http" \
        --title "$endpoint Backend"
done

echo "Backends created successfully."

# Apply load balancing policy (simplified version)
echo "Creating load balancing policy..."

POLICY_XML='<policies>
    <inbound>
        <base />
        <set-backend-service id="backend-selector">
            <backend-id>backend-cv-ocr-demo-je-primary</backend-id>
        </set-backend-service>
        <set-header name="Ocp-Apim-Subscription-Key" exists-action="override">
            <value>{{cv-api-key}}</value>
        </set-header>
        <set-header name="X-APIM-Request-Id" exists-action="override">
            <value>@(context.RequestId)</value>
        </set-header>
    </inbound>
    <backend>
        <retry condition="@(context.Response.StatusCode >= 500)" count="2" interval="1">
            <base />
        </retry>
    </backend>
    <outbound>
        <base />
        <set-header name="X-Served-By-Backend" exists-action="override">
            <value>backend-cv-ocr-demo-je-primary</value>
        </set-header>
    </outbound>
    <on-error>
        <base />
    </on-error>
</policies>'

# Apply policy to the operation
echo "Applying policy to operation..."
echo "$POLICY_XML" | az apim api operation policy create \
    --resource-group "$RESOURCE_GROUP" \
    --service-name "$APIM_NAME" \
    --api-id "$API_ID" \
    --operation-id "analyze-read" \
    --policy-content @-

echo "Policy applied successfully."

# Get API URL
API_URL="https://$APIM_NAME.azure-api.net/$API_PATH"
echo
echo "=== Setup Complete ==="
echo "API URL: $API_URL"
echo "API Path: /$API_PATH"
echo "Test endpoint: $API_URL/formrecognizer/documentModels/prebuilt-read:analyze?api-version=2024-02-29-preview"
echo
echo "Don't forget to:"
echo "1. Configure named values for cv-api-key"
echo "2. Test the API endpoint"
echo "3. Monitor logs for any issues"