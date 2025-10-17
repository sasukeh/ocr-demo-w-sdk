targetScope = 'subscription'

@description('Japan East リージョンでのComputer Vision負荷分散・フォールバックデモ用リソース')

param resourceGroupName string = 'rg-ocr-demo-japan-east'
param computerVisionBaseName string = 'cv-ocr-demo-je'
param location string = 'japaneast'
param tags object = {
  project: 'ocr-demo'
  scenario: 'japan-east-loadbalancing'
  environment: 'demo'
  region: 'japaneast'
}

// Japan East リージョンに3つのComputer Visionエンドポイント
var endpoints = [
  {
    name: 'primary'
    displayName: 'Primary Endpoint'
    suffix: 'primary'
    description: 'メインエンドポイント'
  }
  {
    name: 'secondary'
    displayName: 'Secondary Endpoint'
    suffix: 'secondary'
    description: 'セカンダリエンドポイント'
  }
  {
    name: 'tertiary'
    displayName: 'Tertiary Endpoint'
    suffix: 'tertiary'
    description: '第三エンドポイント'
  }
]

// リソースグループ
resource resourceGroup 'Microsoft.Resources/resourceGroups@2023-07-01' = {
  name: resourceGroupName
  location: location
  tags: tags
}

// Japan East に3つのComputer Visionリソースをデプロイ
module computerVisionResources 'modules/computer-vision.bicep' = [for endpoint in endpoints: {
  name: 'computerVision-${endpoint.suffix}'
  scope: resourceGroup
  params: {
    computerVisionName: '${computerVisionBaseName}-${endpoint.suffix}'
    location: location
    sku: 'S1'  // Standard tier for production workloads
    tags: union(tags, {
      endpointType: endpoint.displayName
      suffix: endpoint.suffix
      description: endpoint.description
    })
  }
}]

// 出力（後でスクリプトから参照）
output resourceGroupName string = resourceGroup.name
output computerVisionEndpoints array = [for (endpoint, i) in endpoints: {
  region: location
  name: computerVisionResources[i].outputs.name
  endpoint: computerVisionResources[i].outputs.endpoint
  resourceId: computerVisionResources[i].outputs.resourceId
  suffix: endpoint.suffix
  endpointType: endpoint.name
  description: endpoint.description
}]

var endpointTypeNames = [
  'primary'
  'secondary'
  'tertiary'
]

output summary object = {
  resourceGroup: resourceGroup.name
  region: location
  endpointCount: length(endpoints)
  endpointTypes: endpointTypeNames
}
