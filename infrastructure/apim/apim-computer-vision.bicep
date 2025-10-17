@description('Location for all resources')
param location string = resourceGroup().location

@description('Name prefix for resources')
param namePrefix string = 'ocr-demo'

@description('Environment name (dev, prod, etc.)')
param environment string = 'dev'

@description('Publisher name for APIM')
param publisherName string = 'OCR Demo'

@description('Publisher email for APIM')
param publisherEmail string = 'admin@example.com'

@description('APIM SKU name')
@allowed([
  'Developer'
  'Standard'
  'Premium'
])
param apimSku string = 'Developer'

@description('APIM SKU capacity')
param apimSkuCount int = 1

// Variables
var apimName = '${namePrefix}-apim-${environment}'

var cvPrimaryName = 'cv-ocr-demo-je-primary'
var cvSecondaryName = 'cv-ocr-demo-je-secondary'
var cvTertiaryName = 'cv-ocr-demo-je-tertiary'

// Existing Computer Vision resources
resource cvPrimary 'Microsoft.CognitiveServices/accounts@2023-05-01' existing = {
  name: cvPrimaryName
}

resource cvSecondary 'Microsoft.CognitiveServices/accounts@2023-05-01' existing = {
  name: cvSecondaryName
}

resource cvTertiary 'Microsoft.CognitiveServices/accounts@2023-05-01' existing = {
  name: cvTertiaryName
}

// API Management instance
resource apim 'Microsoft.ApiManagement/service@2023-05-01-preview' = {
  name: apimName
  location: location
  sku: {
    name: apimSku
    capacity: apimSkuCount
  }
  properties: {
    publisherEmail: publisherEmail
    publisherName: publisherName
    notificationSenderEmail: publisherEmail
  }
  tags: {
    environment: environment
    project: 'ocr-demo'
    scenario: 'scenario-b'
    costCenter: 'Engineering'
    owner: publisherEmail
    managedBy: 'Bicep'
    purpose: 'OCR Load Balancing and Circuit Breaker'
  }
}

// Named values for Computer Vision endpoints and keys
resource namedValueCvPrimaryEndpoint 'Microsoft.ApiManagement/service/namedValues@2023-05-01-preview' = {
  parent: apim
  name: 'cv-primary-endpoint'
  properties: {
    displayName: 'cv-primary-endpoint'
    value: cvPrimary.properties.endpoint
    secret: false
  }
}

resource namedValueCvSecondaryEndpoint 'Microsoft.ApiManagement/service/namedValues@2023-05-01-preview' = {
  parent: apim
  name: 'cv-secondary-endpoint'
  properties: {
    displayName: 'cv-secondary-endpoint'
    value: cvSecondary.properties.endpoint
    secret: false
  }
}

resource namedValueCvTertiaryEndpoint 'Microsoft.ApiManagement/service/namedValues@2023-05-01-preview' = {
  parent: apim
  name: 'cv-tertiary-endpoint'
  properties: {
    displayName: 'cv-tertiary-endpoint'
    value: cvTertiary.properties.endpoint
    secret: false
  }
}

resource namedValueCvPrimaryKey 'Microsoft.ApiManagement/service/namedValues@2023-05-01-preview' = {
  parent: apim
  name: 'cv-primary-key'
  properties: {
    displayName: 'cv-primary-key'
    value: cvPrimary.listKeys().key1
    secret: true
  }
}

resource namedValueCvSecondaryKey 'Microsoft.ApiManagement/service/namedValues@2023-05-01-preview' = {
  parent: apim
  name: 'cv-secondary-key'
  properties: {
    displayName: 'cv-secondary-key'
    value: cvSecondary.listKeys().key1
    secret: true
  }
}

resource namedValueCvTertiaryKey 'Microsoft.ApiManagement/service/namedValues@2023-05-01-preview' = {
  parent: apim
  name: 'cv-tertiary-key'
  properties: {
    displayName: 'cv-tertiary-key'
    value: cvTertiary.listKeys().key1
    secret: true
  }
}

// Backend definitions for Computer Vision services
resource backendCvPrimary 'Microsoft.ApiManagement/service/backends@2023-05-01-preview' = {
  parent: apim
  name: 'cv-primary'
  properties: {
    description: 'Computer Vision Primary Backend'
    url: cvPrimary.properties.endpoint
    protocol: 'http'
    circuitBreaker: {
      rules: [
        {
          failureCondition: {
            count: 3
            errorReasons: [
              'Server errors'
            ]
            interval: 'PT1M'
            statusCodeRanges: [
              {
                min: 500
                max: 599
              }
            ]
          }
          name: 'serverErrorRule'
          tripDuration: 'PT1M'
        }
        {
          failureCondition: {
            count: 5
            errorReasons: [
              'Too many requests'
            ]
            interval: 'PT1M'
            statusCodeRanges: [
              {
                min: 429
                max: 429
              }
            ]
          }
          name: 'rateLimitRule'
          tripDuration: 'PT2M'
        }
      ]
    }
  }
}

resource backendCvSecondary 'Microsoft.ApiManagement/service/backends@2023-05-01-preview' = {
  parent: apim
  name: 'cv-secondary'
  properties: {
    description: 'Computer Vision Secondary Backend'
    url: cvSecondary.properties.endpoint
    protocol: 'http'
    circuitBreaker: {
      rules: [
        {
          failureCondition: {
            count: 3
            errorReasons: [
              'Server errors'
            ]
            interval: 'PT1M'
            statusCodeRanges: [
              {
                min: 500
                max: 599
              }
            ]
          }
          name: 'serverErrorRule'
          tripDuration: 'PT1M'
        }
        {
          failureCondition: {
            count: 5
            errorReasons: [
              'Too many requests'
            ]
            interval: 'PT1M'
            statusCodeRanges: [
              {
                min: 429
                max: 429
              }
            ]
          }
          name: 'rateLimitRule'
          tripDuration: 'PT2M'
        }
      ]
    }
  }
}

resource backendCvTertiary 'Microsoft.ApiManagement/service/backends@2023-05-01-preview' = {
  parent: apim
  name: 'cv-tertiary'
  properties: {
    description: 'Computer Vision Tertiary Backend'
    url: cvTertiary.properties.endpoint
    protocol: 'http'
    circuitBreaker: {
      rules: [
        {
          failureCondition: {
            count: 3
            errorReasons: [
              'Server errors'
            ]
            interval: 'PT1M'
            statusCodeRanges: [
              {
                min: 500
                max: 599
              }
            ]
          }
          name: 'serverErrorRule'
          tripDuration: 'PT1M'
        }
        {
          failureCondition: {
            count: 5
            errorReasons: [
              'Too many requests'
            ]
            interval: 'PT1M'
            statusCodeRanges: [
              {
                min: 429
                max: 429
              }
            ]
          }
          name: 'rateLimitRule'
          tripDuration: 'PT2M'
        }
      ]
    }
  }
}

// API definition
resource computerVisionApi 'Microsoft.ApiManagement/service/apis@2023-05-01-preview' = {
  parent: apim
  name: 'computer-vision-api'
  properties: {
    displayName: 'Computer Vision OCR API'
    description: 'Computer Vision API with circuit breaker and load balancing'
    serviceUrl: cvPrimary.properties.endpoint
    path: 'vision'
    protocols: [
      'https'
    ]
    subscriptionRequired: true
    apiRevision: '1'
    apiVersion: 'v3.2'
    apiVersionSetId: null
    isCurrent: true
  }
}

// API Operations
resource ocrOperation 'Microsoft.ApiManagement/service/apis/operations@2023-05-01-preview' = {
  parent: computerVisionApi
  name: 'ocr-read'
  properties: {
    displayName: 'OCR Read'
    method: 'POST'
    urlTemplate: '/vision/v3.2/read/analyze'
    description: 'Extract text from images using OCR'
    request: {
      headers: [
        {
          name: 'Content-Type'
          type: 'string'
          required: true
          values: [
            'application/octet-stream'
            'application/json'
          ]
        }
      ]
      queryParameters: [
        {
          name: 'readingOrder'
          type: 'string'
          required: false
        }
        {
          name: 'language'
          type: 'string'
          required: false
        }
      ]
    }
    responses: [
      {
        statusCode: 202
        description: 'Operation started successfully'
        headers: [
          {
            name: 'Operation-Location'
            type: 'string'
          }
        ]
      }
      {
        statusCode: 400
        description: 'Bad request'
      }
      {
        statusCode: 429
        description: 'Too many requests'
      }
      {
        statusCode: 500
        description: 'Internal server error'
      }
    ]
  }
}

resource ocrResultOperation 'Microsoft.ApiManagement/service/apis/operations@2023-05-01-preview' = {
  parent: computerVisionApi
  name: 'ocr-read-result'
  properties: {
    displayName: 'Get OCR Read Result'
    method: 'GET'
    urlTemplate: '/vision/v3.2/read/analyzeResults/{resultId}'
    description: 'Get the result of an OCR read operation'
    templateParameters: [
      {
        name: 'resultId'
        type: 'string'
        required: true
      }
    ]
    responses: [
      {
        statusCode: 200
        description: 'Success'
      }
      {
        statusCode: 400
        description: 'Bad request'
      }
      {
        statusCode: 429
        description: 'Too many requests'
      }
      {
        statusCode: 500
        description: 'Internal server error'
      }
    ]
  }
}

// Product for API
resource computerVisionProduct 'Microsoft.ApiManagement/service/products@2023-05-01-preview' = {
  parent: apim
  name: 'computer-vision-product'
  properties: {
    displayName: 'Computer Vision OCR'
    description: 'Computer Vision OCR with load balancing and circuit breaker'
    state: 'published'
    subscriptionRequired: true
    approvalRequired: false
    subscriptionsLimit: 100
  }
}

// Link API to Product
resource computerVisionProductApi 'Microsoft.ApiManagement/service/products/apis@2023-05-01-preview' = {
  parent: computerVisionProduct
  name: computerVisionApi.name
}

// Policy for load balancing and circuit breaker
resource ocrPolicy 'Microsoft.ApiManagement/service/apis/operations/policies@2023-05-01-preview' = {
  parent: ocrOperation
  name: 'policy'
  properties: {
    value: loadTextContent('./policies/ocr-load-balancer-policy.xml')
    format: 'xml'
  }
  dependsOn: [
    backendCvPrimary
    backendCvSecondary
    backendCvTertiary
    namedValueCvPrimaryKey
    namedValueCvSecondaryKey
    namedValueCvTertiaryKey
  ]
}

resource ocrResultPolicy 'Microsoft.ApiManagement/service/apis/operations/policies@2023-05-01-preview' = {
  parent: ocrResultOperation
  name: 'policy'
  properties: {
    value: loadTextContent('./policies/ocr-result-policy.xml')
    format: 'xml'
  }
  dependsOn: [
    backendCvPrimary
    backendCvSecondary
    backendCvTertiary
    namedValueCvPrimaryKey
    namedValueCvSecondaryKey
    namedValueCvTertiaryKey
  ]
}

// Log Analytics Workspace for diagnostics
resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: '${namePrefix}-log-${environment}'
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
  tags: {
    environment: environment
    project: 'ocr-demo'
    managedBy: 'Bicep'
  }
}

// APIM Diagnostic Settings
resource apimDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'apim-diagnostics'
  scope: apim
  properties: {
    workspaceId: logAnalyticsWorkspace.id
    logs: [
      {
        category: 'GatewayLogs'
        enabled: true
        retentionPolicy: {
          enabled: true
          days: 30
        }
      }
      {
        category: 'WebSocketConnectionLogs'
        enabled: true
        retentionPolicy: {
          enabled: true
          days: 30
        }
      }
    ]
    metrics: [
      {
        category: 'AllMetrics'
        enabled: true
        retentionPolicy: {
          enabled: true
          days: 30
        }
      }
    ]
  }
}

// Computer Vision Diagnostic Settings
resource cvPrimaryDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'cv-primary-diagnostics'
  scope: cvPrimary
  properties: {
    workspaceId: logAnalyticsWorkspace.id
    logs: [
      {
        category: 'Audit'
        enabled: true
        retentionPolicy: {
          enabled: true
          days: 30
        }
      }
      {
        category: 'RequestResponse'
        enabled: true
        retentionPolicy: {
          enabled: true
          days: 30
        }
      }
    ]
    metrics: [
      {
        category: 'AllMetrics'
        enabled: true
        retentionPolicy: {
          enabled: true
          days: 30
        }
      }
    ]
  }
}

resource cvSecondaryDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'cv-secondary-diagnostics'
  scope: cvSecondary
  properties: {
    workspaceId: logAnalyticsWorkspace.id
    logs: [
      {
        category: 'Audit'
        enabled: true
        retentionPolicy: {
          enabled: true
          days: 30
        }
      }
      {
        category: 'RequestResponse'
        enabled: true
        retentionPolicy: {
          enabled: true
          days: 30
        }
      }
    ]
    metrics: [
      {
        category: 'AllMetrics'
        enabled: true
        retentionPolicy: {
          enabled: true
          days: 30
        }
      }
    ]
  }
}

resource cvTertiaryDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'cv-tertiary-diagnostics'
  scope: cvTertiary
  properties: {
    workspaceId: logAnalyticsWorkspace.id
    logs: [
      {
        category: 'Audit'
        enabled: true
        retentionPolicy: {
          enabled: true
          days: 30
        }
      }
      {
        category: 'RequestResponse'
        enabled: true
        retentionPolicy: {
          enabled: true
          days: 30
        }
      }
    ]
    metrics: [
      {
        category: 'AllMetrics'
        enabled: true
        retentionPolicy: {
          enabled: true
          days: 30
        }
      }
    ]
  }
}

// Outputs
output apimName string = apim.name
output apimGatewayUrl string = 'https://${apim.properties.gatewayUrl}'
output computerVisionApiPath string = computerVisionApi.properties.path
output subscriptionKeyHeaderName string = 'Ocp-Apim-Subscription-Key'
output logAnalyticsWorkspaceId string = logAnalyticsWorkspace.id
output logAnalyticsWorkspaceName string = logAnalyticsWorkspace.name
