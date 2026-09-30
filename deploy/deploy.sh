#!/usr/bin/env bash
# 在本地执行：测试、打包前端，连同抓取脚本和部署文件上传到服务器的 /opt/lhc。
# 用法：deploy/deploy.sh root@服务器IP              更新网页和抓取脚本
#       deploy/deploy.sh root@服务器IP --with-data  首次部署：连本地已有的历史数据一起上传
set -euo pipefail
cd "$(dirname "$0")/.."

host="${1:?用法：deploy/deploy.sh root@服务器IP [--with-data]}"

python3 -m unittest scraper/test_scrape.py
(cd web && npm ci && npm test && npm run build)

ssh "$host" 'mkdir -p /opt/lhc/web /opt/lhc/scraper /opt/lhc/data /opt/lhc/logs /opt/lhc/deploy'
rsync -az --delete web/dist/ "$host:/opt/lhc/web/"
rsync -az scraper/scrape.py "$host:/opt/lhc/scraper/"
rsync -az deploy/nginx.conf deploy/setup-server.sh "$host:/opt/lhc/deploy/"
if [[ "${2:-}" == "--with-data" ]]; then
  rsync -az data/draws.json "$host:/opt/lhc/data/"
fi

echo
echo "已上传到 $host:/opt/lhc"
echo "首次部署还要在服务器上运行一次：ssh $host 'bash /opt/lhc/deploy/setup-server.sh'"
