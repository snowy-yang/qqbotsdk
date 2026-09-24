#!/usr/bin/env bash
# 组装纯文档目录并部署到 Cloudflare Pages（docsify 零构建，Direct Upload）。
#
# 用法：scripts/deploy_docs.sh [项目名]     # 项目名默认取 PROJECT_NAME，再默认 qqbotsdk-docs
# 本地首次运行会自动唤起 wrangler 浏览器授权（或预先 export CLOUDFLARE_API_TOKEN）；
# 项目不存在时 wrangler 会自动创建，站点地址 https://<项目名>.pages.dev。
# CI（.gitea/workflows/deploy-docs.yml）经 CLOUDFLARE_API_TOKEN/CLOUDFLARE_ACCOUNT_ID 鉴权调用本脚本。

set -euo pipefail
cd "$(dirname "$0")/.."

PROJECT_NAME="${1:-${PROJECT_NAME:-qqbotsdk-docs}}"

rm -rf dist
mkdir dist
# docsify 站点只由这些 markdown 和 index.html 组成，静态资源全部走 CDN——
# 只挑文档文件，不把源码仓库整个传上站点
cp index.html README.md _sidebar.md CHANGELOG.md dist/
cp -r docs examples dist/
cp .nojekyll dist/ 2>/dev/null || true
# examples/ 里的 Python 字节码缓存不该上站点
find dist -type d -name __pycache__ -exec rm -rf {} +

# 新版 wrangler 的 pages deploy 不再自动建项目：先幂等创建（已存在则忽略报错）
npx wrangler pages project create "$PROJECT_NAME" --production-branch=main >/dev/null 2>&1 || true
npx wrangler pages deploy dist --project-name="$PROJECT_NAME" --branch=main --commit-dirty=true
