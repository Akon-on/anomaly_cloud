param(
    [int]$RunsPerScenario = 10,
    [string[]]$Scenarios = @("balanced", "aggressive", "mostly-normal"),
    [int]$BaseSeed = 1000
)

$ErrorActionPreference = "Stop"

function Get-StdDev {
    param([double[]]$Values)

    if ($null -eq $Values -or $Values.Count -lt 2) {
        return 0.0
    }

    $mean = ($Values | Measure-Object -Average).Average
    $variance = ($Values | ForEach-Object { [Math]::Pow($_ - $mean, 2) } | Measure-Object -Sum).Sum / ($Values.Count - 1)
    return [Math]::Sqrt($variance)
}

function Write-MarkdownTable {
    param(
        [string]$Path,
        [object[]]$Rows,
        [string[]]$Columns
    )

    $lines = @()
    $lines += "| " + ($Columns -join " | ") + " |"
    $lines += "| " + (($Columns | ForEach-Object { "---" }) -join " | ") + " |"

    foreach ($row in $Rows) {
        $vals = @()
        foreach ($col in $Columns) {
            $vals += [string]$row.$col
        }
        $lines += "| " + ($vals -join " | ") + " |"
    }

    Set-Content -Path $Path -Value ($lines -join "`n") -Encoding UTF8
}

$outputDir = Join-Path $PSScriptRoot "output"
$runsDir = Join-Path $outputDir "runs"
$null = New-Item -ItemType Directory -Force -Path $runsDir

$allRows = @()
$globalRunIndex = 0

Write-Host "Building images once before batch runs..."
docker compose build ml ml_eval traffic
if ($LASTEXITCODE -ne 0) {
    throw "Failed to build docker images"
}

foreach ($scenario in $Scenarios) {
    Write-Host "\n=== Scenario: $scenario ==="

    $scenarioDir = Join-Path $runsDir $scenario
    $null = New-Item -ItemType Directory -Force -Path $scenarioDir

    for ($run = 1; $run -le $RunsPerScenario; $run++) {
        $globalRunIndex++
        $seed = $BaseSeed + $globalRunIndex

        Write-Host "Run $run/$RunsPerScenario (seed=$seed)"
        & "$PSScriptRoot\run_experiment.ps1" -Scenario $scenario -SeedOverride $seed -SkipBuild
        if ($LASTEXITCODE -ne 0) {
            throw "Experiment failed for scenario=$scenario run=$run"
        }

        $comparisonPath = Join-Path $outputDir "model_comparison.csv"
        if (-not (Test-Path $comparisonPath)) {
            throw "Missing model_comparison.csv after run"
        }

        $runCsvPath = Join-Path $scenarioDir ("run_{0:00}_model_comparison.csv" -f $run)
        Copy-Item -Path $comparisonPath -Destination $runCsvPath -Force

        $rows = Import-Csv $comparisonPath
        foreach ($row in $rows) {
            $allRows += [pscustomobject]@{
                scenario = $scenario
                run = $run
                seed = $seed
                model = $row.model
                precision = [double]$row.precision
                recall = [double]$row.recall
                f1 = [double]$row.f1
                accuracy = [double]$row.accuracy
                roc_auc = if ([string]::IsNullOrWhiteSpace($row.roc_auc)) { $null } else { [double]$row.roc_auc }
                pr_auc = if ([string]::IsNullOrWhiteSpace($row.pr_auc)) { $null } else { [double]$row.pr_auc }
                label_source = $row.label_source
            }
        }
    }
}

$allRunsCsv = Join-Path $outputDir "batch_all_runs.csv"
$allRows | Export-Csv -Path $allRunsCsv -NoTypeInformation

$summaryRows = @()
$groups = $allRows | Group-Object scenario, model

foreach ($g in $groups) {
    $groupRows = $g.Group
    $scenario = $groupRows[0].scenario
    $model = $groupRows[0].model

    $f1Vals = @($groupRows | ForEach-Object { [double]$_.f1 })
    $rocVals = @($groupRows | Where-Object { $null -ne $_.roc_auc } | ForEach-Object { [double]$_.roc_auc })
    $prVals = @($groupRows | Where-Object { $null -ne $_.pr_auc } | ForEach-Object { [double]$_.pr_auc })

    $summaryRows += [pscustomobject]@{
        scenario = $scenario
        model = $model
        runs = $groupRows.Count
        f1_mean = "{0:N4}" -f (($f1Vals | Measure-Object -Average).Average)
        f1_std = "{0:N4}" -f (Get-StdDev -Values $f1Vals)
        roc_auc_mean = if ($rocVals.Count -eq 0) { "N/A" } else { "{0:N4}" -f (($rocVals | Measure-Object -Average).Average) }
        roc_auc_std = if ($rocVals.Count -eq 0) { "N/A" } else { "{0:N4}" -f (Get-StdDev -Values $rocVals) }
        pr_auc_mean = if ($prVals.Count -eq 0) { "N/A" } else { "{0:N4}" -f (($prVals | Measure-Object -Average).Average) }
        pr_auc_std = if ($prVals.Count -eq 0) { "N/A" } else { "{0:N4}" -f (Get-StdDev -Values $prVals) }
    }
}

$summarySorted = $summaryRows | Sort-Object scenario, @{Expression = "f1_mean"; Descending = $true}

$summaryCsv = Join-Path $outputDir "batch_summary_stats.csv"
$summarySorted | Export-Csv -Path $summaryCsv -NoTypeInformation

$summaryTxt = Join-Path $outputDir "batch_summary_stats.txt"
$summarySorted | Format-Table -AutoSize | Out-String | Set-Content -Path $summaryTxt -Encoding UTF8

$summaryMd = Join-Path $outputDir "batch_summary_stats.md"
Write-MarkdownTable -Path $summaryMd -Rows $summarySorted -Columns @(
    "scenario", "model", "runs", "f1_mean", "f1_std", "roc_auc_mean", "roc_auc_std", "pr_auc_mean", "pr_auc_std"
)

Write-Host "\nBatch experiment artifacts saved:"
Write-Host "- $allRunsCsv"
Write-Host "- $summaryCsv"
Write-Host "- $summaryTxt"
Write-Host "- $summaryMd"
