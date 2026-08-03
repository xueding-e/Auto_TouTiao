<#
.SYNOPSIS
    启动多个独立 Chrome 实例用于并行 E2E 测试
.DESCRIPTION
    启动 3 个带不同调试端口的 Chrome 实例（9222/9223/9224），
    每个实例使用独立的用户数据目录，支持真正的并行测试。
    已在运行的端口会被跳过。
.PARAMETER Count
    要启动的实例数量，默认 3
.PARAMETER ChromePath
    Chrome 可执行文件路径，默认自动探测
.EXAMPLE
    .\start-chrome-instances.ps1
    .\start-chrome-instances.ps1 -Count 2
#>
param(
    [int]$Count = 3,
    [string]$ChromePath = ""
)

# 探测 Chrome 路径
if ([string]::IsNullOrEmpty($ChromePath)) {
    $candidates = @(
        "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe",
        "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
        "${env:LocalAppData}\Google\Chrome\Application\chrome.exe"
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) { $ChromePath = $c; break }
    }
}

if (-not (Test-Path $ChromePath)) {
    Write-Error "未找到 Chrome，请通过 -ChromePath 参数指定路径"
    exit 1
}

Write-Host "Chrome 路径: $ChromePath" -ForegroundColor Cyan

# 实例配置：端口 + 用户数据目录
$instances = @(
    @{ Port = 9222; DataDir = "$env:TEMP\chrome-e2e-instance-1" }
    @{ Port = 9223; DataDir = "$env:TEMP\chrome-e2e-instance-2" }
    @{ Port = 9224; DataDir = "$env:TEMP\chrome-e2e-instance-3" }
) | Select-Object -First $Count

$started = 0
$skipped = 0

foreach ($inst in $instances) {
    $port = $inst.Port
    $dataDir = $inst.DataDir

    # 检查端口是否已被占用（实例可能已在运行）
    $inUse = $false
    try {
        $connection = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
        if ($connection) {
            # 进一步验证是否是 Chrome 调试端口
            try {
                $response = Invoke-WebRequest -Uri "http://localhost:$port/json/version" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
                if ($response.StatusCode -eq 200) {
                    $inUse = $true
                    Write-Host "[跳过] 端口 $port 已有 Chrome 调试实例运行" -ForegroundColor Yellow
                    $skipped++
                    continue
                }
            } catch {
                # 端口被占用但不是 Chrome 调试端口，报错
                Write-Error "端口 $port 被其他程序占用，请释放后重试"
                exit 1
            }
        }
    } catch {
        # Get-NetTCPConnection 在某些环境不可用，忽略继续
    }

    # 确保用户数据目录存在
    if (-not (Test-Path $dataDir)) {
        New-Item -ItemType Directory -Path $dataDir -Force | Out-Null
    }

    # 启动 Chrome 实例
    $args = @(
        "--remote-debugging-port=$port",
        "--user-data-dir=$dataDir",
        "--ignore-certificate-errors",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-features=TranslateUI",
        "--window-size=1280,900"
    )

    Start-Process -FilePath $ChromePath -ArgumentList $args -WindowStyle Normal
    $started++
    Write-Host "[启动] 端口 $port -> 数据目录 $dataDir" -ForegroundColor Green

    # 等待实例就绪
    Start-Sleep -Seconds 2
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$port/json/version" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
        Write-Host "  验证成功: $($response.Content.Substring(0, [Math]::Min(80, $response.Content.Length)))..." -ForegroundColor DarkGray
    } catch {
        Write-Warning "  端口 $port 的调试服务未就绪，可能需要多等几秒"
    }
}

Write-Host ""
Write-Host "完成: 新启动 $started 个，跳过 $skipped 个" -ForegroundColor Cyan
Write-Host "调试端口列表: $($instances.Port -join ', ')" -ForegroundColor Cyan
