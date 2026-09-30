#!/usr/bin/env bash
# 在 Ubuntu 服务器上用 sudo 运行：配置网站、设置每天定时抓取。不会改动服务器上已有的其他网站。
# 先在本地运行 deploy/deploy.sh 把文件传上来，再执行：
#   sudo bash /opt/lhc/deploy/setup-server.sh              不开微信推送
#   sudo bash /opt/lhc/deploy/setup-server.sh 你的SendKey   开启微信推送（Server酱）
# 端口默认 8091，要换端口：sudo LHC_PORT=8092 bash /opt/lhc/deploy/setup-server.sh
# 可以重复运行（比如要改 SendKey），不会产生重复配置。
set -euo pipefail

APP=/opt/lhc
PORT="${LHC_PORT:-8091}"
PUSH_KEY="${1:-}"
RUN_USER="${SUDO_USER:-root}" # 定时抓取以登录用户身份运行，文件归属一致
SITE=/etc/nginx/sites-available/lhc
LINK=/etc/nginx/sites-enabled/lhc

step() { echo; echo "== $*"; }
fail() { echo "错误：$*"; exit 1; }

[[ $EUID -eq 0 ]] || fail "请在命令前加 sudo"
[[ -f $APP/scraper/scrape.py && -f $APP/web/index.html ]] || fail "没找到 $APP 下的网页和抓取脚本，请先在本地运行 deploy/deploy.sh"

step "1/7 检查依赖（已安装的不会重复安装）"
missing=()
command -v nginx >/dev/null || missing+=(nginx)
command -v crontab >/dev/null || missing+=(cron)
command -v python3 >/dev/null || missing+=(python3)
command -v curl >/dev/null || missing+=(curl)
[[ -e /usr/share/zoneinfo/Asia/Shanghai ]] || missing+=(tzdata)
if ((${#missing[@]})); then
  echo "安装：${missing[*]}"
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get install -y -qq "${missing[@]}" >/dev/null
fi
echo "完成"

step "2/7 检查能否访问数据源"
UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/128 Safari/537.36'
probe() { curl -sS -o /dev/null -w '%{http_code}' --max-time 20 -A "$UA" "$1/kjh/history_newam6hc.aspx" 2>/dev/null || true; }
www=$(probe https://www.55128.cn)
mob=$(probe https://m.55128.cn)
if [[ $www == 200 ]]; then
  echo "正常（电脑版）"
elif [[ $mob == 200 ]]; then
  echo "电脑版返回 ${www:-失败}（这台服务器的 IP 被网站屏蔽），手机版正常，抓取时会自动改用手机版"
else
  echo "警告：电脑版返回 ${www:-失败}、手机版返回 ${mob:-失败}，这台服务器访问不了数据源，每天的自动抓取会失败"
fi

step "3/7 检查端口 $PORT 是否空闲"
# 其他站点配置里已经写了这个端口，或者有别的程序在用，都换一个端口
# sites-enabled 里一般是链接文件，要用 -R 才会跟进去检查
others=$(grep -RlE "listen[[:space:]]+([^;]*:)?$PORT([[:space:];]|$)" /etc/nginx/sites-enabled /etc/nginx/conf.d 2>/dev/null | grep -v "/lhc" || true)
[[ -z $others ]] || fail "端口 $PORT 已被这些 nginx 配置使用：$others。请换端口，例如：sudo LHC_PORT=8092 bash $0 ${PUSH_KEY}"
if [[ ! -e $LINK ]] && command -v ss >/dev/null && ss -ltn "( sport = :$PORT )" | grep -q LISTEN; then
  fail "端口 $PORT 已被其他程序占用。请换端口，例如：sudo LHC_PORT=8092 bash $0 ${PUSH_KEY}"
fi
echo "可用"

step "4/7 配置网站（新增 $SITE，不改动其他站点）"
chown -R "$RUN_USER": $APP
mkdir -p $APP/data $APP/logs
chown "$RUN_USER": $APP/data $APP/logs
chmod -R a+rX $APP # nginx 以 www-data 身份运行，需要能读取网页和数据
backup=""
[[ -f $SITE ]] && backup=$(cat $SITE)
sed -E "s/listen[[:space:]]+[0-9]+;/listen $PORT;/" $APP/deploy/nginx.conf > $SITE
ln -sf $SITE $LINK
if ! nginx -t 2>/tmp/lhc-nginx-test.log; then
  # 配置检查不通过：撤回本次改动，不重载 nginx，已有站点不受影响
  if [[ -n $backup ]]; then echo "$backup" > $SITE; else rm -f $SITE $LINK; fi
  cat /tmp/lhc-nginx-test.log
  fail "nginx 配置检查未通过，已撤回改动，现有网站不受影响"
fi
if systemctl is-active --quiet nginx 2>/dev/null; then
  systemctl reload nginx
elif pidof nginx >/dev/null; then
  nginx -s reload
else
  systemctl enable --now nginx >/dev/null 2>&1 || nginx
fi
echo "完成"

step "5/7 抓取最新数据"
if [[ -s $APP/data/draws.json ]]; then args=(); else args=(--all); fi
sudo -u "$RUN_USER" python3 $APP/scraper/scrape.py "${args[@]}" || echo "抓取失败，定时任务会在开奖后重试"

step "6/7 定时任务：每天北京时间 21:34 开奖时开始抓取，没抓到每分钟重试，最晚到 22:40"
# 按服务器自己的时区换算出北京时间 21:34 对应的时刻（东八区服务器就是 21:34）
read -r MIN HOUR < <(date -d 'TZ="Asia/Shanghai" 21:34' '+%-M %-H')
LINE="$MIN $HOUR * * * cd $APP && LHC_PUSH_KEY='$PUSH_KEY' /usr/bin/python3 scraper/scrape.py --wait 22:40 >> $APP/logs/scrape.log 2>&1"
{ crontab -u "$RUN_USER" -l 2>/dev/null | grep -v 'scraper/scrape.py' || true; echo "$LINE"; } | crontab -u "$RUN_USER" -
systemctl enable --now cron >/dev/null 2>&1 || service cron start >/dev/null 2>&1 || true
echo "以 $RUN_USER 身份运行；服务器时区 $(date +%Z)，每天 $(printf '%02d:%02d' "$HOUR" "$MIN") 开始；微信推送：$([[ -n $PUSH_KEY ]] && echo 已开启 || echo 未开启)"

step "7/7 防火墙"
if command -v ufw >/dev/null && ufw status | grep -q 'Status: active'; then
  ufw allow "$PORT"/tcp >/dev/null && echo "已放行 $PORT 端口"
else
  echo "ufw 未启用，跳过"
fi

echo
echo "全部完成。浏览器打开 http://服务器公网IP:$PORT"
echo "云服务器还需要在控制台的安全组（防火墙）里放行 TCP $PORT 端口。"
if [[ -n $PUSH_KEY ]]; then
  echo "测试微信推送：LHC_PUSH_KEY='$PUSH_KEY' python3 $APP/scraper/scrape.py --push-test"
fi
