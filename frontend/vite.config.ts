import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

/** Vite dev proxy target. Override when API and dev server are not on the same localhost (e.g. API on Windows, Vite in WSL). */
function apiProxyTarget(): string {
  const fromEnv = process.env.VITE_API_PROXY_TARGET?.trim()
  if (fromEnv) return fromEnv.replace(/\/$/, '')
  return 'http://127.0.0.1:8000'
}

function warnWslWindowsApiSplit() {
  if (!process.env.WSL_DISTRO_NAME) return
  console.warn(
    '\n[vite] Dev server is running in WSL but /api is proxied to 127.0.0.1:8000 (WSL localhost).\n' +
      '       If uvicorn runs in Windows PowerShell, pick one:\n' +
      '         • Run `npm run dev` from PowerShell in frontend/ (same host as the API), or\n' +
      '         • Run uvicorn inside this WSL session, or\n' +
      '         • Enable WSL mirrored networking (%USERPROFILE%\\.wslconfig → [wsl2] networkingMode=mirrored, then wsl --shutdown).\n' +
      '       Optional: set VITE_API_PROXY_TARGET to your Windows host IP (see /etc/resolv.conf nameserver) and allow TCP 8000 in Windows Firewall.\n',
  )
}

warnWslWindowsApiSplit()

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: apiProxyTarget(),
        changeOrigin: true,
      },
    },
  },
})
