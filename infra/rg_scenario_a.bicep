@description('シナリオA用のComputer Visionリソースをデプロイ')
param projectName string = 'ocr-demo-a'
param location string = resourceGroup().location

@allowed([
  'S0'
  'S1'
])
param cognitiveServicesSku string = 'S1'

param locations array = [
  'eastus'
  'japaneast' 
  'westeurope'
]

// Computer Vision アカウントを複数リージョンに作成
resource cognitiveServices 'Microsoft.CognitiveServices/accounts@2023-05-01' = [for (loc, i) in locations: {
  name: '${projectName}-cv-${loc}'
  location: loc
  sku: {
    name: cognitiveServicesSku
  }
  kind: 'ComputerVision'
  properties: {
    apiProperties: {}
    customSubDomainName: '${projectName}-cv-${loc}'
    networkAcls: {
      defaultAction: 'Allow'
    }
    publicNetworkAccess: 'Enabled'
  }
  tags: {
    Project: projectName
    Scenario: 'A'
    Environment: 'Demo'
    Region: loc
  }
}]

// 各Computer Visionアカウントの情報を出力
output cognitiveServicesEndpoints array = [for (loc, i) in locations: {
  name: cognitiveServices[i].name
  location: loc
  endpoint: cognitiveServices[i].properties.endpoint
  key: cognitiveServices[i].listKeys().key1
}]

output resourceGroupName string = resourceGroup().name
output subscriptionId string = subscription().subscriptionId

// .env ファイル用の設定文字列を出力として生成
output ocrEndpoints string = join([for (loc, i) in locations: '${cognitiveServices[i].properties.endpoint}vision/v3.2/read/analyze'], ',')
output ocrKeys string = join([for (loc, i) in locations: cognitiveServices[i].listKeys().key1], ',')
