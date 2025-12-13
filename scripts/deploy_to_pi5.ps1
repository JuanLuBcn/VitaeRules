# Deploy VitaeRules to Raspberry Pi 5 from Windows
# Usage: .\scripts\deploy_to_pi5.ps1 [pi_user@pi_ip]

param(
    [string]$PiHost = "core@homeassistant.local"
)

Write-Host "`n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host "  VitaeRules - Raspberry Pi 5 Deployment" -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`n" -ForegroundColor Green

Write-Host "📡 Connecting to: $PiHost`n" -ForegroundColor Yellow

$commands = @"
set -e
cd VitaeRules
echo -e "\033[1;33m🔄 Step 1: Pulling latest changes from Git...\033[0m"
git pull origin main
echo -e "\033[1;33m🐳 Step 2: Stopping current container...\033[0m"
docker compose down || docker stop vitaerules || true
echo -e "\033[1;33m🔧 Step 3: Updating .env with minimax-m2:cloud model...\033[0m"
if grep -q "^OLLAMA_MODEL=" .env; then
    sed -i 's/^OLLAMA_MODEL=.*/OLLAMA_MODEL=minimax-m2:cloud/' .env
else
    echo "OLLAMA_MODEL=minimax-m2:cloud" >> .env
fi
echo -e "\033[1;33m📦 Step 4: Rebuilding Docker image (this copies the .env file)...\033[0m"
docker compose build --no-cache
echo -e "\033[1;33m🚀 Step 5: Starting VitaeRules container...\033[0m"
docker compose up -d
echo -e "\033[1;33m⏳ Step 6: Waiting for bot to start...\033[0m"
sleep 5
echo -e "\033[1;33m📋 Step 7: Checking container status...\033[0m"
docker ps | grep vitaerules
echo ""
echo -e "\033[0;32m✅ Deployment completed successfully!\033[0m"
echo -e "\033[0;32m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m"
echo ""
echo -e "\033[1;33m📊 To view logs:\033[0m"
echo "   docker logs -f vitaerules"
echo ""
echo -e "\033[1;33m🔄 To restart:\033[0m"
echo "   docker compose restart"
echo ""
"@

try {
    ssh $PiHost $commands
    Write-Host "`n🎉 Deployment finished! Your bot is running on the Pi5.`n" -ForegroundColor Green
}
catch {
    Write-Host "`n❌ Deployment failed: $_`n" -ForegroundColor Red
    exit 1
}
