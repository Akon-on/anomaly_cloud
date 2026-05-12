param(
    [int]$RunsPerScenario = 5,
    [string[]]$Scenarios = @(
        "balanced",
        "aggressive",
        "mostly-normal",
        "credential-stuffing",
        "endpoint-scanning",
        "burst-traffic",
        "slow-brute-force",
        "mixed-attacks"
    ),
    [int]$BaseSeed = 1000,
    [ValidateSet("standard", "thesis")]
    [string]$DurationProfile = "standard"
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

function Format-Percent {
    param([double]$Value)

    return "{0:N1}%" -f ($Value * 100)
}

$outputDir = Join-Path $PSScriptRoot "output"
$runsDir = Join-Path $outputDir "runs"
$null = New-Item -ItemType Directory -Force -Path $runsDir

$allRows = @()
$globalRunIndex = 0

Write-Host "Building images once before batch runs..."
docker compose build victim ml ml_eval traffic visual
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
        & "$PSScriptRoot\run_experiment.ps1" -Scenario $scenario -SeedOverride $seed -DurationProfile $DurationProfile -SkipBuild
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
                true_negatives = if ([string]::IsNullOrWhiteSpace($row.true_negatives)) { $null } else { [int]$row.true_negatives }
                false_positives = if ([string]::IsNullOrWhiteSpace($row.false_positives)) { $null } else { [int]$row.false_positives }
                false_negatives = if ([string]::IsNullOrWhiteSpace($row.false_negatives)) { $null } else { [int]$row.false_negatives }
                true_positives = if ([string]::IsNullOrWhiteSpace($row.true_positives)) { $null } else { [int]$row.true_positives }
                roc_auc = if ([string]::IsNullOrWhiteSpace($row.roc_auc)) { $null } else { [double]$row.roc_auc }
                pr_auc = if ([string]::IsNullOrWhiteSpace($row.pr_auc)) { $null } else { [double]$row.pr_auc }
                best_threshold = if ([string]::IsNullOrWhiteSpace($row.best_threshold)) { $null } else { [double]$row.best_threshold }
                best_precision = if ([string]::IsNullOrWhiteSpace($row.best_precision)) { $null } else { [double]$row.best_precision }
                best_recall = if ([string]::IsNullOrWhiteSpace($row.best_recall)) { $null } else { [double]$row.best_recall }
                best_f1 = if ([string]::IsNullOrWhiteSpace($row.best_f1)) { $null } else { [double]$row.best_f1 }
                best_true_negatives = if ([string]::IsNullOrWhiteSpace($row.best_true_negatives)) { $null } else { [int]$row.best_true_negatives }
                best_false_positives = if ([string]::IsNullOrWhiteSpace($row.best_false_positives)) { $null } else { [int]$row.best_false_positives }
                best_false_negatives = if ([string]::IsNullOrWhiteSpace($row.best_false_negatives)) { $null } else { [int]$row.best_false_negatives }
                best_true_positives = if ([string]::IsNullOrWhiteSpace($row.best_true_positives)) { $null } else { [int]$row.best_true_positives }
                label_source = $row.label_source
                evaluation_mode = $row.evaluation_mode
                train_samples = if ([string]::IsNullOrWhiteSpace($row.train_samples)) { $null } else { [int]$row.train_samples }
            }
        }
    }
}

$allRunsCsv = Join-Path $outputDir "batch_all_runs.csv"
$allRows | Export-Csv -Path $allRunsCsv -NoTypeInformation

$summaryRows = @()
$summaryNumericRows = @()
$groups = $allRows | Group-Object scenario, model

foreach ($g in $groups) {
    $groupRows = $g.Group
    $scenario = $groupRows[0].scenario
    $model = $groupRows[0].model

    $f1Vals = @($groupRows | ForEach-Object { [double]$_.f1 })
    $rocVals = @($groupRows | Where-Object { $null -ne $_.roc_auc } | ForEach-Object { [double]$_.roc_auc })
    $prVals = @($groupRows | Where-Object { $null -ne $_.pr_auc } | ForEach-Object { [double]$_.pr_auc })
    $bestF1Vals = @($groupRows | Where-Object { $null -ne $_.best_f1 } | ForEach-Object { [double]$_.best_f1 })
    $f1Mean = ($f1Vals | Measure-Object -Average).Average
    $f1Std = Get-StdDev -Values $f1Vals
    $rocMean = if ($rocVals.Count -eq 0) { $null } else { ($rocVals | Measure-Object -Average).Average }
    $rocStd = if ($rocVals.Count -eq 0) { $null } else { Get-StdDev -Values $rocVals }
    $prMean = if ($prVals.Count -eq 0) { $null } else { ($prVals | Measure-Object -Average).Average }
    $prStd = if ($prVals.Count -eq 0) { $null } else { Get-StdDev -Values $prVals }
    $bestF1Mean = if ($bestF1Vals.Count -eq 0) { $null } else { ($bestF1Vals | Measure-Object -Average).Average }
    $bestF1Std = if ($bestF1Vals.Count -eq 0) { $null } else { Get-StdDev -Values $bestF1Vals }

    $summaryNumericRows += [pscustomobject]@{
        scenario = $scenario
        model = $model
        runs = $groupRows.Count
        f1_mean = $f1Mean
        f1_std = $f1Std
        roc_auc_mean = $rocMean
        roc_auc_std = $rocStd
        pr_auc_mean = $prMean
        pr_auc_std = $prStd
        best_f1_mean = $bestF1Mean
        best_f1_std = $bestF1Std
    }

    $summaryRows += [pscustomobject]@{
        scenario = $scenario
        model = $model
        runs = $groupRows.Count
        f1_mean = "{0:N4}" -f $f1Mean
        f1_std = "{0:N4}" -f $f1Std
        roc_auc_mean = if ($null -eq $rocMean) { "N/A" } else { "{0:N4}" -f $rocMean }
        roc_auc_std = if ($null -eq $rocStd) { "N/A" } else { "{0:N4}" -f $rocStd }
        pr_auc_mean = if ($null -eq $prMean) { "N/A" } else { "{0:N4}" -f $prMean }
        pr_auc_std = if ($null -eq $prStd) { "N/A" } else { "{0:N4}" -f $prStd }
        best_f1_mean = if ($null -eq $bestF1Mean) { "N/A" } else { "{0:N4}" -f $bestF1Mean }
        best_f1_std = if ($null -eq $bestF1Std) { "N/A" } else { "{0:N4}" -f $bestF1Std }
    }
}

$summarySorted = $summaryRows | Sort-Object scenario, @{Expression = { [double]$_.f1_mean }; Descending = $true}
$rankedRows = @()
$summaryNumericRows | Group-Object scenario | ForEach-Object {
    $rank = 0
    $_.Group | Sort-Object @{Expression = "f1_mean"; Descending = $true} | ForEach-Object {
        $rank++
        $isWinner = if ($rank -eq 1) { "yes" } else { "no" }
        $rocText = if ($null -eq $_.roc_auc_mean) { "N/A" } else { "{0:N4} +/- {1:N4}" -f $_.roc_auc_mean, $_.roc_auc_std }
        $prText = if ($null -eq $_.pr_auc_mean) { "N/A" } else { "{0:N4} +/- {1:N4}" -f $_.pr_auc_mean, $_.pr_auc_std }
        $bestF1Text = if ($null -eq $_.best_f1_mean) { "N/A" } else { "{0:N4} +/- {1:N4}" -f $_.best_f1_mean, $_.best_f1_std }

        $rankedRows += [pscustomobject]@{
            scenario = $_.scenario
            rank = $rank
            winner = $isWinner
            model = $_.model
            runs = $_.runs
            f1_score = "{0:N4} +/- {1:N4}" -f $_.f1_mean, $_.f1_std
            best_f1_score = $bestF1Text
            f1_percent = "$(Format-Percent $_.f1_mean) +/- $(Format-Percent $_.f1_std)"
            roc_auc = $rocText
            pr_auc = $prText
        }
    }
}

$summaryCsv = Join-Path $outputDir "batch_summary_stats.csv"
$summarySorted | Export-Csv -Path $summaryCsv -NoTypeInformation

$summaryTxt = Join-Path $outputDir "batch_summary_stats.txt"
$summarySorted | Format-Table -AutoSize | Out-String -Width 240 | Set-Content -Path $summaryTxt -Encoding UTF8

$summaryMd = Join-Path $outputDir "batch_summary_stats.md"
Write-MarkdownTable -Path $summaryMd -Rows $summarySorted -Columns @(
    "scenario", "model", "runs", "f1_mean", "f1_std", "best_f1_mean", "best_f1_std", "roc_auc_mean", "roc_auc_std", "pr_auc_mean", "pr_auc_std"
)

$rankedCsv = Join-Path $outputDir "batch_ranked_summary.csv"
$rankedRows | Export-Csv -Path $rankedCsv -NoTypeInformation

$rankedTxt = Join-Path $outputDir "batch_ranked_summary.txt"
$rankedRows | Format-Table -AutoSize | Out-String -Width 320 | Set-Content -Path $rankedTxt -Encoding UTF8

$rankedMd = Join-Path $outputDir "batch_ranked_summary.md"
Write-MarkdownTable -Path $rankedMd -Rows $rankedRows -Columns @(
    "scenario", "rank", "winner", "model", "runs", "f1_score", "best_f1_score", "f1_percent", "roc_auc", "pr_auc"
)

Write-Host "Generating batch charts and thesis report..."
docker compose run --rm --no-deps visual python batch_report.py
if ($LASTEXITCODE -ne 0) {
    throw "Failed to generate batch report artifacts"
}

Write-Host "\nBatch experiment artifacts saved:"
Write-Host "- $allRunsCsv"
Write-Host "- $summaryCsv"
Write-Host "- $summaryTxt"
Write-Host "- $summaryMd"
Write-Host "- $rankedCsv"
Write-Host "- $rankedTxt"
Write-Host "- $rankedMd"
Write-Host "- $(Join-Path $outputDir 'batch_overall_ranking.txt')"
Write-Host "- $(Join-Path $outputDir 'batch_f1_by_scenario.png')"
Write-Host "- $(Join-Path $outputDir 'batch_roc_auc_by_scenario.png')"
Write-Host "- $(Join-Path $outputDir 'batch_pr_auc_by_scenario.png')"
Write-Host "- $(Join-Path $outputDir 'thesis_results_report.md')"
