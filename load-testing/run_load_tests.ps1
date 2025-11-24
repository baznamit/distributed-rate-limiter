# Rate Limiter Load Testing Script
# ================================
# This PowerShell script automates the complete load testing process

param(
    [string]$Host = "http://localhost:8000",
    [string]$TestType = "all",
    [int]$Users = 50,
    [int]$Duration = 120
)

Write-Host "🔥 Rate Limiter Load Testing Suite" -ForegroundColor Yellow
Write-Host "=================================" -ForegroundColor Yellow

# Check if required tools are installed
function Test-Dependencies {
    Write-Host "🔍 Checking dependencies..." -ForegroundColor Blue
    
    # Check Python
    if (!(Get-Command python -ErrorAction SilentlyContinue)) {
        Write-Host "❌ Python is not installed or not in PATH" -ForegroundColor Red
        exit 1
    }
    
    # Check pip
    if (!(Get-Command pip -ErrorAction SilentlyContinue)) {
        Write-Host "❌ pip is not installed or not in PATH" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "✅ Python and pip are available" -ForegroundColor Green
}

# Install load testing dependencies
function Install-Dependencies {
    Write-Host "📦 Installing load testing dependencies..." -ForegroundColor Blue
    
    try {
        pip install -r requirements.txt --quiet
        Write-Host "✅ Dependencies installed successfully" -ForegroundColor Green
    }
    catch {
        Write-Host "❌ Failed to install dependencies: $_" -ForegroundColor Red
        exit 1
    }
}

# Check server health
function Test-ServerHealth {
    param([string]$HostUrl)
    
    Write-Host "🏥 Checking server health at $HostUrl..." -ForegroundColor Blue
    
    try {
        $response = Invoke-WebRequest -Uri "$HostUrl/health" -Method Get -TimeoutSec 10
        if ($response.StatusCode -eq 200) {
            Write-Host "✅ Server is healthy and ready for testing" -ForegroundColor Green
            return $true
        } else {
            Write-Host "❌ Server returned status code: $($response.StatusCode)" -ForegroundColor Red
            return $false
        }
    }
    catch {
        Write-Host "❌ Cannot reach server at $HostUrl" -ForegroundColor Red
        Write-Host "   Make sure the FastAPI server is running:" -ForegroundColor Yellow
        Write-Host "   cd ../backend" -ForegroundColor Gray
        Write-Host "   python -m uvicorn app.sliding_window_demo:app --reload" -ForegroundColor Gray
        return $false
    }
}

# Run basic load test
function Start-BasicLoadTest {
    param([string]$HostUrl, [int]$UserCount, [int]$TestDuration)
    
    Write-Host "🚀 Starting basic load test..." -ForegroundColor Blue
    Write-Host "   Users: $UserCount" -ForegroundColor Gray
    Write-Host "   Duration: $TestDuration seconds" -ForegroundColor Gray
    Write-Host "   Host: $HostUrl" -ForegroundColor Gray
    
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $outputFile = "results_basic_$timestamp.html"
    
    try {
        locust -f locustfile.py --host $HostUrl --users $UserCount --spawn-rate 5 --run-time "${TestDuration}s" --headless --html $outputFile
        
        if (Test-Path $outputFile) {
            Write-Host "✅ Load test completed successfully" -ForegroundColor Green
            Write-Host "📊 Results saved to: $outputFile" -ForegroundColor Blue
            
            # Open results in browser
            $choice = Read-Host "Open results in browser? (y/N)"
            if ($choice -eq "y" -or $choice -eq "Y") {
                Start-Process $outputFile
            }
        } else {
            Write-Host "⚠️  Load test completed but no results file generated" -ForegroundColor Yellow
        }
    }
    catch {
        Write-Host "❌ Load test failed: $_" -ForegroundColor Red
    }
}

# Run advanced test scenarios
function Start-AdvancedTests {
    param([string]$HostUrl)
    
    Write-Host "🎯 Starting advanced test scenarios..." -ForegroundColor Blue
    
    try {
        python run_test_scenarios.py --host $HostUrl
        Write-Host "✅ Advanced test scenarios completed" -ForegroundColor Green
    }
    catch {
        Write-Host "❌ Advanced tests failed: $_" -ForegroundColor Red
    }
}

# Interactive load test with web UI
function Start-InteractiveTest {
    param([string]$HostUrl)
    
    Write-Host "🌐 Starting interactive load test with web UI..." -ForegroundColor Blue
    Write-Host "   Navigate to http://localhost:8089 to control the test" -ForegroundColor Yellow
    Write-Host "   Press Ctrl+C to stop the test" -ForegroundColor Gray
    
    try {
        locust -f locustfile.py --host $HostUrl
    }
    catch {
        Write-Host "❌ Interactive test failed: $_" -ForegroundColor Red
    }
}

# Main script execution
function Main {
    Write-Host "Target Host: $Host" -ForegroundColor Blue
    Write-Host "Test Type: $TestType" -ForegroundColor Blue
    Write-Host ""
    
    # Check dependencies
    Test-Dependencies
    
    # Install requirements
    Install-Dependencies
    
    # Check server health
    if (!(Test-ServerHealth -HostUrl $Host)) {
        Write-Host ""
        Write-Host "💡 To start the server, run:" -ForegroundColor Yellow
        Write-Host "   cd ..\backend" -ForegroundColor Gray
        Write-Host "   python -m uvicorn app.sliding_window_demo:app --reload" -ForegroundColor Gray
        exit 1
    }
    
    Write-Host ""
    
    # Run appropriate test based on type
    switch ($TestType.ToLower()) {
        "basic" {
            Start-BasicLoadTest -HostUrl $Host -UserCount $Users -TestDuration $Duration
        }
        "advanced" {
            Start-AdvancedTests -HostUrl $Host
        }
        "interactive" {
            Start-InteractiveTest -HostUrl $Host
        }
        "all" {
            Write-Host "🔄 Running all test types..." -ForegroundColor Blue
            Start-BasicLoadTest -HostUrl $Host -UserCount 50 -TestDuration 60
            Write-Host ""
            Start-AdvancedTests -HostUrl $Host
        }
        default {
            Write-Host "❌ Unknown test type: $TestType" -ForegroundColor Red
            Write-Host "Available types: basic, advanced, interactive, all" -ForegroundColor Yellow
        }
    }
    
    Write-Host ""
    Write-Host "🎉 Load testing completed!" -ForegroundColor Green
}

# Show help if requested
if ($args -contains "--help" -or $args -contains "-h") {
    Write-Host "Rate Limiter Load Testing Script"
    Write-Host ""
    Write-Host "Usage:"
    Write-Host "  .\run_load_tests.ps1 [-Host <url>] [-TestType <type>] [-Users <count>] [-Duration <seconds>]"
    Write-Host ""
    Write-Host "Parameters:"
    Write-Host "  -Host      Target server URL (default: http://localhost:8000)"
    Write-Host "  -TestType  Type of test: basic, advanced, interactive, all (default: all)"
    Write-Host "  -Users     Number of concurrent users for basic test (default: 50)"
    Write-Host "  -Duration  Duration in seconds for basic test (default: 120)"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\run_load_tests.ps1                                    # Run all tests"
    Write-Host "  .\run_load_tests.ps1 -TestType basic -Users 100        # Basic test with 100 users"
    Write-Host "  .\run_load_tests.ps1 -TestType interactive              # Interactive web UI test"
    exit 0
}

# Run main function
Main