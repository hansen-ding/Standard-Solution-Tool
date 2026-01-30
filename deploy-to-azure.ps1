# Azure 部署脚本 - BESS Sizing Tool
# 使用前请先安装 Azure CLI: https://aka.ms/installazurecliwindows

param(
    [string]$ResourceGroup = "bess-tool-rg",
    [string]$Location = "eastus",
    [string]$ACRName = "besstoolregistry",
    [string]$ContainerName = "bess-sizing-tool",
    [string]$DNSLabel = "bess-tool-app"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "BESS Sizing Tool - Azure 部署" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查 Azure CLI
Write-Host "检查 Azure CLI..." -ForegroundColor Yellow
if (!(Get-Command az -ErrorAction SilentlyContinue)) {
    Write-Host "错误: 未找到 Azure CLI" -ForegroundColor Red
    Write-Host "请先安装: https://aka.ms/installazurecliwindows" -ForegroundColor Yellow
    exit 1
}
Write-Host "✓ Azure CLI 已安装" -ForegroundColor Green
Write-Host ""

# 检查本地镜像
Write-Host "检查本地 Docker 镜像..." -ForegroundColor Yellow
$localImage = docker images bess-sizing-tool -q
if (!$localImage) {
    Write-Host "错误: 未找到本地镜像 'bess-sizing-tool'" -ForegroundColor Red
    Write-Host "请先运行: docker-compose build" -ForegroundColor Yellow
    exit 1
}
Write-Host "✓ 本地镜像存在" -ForegroundColor Green
Write-Host ""

# 登录 Azure
Write-Host "登录 Azure..." -ForegroundColor Yellow
az login
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Azure 登录失败" -ForegroundColor Red
    exit 1
}
Write-Host "✓ 已登录 Azure" -ForegroundColor Green
Write-Host ""

# 创建资源组
Write-Host "创建资源组: $ResourceGroup" -ForegroundColor Yellow
az group create --name $ResourceGroup --location $Location --output none
Write-Host "✓ 资源组已创建" -ForegroundColor Green
Write-Host ""

# 创建 ACR
Write-Host "创建 Azure Container Registry: $ACRName" -ForegroundColor Yellow
Write-Host "(如果已存在会跳过)" -ForegroundColor Gray
az acr create --resource-group $ResourceGroup --name $ACRName --sku Basic --output none 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "注意: ACR 可能已存在，继续..." -ForegroundColor Yellow
}
Write-Host "✓ ACR 已准备" -ForegroundColor Green
Write-Host ""

# 登录 ACR
Write-Host "登录到 ACR..." -ForegroundColor Yellow
az acr login --name $ACRName
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ ACR 登录失败" -ForegroundColor Red
    exit 1
}
Write-Host "✓ 已登录 ACR" -ForegroundColor Green
Write-Host ""

# 获取 ACR 地址
Write-Host "获取 ACR 登录服务器..." -ForegroundColor Yellow
$ACRLoginServer = az acr show --name $ACRName --query loginServer --output tsv
Write-Host "ACR 地址: $ACRLoginServer" -ForegroundColor Cyan
Write-Host ""

# 标记并推送镜像
Write-Host "推送镜像到 Azure..." -ForegroundColor Yellow
Write-Host "标记镜像..." -ForegroundColor Gray
docker tag bess-sizing-tool "${ACRLoginServer}/bess-sizing-tool:latest"

Write-Host "上传镜像 (这可能需要几分钟)..." -ForegroundColor Gray
docker push "${ACRLoginServer}/bess-sizing-tool:latest"
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ 镜像推送失败" -ForegroundColor Red
    exit 1
}
Write-Host "✓ 镜像已推送到 Azure" -ForegroundColor Green
Write-Host ""

# 启用 ACR 管理员账号
Write-Host "配置 ACR 权限..." -ForegroundColor Yellow
az acr update --name $ACRName --admin-enabled true --output none
$ACRPassword = az acr credential show --name $ACRName --query "passwords[0].value" --output tsv
Write-Host "✓ ACR 权限已配置" -ForegroundColor Green
Write-Host ""

# 删除旧容器实例（如果存在）
Write-Host "检查是否存在旧实例..." -ForegroundColor Yellow
$existingContainer = az container show --resource-group $ResourceGroup --name $ContainerName 2>$null
if ($existingContainer) {
    Write-Host "删除旧实例..." -ForegroundColor Yellow
    az container delete --resource-group $ResourceGroup --name $ContainerName --yes --output none
    Write-Host "等待删除完成..." -ForegroundColor Gray
    Start-Sleep -Seconds 10
}
Write-Host ""

# 部署容器实例
Write-Host "部署容器到 Azure (这可能需要2-3分钟)..." -ForegroundColor Yellow
az container create `
  --resource-group $ResourceGroup `
  --name $ContainerName `
  --image "${ACRLoginServer}/bess-sizing-tool:latest" `
  --cpu 2 `
  --memory 2 `
  --registry-login-server $ACRLoginServer `
  --registry-username $ACRName `
  --registry-password $ACRPassword `
  --dns-name-label $DNSLabel `
  --ports 8501 `
  --output none

if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ 容器部署失败" -ForegroundColor Red
    exit 1
}
Write-Host "✓ 容器已部署" -ForegroundColor Green
Write-Host ""

# 获取访问地址
Write-Host "获取访问信息..." -ForegroundColor Yellow
$containerInfo = az container show --resource-group $ResourceGroup --name $ContainerName --query "{FQDN:ipAddress.fqdn,ProvisioningState:provisioningState}" --output json | ConvertFrom-Json

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "✓ 部署成功!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "访问地址:" -ForegroundColor Cyan
Write-Host "  http://$($containerInfo.FQDN):8501" -ForegroundColor White
Write-Host ""
Write-Host "状态: $($containerInfo.ProvisioningState)" -ForegroundColor Gray
Write-Host ""
Write-Host "管理命令:" -ForegroundColor Yellow
Write-Host "  查看日志: az container logs --resource-group $ResourceGroup --name $ContainerName" -ForegroundColor Gray
Write-Host "  重启容器: az container restart --resource-group $ResourceGroup --name $ContainerName" -ForegroundColor Gray
Write-Host "  停止容器: az container stop --resource-group $ResourceGroup --name $ContainerName" -ForegroundColor Gray
Write-Host "  删除容器: az container delete --resource-group $ResourceGroup --name $ContainerName" -ForegroundColor Gray
Write-Host ""
Write-Host "注意: 容器启动需要约1-2分钟，请稍后访问" -ForegroundColor Yellow
Write-Host ""
