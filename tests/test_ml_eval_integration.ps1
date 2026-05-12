$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$tempRoot = Join-Path $repoRoot "tests\.tmp_ml_eval_integration"
$logsDir = Join-Path $tempRoot "logs"
$outDir = Join-Path $tempRoot "output"

if (Test-Path $tempRoot) {
    Remove-Item -Recurse -Force $tempRoot
}

New-Item -ItemType Directory -Path $logsDir | Out-Null
New-Item -ItemType Directory -Path $outDir | Out-Null

$accessLog = Join-Path $logsDir "access.log"
$labelFile = Join-Path $logsDir "traffic_labels.jsonl"

$accessRecords = @(
    @{ time = 1; ip = "10.0.0.1"; endpoint = "/"; status = "ok"; user_agent = "ua-a" },
    @{ time = 2; ip = "10.0.0.1"; endpoint = "/login"; status = "success"; user_agent = "ua-a" },
    @{ time = 3; ip = "10.0.0.2"; endpoint = "/"; status = "ok"; user_agent = "ua-b" },
    @{ time = 4; ip = "10.0.0.2"; endpoint = "/login"; status = "fail"; user_agent = "ua-b" },
    @{ time = 11; ip = "10.0.0.1"; endpoint = "/"; status = "ok"; user_agent = "ua-a" },
    @{ time = 12; ip = "10.0.0.1"; endpoint = "/login"; status = "success"; user_agent = "ua-a" },
    @{ time = 13; ip = "10.0.0.2"; endpoint = "/"; status = "ok"; user_agent = "ua-b" },
    @{ time = 14; ip = "10.0.0.2"; endpoint = "/login"; status = "fail"; user_agent = "ua-b" },
    @{ time = 21; ip = "10.0.0.1"; endpoint = "/admin"; status = "ok"; user_agent = "ua-a" },
    @{ time = 22; ip = "10.0.0.1"; endpoint = "/login"; status = "fail"; user_agent = "ua-a" },
    @{ time = 23; ip = "10.0.0.2"; endpoint = "/admin"; status = "ok"; user_agent = "ua-b" },
    @{ time = 24; ip = "10.0.0.2"; endpoint = "/login"; status = "fail"; user_agent = "ua-b" },
    @{ time = 31; ip = "10.0.0.1"; endpoint = "/"; status = "ok"; user_agent = "ua-a" },
    @{ time = 32; ip = "10.0.0.1"; endpoint = "/"; status = "ok"; user_agent = "ua-a" },
    @{ time = 33; ip = "10.0.0.2"; endpoint = "/"; status = "ok"; user_agent = "ua-b" },
    @{ time = 34; ip = "10.0.0.2"; endpoint = "/login"; status = "success"; user_agent = "ua-b" }
)

$accessRecords | ForEach-Object {
    $_ | ConvertTo-Json -Compress
} | Set-Content -Path $accessLog -Encoding utf8

$labels = @(
    @{ time = 1; label = "normal"; client_ip = "10.0.0.1" },
    @{ time = 2; label = "normal"; client_ip = "10.0.0.1" },
    @{ time = 3; label = "normal"; client_ip = "10.0.0.2" },
    @{ time = 4; label = "normal"; client_ip = "10.0.0.2" },
    @{ time = 11; label = "normal"; client_ip = "10.0.0.1" },
    @{ time = 12; label = "normal"; client_ip = "10.0.0.1" },
    @{ time = 13; label = "normal"; client_ip = "10.0.0.2" },
    @{ time = 14; label = "normal"; client_ip = "10.0.0.2" },
    @{ time = 21; label = "attack"; client_ip = "10.0.0.1" },
    @{ time = 22; label = "attack"; client_ip = "10.0.0.1" },
    @{ time = 23; label = "attack"; client_ip = "10.0.0.2" },
    @{ time = 24; label = "attack"; client_ip = "10.0.0.2" },
    @{ time = 31; label = "normal"; client_ip = "10.0.0.1" },
    @{ time = 32; label = "normal"; client_ip = "10.0.0.1" },
    @{ time = 33; label = "normal"; client_ip = "10.0.0.2" },
    @{ time = 34; label = "normal"; client_ip = "10.0.0.2" }
)

$labels | ForEach-Object {
    $_ | ConvertTo-Json -Compress
} | Set-Content -Path $labelFile -Encoding utf8

Push-Location $repoRoot
try {
    docker compose run --rm --build --no-deps `
        -v "${logsDir}:/logs" `
        -v "${outDir}:/app/output" `
        -e EVAL_MIN_BASELINE_WINDOWS=2 `
        ml_eval

    $requiredFiles = @(
        "model_comparison.csv",
        "model_comparison.md",
        "model_report.md",
        "roc_curve.png",
        "pr_curve.png"
    )

    foreach ($name in $requiredFiles) {
        $filePath = Join-Path $outDir $name
        if (-not (Test-Path $filePath)) {
            throw "Missing expected artifact: $filePath"
        }
    }

    $comparisonPath = Join-Path $outDir "model_comparison.csv"
    $rows = Import-Csv -Path $comparisonPath
    if ($rows.Count -lt 3) {
        throw "Expected at least 3 model rows in model_comparison.csv"
    }

    $requiredColumns = @("model", "f1", "precision", "recall", "label_source", "evaluation_mode")
    $actualColumns = @($rows[0].PSObject.Properties.Name)
    foreach ($column in $requiredColumns) {
        if ($actualColumns -notcontains $column) {
            throw "Missing required column '$column' in model_comparison.csv"
        }
    }

    Write-Host "Integration test passed: ml_eval produced expected artifacts and columns."
}
finally {
    Pop-Location
}
