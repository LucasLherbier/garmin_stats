$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Test-ApiHealth {
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/health" -UseBasicParsing -TimeoutSec 2
        return $response.StatusCode -eq 200
    } catch {
        return $false
    }
}

if (Test-ApiHealth) {
    Write-Host "FastAPI already running on http://127.0.0.1:8000"
} else {
    Write-Host "Starting FastAPI on http://127.0.0.1:8000 ..."
    Start-Process -FilePath "python" `
        -ArgumentList "-m", "uvicorn", "api.main:app", "--reload", "--host", "127.0.0.1", "--port", "8000" `
        -WorkingDirectory $Root `
        -WindowStyle Normal

    $ready = $false
    for ($i = 1; $i -le 120; $i++) {
        if (Test-ApiHealth) {
            $ready = $true
            break
        }
        Start-Sleep -Milliseconds 500
    }

    if (-not $ready) {
        Write-Error "FastAPI did not become ready on http://127.0.0.1:8000/api/health. Check the API window for errors."
    }

    Write-Host "FastAPI is ready."
}

Write-Host "Starting Vite on http://127.0.0.1:5173 ..."
Set-Location (Join-Path $Root "frontend")
npm run dev
