import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import fs from 'node:fs'
import path from 'node:path'

// 开发时把项目根目录的 data/ 挂到 /data/ 下；线上由 nginx 提供同样的路径，
// 抓取脚本直接改写那里的 draws.json，前端不用重新打包。
const dataDir = path.resolve(import.meta.dirname, '../data')
function serveData() {
  const handler = (req, res, next) => {
    const file = path.join(dataDir, decodeURIComponent(req.url.split('?')[0]))
    if (!file.startsWith(dataDir) || !fs.existsSync(file)) return next()
    res.setHeader('Content-Type', 'application/json; charset=utf-8')
    res.setHeader('Cache-Control', 'no-cache')
    fs.createReadStream(file).pipe(res)
  }
  return {
    name: 'serve-data',
    configureServer(server) {
      server.middlewares.use('/data', handler)
    },
    configurePreviewServer(server) {
      server.middlewares.use('/data', handler)
    },
  }
}

export default defineConfig({
  base: './',
  plugins: [vue(), serveData()],
  server: { host: true },
  preview: { host: true },
})
