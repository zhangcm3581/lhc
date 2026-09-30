#!/usr/bin/env bash
# 在 Ubuntu 服务器上以 root 运行：安装 nginx、配置网站、设置每天定时抓取。
# 先在本地运行 deploy/deploy.sh 把文件传上来，再执行：
#   bash /opt/lhc/deploy/setup-server.sh              不开微信推送
#   bash /opt/lhc/deploy/setup-server.sh 你的SendKey   开启微信推送（Server酱）
# 可以重复运行（比如要改 SendKey），不会产生重复配置。
set -euo pipefail

APP=/opt/lhc
PORT=8080
PUSH_KEY="${1:-}"

step() { echo; echo "== $*"; }

[[ $EUID -eq 0 ]] || { echo "请用 root 运行，或在命令前加 sudo"; exit 1; }
[[ -f $APP/scraper/scrape.py && -f $APP/web/index.html ]] || {
  echo "没找到 $APP 下的网页和抓取脚本，请先在本地运行 deploy/deploy.sh"; exit 1; }

step "1/6 安装 nginx、cron"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq nginx cron python3 curl tzdata >/dev/null
echo "完成"

step "2/6 检查能否访问数据源"
code=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 20 -A 'Mozilla/5.0' \
  https://www.55128.cn/kjh/history_newam6hc.aspx || true)
if [[ $code == 200 ]]; then
  echo "正常"
else
  echo "警告：访问数据源返回 ${code:-失败}，这台服务器可能访问不了，每天的自动抓取会失败"
fi

step "3/6 配置网站（端口 $PORT）"
cp $APP/deploy/nginx.conf /etc/nginx/conf.d/lhc.conf
mkdir -p $APP/data $APP/logs
chmod -R a+rX $APP # nginx 以 www-data 身份运行，需要能读取网页和数据
nginx -t -q
if systemctl enable --now nginx >/dev/null 2>&1; then
  systemctl reload nginx
else
  nginx -s reload 2>/dev/null || nginx # 没有 systemd 的环境（如容器）
fi
echo "完成"

step "4/6 抓取最新数据"
if [[ -s $APP/data/draws.json ]]; then args=(); else args=(--all); fi
python3 $APP/scraper/scrape.py "${args[@]}" || echo "抓取失败，定时任务会在开奖后重试"

step "5/6 定时任务：每天北京时间 21:34 开奖时开始抓取，没抓到每分钟重试，最晚到 22:40"
# 按服务器自己的时区换算出北京时间 21:34 对应的时刻（东八区服务器就是 21:34）
read -r MIN HOUR < <(date -d 'TZ="Asia/Shanghai" 21:34' '+%-M %-H')
LINE="$MIN $HOUR * * * cd $APP && LHC_PUSH_KEY='$PUSH_KEY' /usr/bin/python3 scraper/scrape.py --wait 22:40 >> $APP/logs/scrape.log 2>&1"
{ crontab -l 2>/dev/null | grep -v 'scraper/scrape.py' || true; echo "$LINE"; } | crontab -
systemctl enable --now cron >/dev/null 2>&1 || service cron start >/dev/null 2>&1 || true
echo "服务器时区 $(date +%Z)，每天 $(printf '%02d:%02d' "$HOUR" "$MIN") 运行；微信推送：$([[ -n $PUSH_KEY ]] && echo 已开启 || echo 未开启)"

step "6/6 防火墙"
if command -v ufw >/dev/null && ufw status | grep -q 'Status: active'; then
  ufw allow $PORT/tcp >/dev/null && echo "已放行 $PORT 端口"
else
  echo "ufw 未启用，跳过"
fi

echo
echo "全部完成。浏览器打开 http://服务器公网IP:$PORT"
echo "云服务器还需要在控制台的安全组（防火墙）里放行 TCP $PORT 端口。"
if [[ -n $PUSH_KEY ]]; then
  echo "测试微信推送：LHC_PUSH_KEY='$PUSH_KEY' python3 $APP/scraper/scrape.py --push-test"
fi
