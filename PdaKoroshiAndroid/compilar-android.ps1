$ErrorActionPreference = 'Stop'

# Script de compilacion de la demo PDA offline para Android.
# No conecta con Odoo ni escribe datos de produccion.

$projectRoot = Split-Path -Parent $PSScriptRoot
$projectFile = Join-Path $PSScriptRoot 'PdaKoroshiAndroid.csproj'
$androidSdkPath = Join-Path $projectRoot '.android-sdk'
$javaSdkPath = 'C:\Program Files\Microsoft\jdk-17.0.21.21-hotspot'
$cliHomePath = Join-Path $projectRoot '.dotnet-cli'
$runtimeIdentifier = 'android-arm64'
$targetFramework = 'net10.0-android'
$configuration = 'Debug'

if (-not (Test-Path -LiteralPath $androidSdkPath)) {
    throw "No se encuentra el Android SDK local: $androidSdkPath"
}

if (-not (Test-Path -LiteralPath $javaSdkPath)) {
    throw "No se encuentra Java 17: $javaSdkPath"
}

$env:DOTNET_CLI_HOME = $cliHomePath
$env:JAVA_HOME = $javaSdkPath
$env:PATH = (Join-Path $javaSdkPath 'bin') + ';' + $env:PATH

$msbuildArguments = @(
    $projectFile
    '-t:SignAndroidPackage'
    "-p:TargetFramework=$targetFramework"
    "-p:Configuration=$configuration"
    "-p:RuntimeIdentifier=$runtimeIdentifier"
    "-p:RuntimeIdentifiers=$runtimeIdentifier"
    "-p:AndroidSdkDirectory=$androidSdkPath"
    "-p:JavaSdkDirectory=$javaSdkPath"
    '-p:AndroidPackageFormat=apk'
    '-p:AndroidPackageFormats=apk'
    '-p:AndroidUseApkSigner=true'
    '-p:EmbedAssembliesIntoApk=true'
    '-p:AndroidUseDebugRuntime=false'
    '-p:PublishTrimmed=false'
    '-p:AndroidLinkMode=None'
    '-v:minimal'
)

# MSBuild puede acabar con error en el paso de firma temporal del sandbox,
# pero deja el APK sin firmar preparado para firmarlo en el paso siguiente.
$buildOutput = & dotnet msbuild @msbuildArguments 2>&1
$buildExitCode = $LASTEXITCODE
$buildOutput | Write-Output

$unsignedApk = Join-Path $projectRoot 'PdaKoroshiAndroid\bin\Debug\net10.0-android\android-arm64\com.effec.koroshi.pda.test.apk'
if (-not (Test-Path -LiteralPath $unsignedApk)) {
    throw "La compilacion no ha generado el APK base. Codigo MSBuild: $buildExitCode"
}

$apksigner = Join-Path $androidSdkPath 'build-tools\36.0.0\apksigner.bat'
$debugKeystore = Join-Path $env:USERPROFILE '.android\debug.keystore'
if (-not (Test-Path -LiteralPath $apksigner)) {
    throw "No se encuentra apksigner: $apksigner"
}

if (-not (Test-Path -LiteralPath $debugKeystore)) {
    throw "No se encuentra el keystore de pruebas: $debugKeystore"
}

$versionsDirectory = Join-Path $projectRoot 'bin\versiones'
New-Item -ItemType Directory -Path $versionsDirectory -Force | Out-Null
$stamp = Get-Date -Format 'yyyy-MM-dd_HHmmss'
$signedApk = Join-Path $versionsDirectory "pda_koroshi_android_test_$stamp.apk"

& $apksigner sign `
    --ks $debugKeystore `
    --ks-pass 'pass:android' `
    --ks-key-alias androiddebugkey `
    --key-pass 'pass:android' `
    --min-sdk-version 23 `
    --max-sdk-version 36 `
    --out $signedApk `
    $unsignedApk

if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $signedApk)) {
    throw 'No se ha podido firmar el APK de pruebas.'
}

& $apksigner verify $signedApk
if ($LASTEXITCODE -ne 0) {
    throw 'La verificacion de firma del APK ha fallado.'
}

Write-Output "APK generado y verificado: $signedApk"
