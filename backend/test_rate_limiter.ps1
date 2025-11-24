# Simple PowerShell test for rate limiter
Write-Host "🧪 Testing Fixed Window Rate Limiter" -ForegroundColor Cyan
Write-Host "=" * 50

# Function to make a request and show result
function Test-Request {
    param($i)
    
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8000/test" -Method GET -ErrorAction Stop
        Write-Host "Request $i : Status 200 (SUCCESS)" -ForegroundColor Green
        $rateLimit = $response.rate_limit
        if ($rateLimit) {
            Write-Host "  Current: $($rateLimit.current_count), Remaining: $($rateLimit.remaining)" -ForegroundColor Yellow
        }
    }
    catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        if ($statusCode -eq 429) {
            Write-Host "Request $i : Status 429 (RATE LIMITED)" -ForegroundColor Red
            # Try to get error details
            try {
                $errorResponse = $_.ErrorDetails.Message | ConvertFrom-Json
                Write-Host "  Retry after: $($errorResponse.retry_after) seconds" -ForegroundColor Red
            } catch {
                Write-Host "  Rate limit exceeded!" -ForegroundColor Red
            }
        } else {
            Write-Host "Request $i : Status $statusCode (ERROR)" -ForegroundColor Red
        }
    }
    
    Start-Sleep -Milliseconds 100
}

# Test multiple requests
for ($i = 1; $i -le 7; $i++) {
    Test-Request -i $i
}

Write-Host "`n" + "=" * 50
Write-Host "Expected behavior:" -ForegroundColor Cyan
Write-Host "- First 5 requests: Status 200 (allowed)" -ForegroundColor Green
Write-Host "- Requests 6-7: Status 429 (rate limited)" -ForegroundColor Red