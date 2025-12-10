import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import fs from 'fs'

const outputDir = path.resolve(__dirname, '../output')
const inputDir = path.resolve(__dirname, '../input')

export default defineConfig({
  plugins: [
    react(),
    {
      name: 'api-server',
      configureServer(server) {
        // API endpoint: list JSON files
        server.middlewares.use('/api/files', (_req, res) => {
          try {
            const files = fs.readdirSync(outputDir)
              .filter(f => f.endsWith('.json'))
              .sort()
            res.setHeader('Content-Type', 'application/json')
            res.end(JSON.stringify(files))
          } catch {
            res.statusCode = 500
            res.end(JSON.stringify({ error: 'Failed to read output directory' }))
          }
        })

        // API endpoint: serve input files (Excel)
        server.middlewares.use('/api/input/', (req, res, next) => {
          const url = req.url || ''
          const fileName = decodeURIComponent(url.slice(1))

          if (!fileName) {
            next()
            return
          }

          const filePath = path.join(inputDir, fileName)

          // Security check
          if (!filePath.startsWith(inputDir)) {
            res.statusCode = 403
            res.end('Forbidden')
            return
          }

          try {
            const content = fs.readFileSync(filePath)
            res.setHeader('Content-Type', 'application/octet-stream')
            res.end(content)
          } catch {
            res.statusCode = 404
            res.end('Not found: ' + fileName)
          }
        })

        // API endpoint: serve data files
        server.middlewares.use('/api/data/', (req, res, next) => {
          // Extract filename from URL (after /api/data/)
          const url = req.url || ''
          const fileName = decodeURIComponent(url.slice(1)) // Remove leading /

          if (!fileName) {
            next()
            return
          }

          const filePath = path.join(outputDir, fileName)

          // Security check
          if (!filePath.startsWith(outputDir)) {
            res.statusCode = 403
            res.end('Forbidden')
            return
          }

          try {
            const content = fs.readFileSync(filePath, 'utf-8')
            if (fileName.endsWith('.json')) {
              res.setHeader('Content-Type', 'application/json')
            } else {
              res.setHeader('Content-Type', 'text/plain')
            }
            res.end(content)
          } catch {
            res.statusCode = 404
            res.end('Not found: ' + fileName)
          }
        })
      }
    }
  ],
})
