@description('Computer Vision Cognitive Service リソース')

param computerVisionName string
param location string
param sku string = 'S1'
param tags object = {}

// Computer Vision リソース
resource computerVision 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: computerVisionName
  location: location
  kind: 'ComputerVision'
  sku: {
    name: sku
  }
  properties: {
    apiProperties: {
      statisticsEnabled: false
    }
    customSubDomainName: computerVisionName
    networkAcls: {
      defaultAction: 'Allow'
      virtualNetworkRules: []
      ipRules: []
    }
    publicNetworkAccess: 'Enabled'
  }
  tags: union(tags, {
    resourceType: 'Computer Vision'
    managedBy: 'Bicep'
    sku: sku
  })
}

// 出力
output name string = computerVision.name
output endpoint string = computerVision.properties.endpoint
output location string = computerVision.location
output resourceId string = computerVision.id
