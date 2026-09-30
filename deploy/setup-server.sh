#!/usr/bin/env bash
# 在 Ubuntu 服务器上用 sudo 运行：配置网站、设置每天定时抓取。不会改动服务器上已有的其他网站。
# 代码通过 git 放在 /opt/lhc（git clone / git pull），然后在仓库目录执行：
#   sudo bash deploy/setup-server.sh              首次部署，或更新了 deploy/ 下的文件后重新应用
#   sudo bash deploy/setup-server.sh 你的SendKey   开启 / 更换微信推送（Server酱）
#   sudo bash deploy/setup-server.sh none         关闭微信推送
# 不带参数重新运行时会保留已设置的 SendKey。
# 端口默认 8091，要换端口：sudo LHC_PORT=8092 bash deploy/setup-server.sh
# 可以重复运行，不会产生重复配置。
set -euo pipefail

APP=$(cd "$(dirname "$0")/.." && pwd) # 仓库目录（一般是 /opt/lhc）
DATA=/opt/lhc-data                     # 每天抓取的数据和日志，放在仓库外，git pull 不会冲突
PORT="${LHC_PORT:-8091}"
RUN_USER="${SUDO_USER:-root}" # 定时抓取以登录用户身份运行，和 git pull 的用户一致
SITE=/etc/nginx/sites-available/lhc
LINK=/etc/nginx/sites-enabled/lhc

step() { echo; echo "== $*"; }
fail() { echo "错误：$*"; exit 1; }

[[ $EUID -eq 0 ]] || fail "请在命令前加 sudo"
[[ -f $APP/scraper/scrape.py ]] || fail "没找到 $APP/scraper/scrape.py，请在仓库目录里运行"
grep -qs 'assets/' $APP/web/dist/index.html ||
  fail "没找到打包好的网页 $APP/web/dist。请在本地运行 cd web && npm run build，把 web/dist 一起提交推送，再在服务器上 git pull"

# 没传 SendKey 时沿用现有定时任务里的；传 none 表示关闭推送
PUSH_KEY="${1:-}"
if [[ -z $PUSH_KEY ]]; then
  PUSH_KEY=$(crontab -u "$RUN_USER" -l 2>/dev/null | grep -o "LHC_PUSH_KEY='[^']*'" | head -1 | cut -d"'" -f2 || true)
fi
[[ $PUSH_KEY == none ]] && PUSH_KEY=""

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
[[ -z $others ]] || fail "端口 $PORT 已被这些 nginx 配置使用：$others。请换端口，例如：sudo LHC_PORT=8092 bash $0"
if [[ ! -e $LINK ]] && command -v ss >/dev/null && ss -ltn "( sport = :$PORT )" | grep -q LISTEN; then
  fail "端口 $PORT 已被其他程序占用。请换端口，例如：sudo LHC_PORT=8092 bash $0"
fi
echo "可用"

step "4/7 准备数据目录 $DATA"
mkdir -p $DATA/logs
if [[ ! -s $DATA/draws.json ]]; then
  if [[ -s $APP/data/draws.json ]]; then
    cp $APP/data/draws.json $DATA/draws.json
    echo "用仓库里的数据作为初始数据"
  fi
fi
chown -R "$RUN_USER": $APP $DATA
chmod -R a+rX $APP/web/dist $DATA # nginx 以 www-data 身份运行，需要能读取网页和数据
chmod a+x $APP $APP/web          # 允许进入仓库目录找到 web/dist
echo "完成"

step "5/7 配置网站（新增 $SITE，不改动其他站点）"
backup=""
[[ -f $SITE ]] && backup=$(cat $SITE)
sed -E -e "s/listen[[:space:]]+[0-9]+;/listen $PORT;/" \
  -e "s#root /opt/lhc/web/dist;#root $APP/web/dist;#" \
  -e "s#alias /opt/lhc-data/;#alias $DATA/;#" $APP/deploy/nginx.conf > $SITE
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

step "6/7 抓取最新数据，设置定时任务"
if [[ -s $DATA/draws.json ]]; then args=(); else args=(--all); fi
sudo -u "$RUN_USER" python3 $APP/scraper/scrape.py --out $DATA/draws.json "${args[@]}" ||
  echo "抓取失败，定时任务会在开奖后重试"
# 每天北京时间 21:34 开奖时开始抓，没抓到每分钟重试，最晚到 22:40；按服务器时区换算（东八区就是 21:34）
read -r MIN HOUR < <(date -d 'TZ="Asia/Shanghai" 21:34' '+%-M %-H')
LINE="$MIN $HOUR * * * cd $APP && LHC_PUSH_KEY='$PUSH_KEY' /usr/bin/python3 scraper/scrape.py --wait 22:40 --out $DATA/draws.json >> $DATA/logs/scrape.log 2>&1"
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
echo "数据：$DATA/draws.json    日志：$DATA/logs/scrape.log"
echo "以后更新网页或脚本：cd $APP && git pull（改了 deploy/ 下的文件时再运行一次本脚本）"
if [[ -n $PUSH_KEY ]]; then
  echo "测试微信推送：LHC_PUSH_KEY='$PUSH_KEY' python3 $APP/scraper/scrape.py --out $DATA/draws.json --push-test"
fi
