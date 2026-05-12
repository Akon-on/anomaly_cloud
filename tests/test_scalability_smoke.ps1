$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$tempRoot = Join-Path $repoRoot "tests\.tmp_scalability_smoke"
$logsDir = Join-Path $tempRoot "logs"
$outDir = Join-Path $tempRoot "output"

if (Test-Path $tempRoot) {
    Remove-Item -Recurse -Force $tempRoot
}

New-Item -ItemType Directory -Path $logsDir | Out-Null
New-Item -ItemType Directory -Path $outDir | Out-Null

$accessLog = Join-Path $logsDir "access.log"
$labelFile = Join-Path $logsDir "traffic_labels.jsonl"

$windowCount = 400
$recordsPerWindow = 20

$accessWriter = [System.IO.StreamWriter]::new($accessLog, $false, [System.Text.Encoding]::UTF8)
$labelWriter = [System.IO.StreamWriter]::new($labelFile, $false, [System.Text.Encoding]::UTF8)

try {
    for ($w = 0; $w -lt $windowCount; $w++) {
        $baseTime = $w * 10
        $isAttackWindow = ($w -ge 140 -and $w -lt 260)

        for ($i = 0; $i -lt $recordsPerWindow; $i++) {
            $ip = if (($i % 2) -eq 0) { "10.0.0.10" } else { "10.0.0.11" }
            $endpoint = if ($isAttackWindow -and ($i % 3 -eq 0)) { "/admin" } else { "/" }
            $status = if ($isAttackWindow -and ($i % 4 -eq 0)) { "fail" } else { "ok" }
            $userAgent = if (($i % 2) -eq 0) { "ua-a" } else { "ua-b" }

            $record = @{
                time = $baseTime + ($i * 0.1)
                ip = $ip
                endpoint = $endpoint
                status = $status
                user_agent = $userAgent
            } | ConvertTo-Json -Compress
            $accessWriter.WriteLine($record)
        }

        $labelType = if ($isAttackWindow) { "attack" } else { "normal" }
        foreach ($ipValue in @("10.0.0.10", "10.0.0.11")) {
            $label = @{
                time = $baseTime
                label = $labelType
                client_ip = $ipValue
            } | ConvertTo-Json -Compress
            $labelWriter.WriteLine($label)
        }
    }
}
finally {
    $accessWriter.Dispose()
    $labelWriter.Dispose()
}

Push-Location $repoRoot
try {
    $timing = Measure-Command {
        docker compose run --rm --build --no-deps `
            -v "${logsDir}:/logs" `
            -v "${outDir}:/app/output" `
            -e EVAL_MIN_BASELINE_WINDOWS=3 `
            ml_eval | Out-Null
    }

    $durationSec = [Math]::Round($timing.TotalSeconds, 3)
    $comparisonPath = Join-Path $outDir "model_comparison.csv"
    if (-not (Test-Path $comparisonPath)) {
        throw "Scalability test failed: model_comparison.csv not generated"
    }

    $rows = Import-Csv -Path $comparisonPath
    if ($rows.Count -lt 4) {
        throw "Scalability test failed: expected at least 4 models in model_comparison.csv"
    }

    $result = [pscustomobject]@{
        windows = $windowCount
        records_per_window = $recordsPerWindow
        total_records = $windowCount * $recordsPerWindow
        duration_seconds = $durationSec
        generated_models = $rows.Count
        generated_at = (Get-Date).ToString("o")
    }

    $resultPath = Join-Path $outDir "scalability_smoke_result.json"
    $result | ConvertTo-Json -Depth 3 | Set-Content -Path $resultPath -Encoding UTF8

    Write-Host "Scalability smoke test passed in $durationSec s"
    Write-Host "Result: $resultPath"
}
finally {
    Pop-Location
}
