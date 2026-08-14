# 将 competition/ 设为只读（Windows）
# 用法：powershell -File scripts/make_readonly.ps1
$comp = Join-Path $PSScriptRoot "..\competition"
if (Test-Path $comp) {
    Get-ChildItem -Path $comp -Recurse -File | ForEach-Object {
        $_.IsReadOnly = $true
    }
    Write-Output "[完成] competition/ 已设为只读"
} else {
    Write-Output "[跳过] 未找到 competition/ 目录"
}
