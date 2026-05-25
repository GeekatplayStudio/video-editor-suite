@echo off
setlocal EnableExtensions DisableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..\..") do set "DEFAULT_COMFY_ROOT=%%~fI"
set "DEFAULT_DOWNLOAD_ROOT=%UserProfile%\OneDrive\Downloads\Geekatplay-VideoEditorSuite-cache"
if not exist "%UserProfile%\OneDrive" set "DEFAULT_DOWNLOAD_ROOT=%UserProfile%\Downloads\Geekatplay-VideoEditorSuite-cache"

set "COMFY_ROOT=%DEFAULT_COMFY_ROOT%"
set "MODELS_ROOT="
set "DOWNLOAD_ROOT=%DEFAULT_DOWNLOAD_ROOT%"
set "PYTHON_EXE="
set "PYTHON_ARGS="
set "INSTALL_DEPS=1"
set "INSTALL_MODELS=1"
set "INSTALL_FFMPEG=1"
set "PAUSE_AT_END=1"
set "SHOW_HELP=0"

call :parse_args %*
if errorlevel 1 goto :fail

if "%SHOW_HELP%"=="1" goto :help

if not defined MODELS_ROOT set "MODELS_ROOT=%COMFY_ROOT%\models"

for %%I in ("%COMFY_ROOT%") do set "COMFY_ROOT=%%~fI"
for %%I in ("%MODELS_ROOT%") do set "MODELS_ROOT=%%~fI"
for %%I in ("%DOWNLOAD_ROOT%") do set "DOWNLOAD_ROOT=%%~fI"

call :ensure_dir "%DOWNLOAD_ROOT%"
if errorlevel 1 goto :fail

if "%INSTALL_MODELS%"=="1" (
    call :ensure_dir "%MODELS_ROOT%"
    if errorlevel 1 goto :fail
)

echo.
echo Geekatplay Video Editor Suite Installer
echo.
echo ComfyUI root:
echo   %COMFY_ROOT%
echo Download cache:
echo   %DOWNLOAD_ROOT%
echo Models root:
echo   %MODELS_ROOT%
echo.
echo This installer can set up:
echo   - Python packages from requirements.txt
echo   - ffmpeg for workflow and VHS compatibility
echo   - The bundled LTX workflow model set and workflow-safe aliases
echo.
echo Note: the three editor/export demo workflows do not need AI models.
echo The model download step is for the bundled LTX workflows.

if "%INSTALL_DEPS%"=="1" (
    call :find_python
    if errorlevel 1 goto :fail
    echo.
    echo Using Python:
    call echo   %%PYTHON_EXE%% %%PYTHON_ARGS%%
)

if "%INSTALL_DEPS%"=="1" (
    call :install_python_deps
    if errorlevel 1 goto :fail
)

if "%INSTALL_FFMPEG%"=="1" (
    call :ensure_ffmpeg
    if errorlevel 1 goto :fail
)

if "%INSTALL_MODELS%"=="1" (
    call :install_models
    if errorlevel 1 goto :fail
)

echo.
echo Finished.
echo Restart ComfyUI before opening workflows.
goto :done

:help
echo.
echo Usage: install.bat [options]
echo.
echo Default behavior:
echo   Installs Python dependencies, ffmpeg, and the bundled LTX workflow models.
echo.
echo Options:
echo   --deps-only            Install Python dependencies only.
echo   --models-only          Download models only.
echo   --skip-ffmpeg          Skip ffmpeg setup.
echo   --comfy-root PATH      Override the detected ComfyUI root.
echo   --models-root PATH     Override the target models folder.
echo   --download-root PATH   Override the download cache folder.
echo   --python PATH          Use a specific Python executable.
echo   --no-pause             Exit immediately when the script finishes.
echo   --help                 Show this help text.
goto :done

:fail
echo.
echo Install did not complete successfully.
goto :done_with_error

:done
if "%PAUSE_AT_END%"=="1" pause
exit /b 0

:done_with_error
if "%PAUSE_AT_END%"=="1" pause
exit /b 1

:parse_args
if "%~1"=="" exit /b 0

if /I "%~1"=="--help" (
    set "SHOW_HELP=1"
    shift
    goto :parse_args
)

if /I "%~1"=="--no-pause" (
    set "PAUSE_AT_END=0"
    shift
    goto :parse_args
)

if /I "%~1"=="--deps-only" (
    set "INSTALL_MODELS=0"
    shift
    goto :parse_args
)

if /I "%~1"=="--models-only" (
    set "INSTALL_DEPS=0"
    shift
    goto :parse_args
)

if /I "%~1"=="--skip-ffmpeg" (
    set "INSTALL_FFMPEG=0"
    shift
    goto :parse_args
)

if /I "%~1"=="--comfy-root" (
    if "%~2"=="" (
        echo ERROR: --comfy-root requires a path.
        exit /b 1
    )
    set "COMFY_ROOT=%~2"
    shift
    shift
    goto :parse_args
)

if /I "%~1"=="--models-root" (
    if "%~2"=="" (
        echo ERROR: --models-root requires a path.
        exit /b 1
    )
    set "MODELS_ROOT=%~2"
    shift
    shift
    goto :parse_args
)

if /I "%~1"=="--download-root" (
    if "%~2"=="" (
        echo ERROR: --download-root requires a path.
        exit /b 1
    )
    set "DOWNLOAD_ROOT=%~2"
    shift
    shift
    goto :parse_args
)

if /I "%~1"=="--python" (
    if "%~2"=="" (
        echo ERROR: --python requires a path.
        exit /b 1
    )
    set "PYTHON_EXE=%~2"
    set "PYTHON_ARGS="
    shift
    shift
    goto :parse_args
)

echo ERROR: Unknown option %~1
exit /b 1

:ensure_dir
if not exist "%~1" mkdir "%~1"
if errorlevel 1 (
    echo ERROR: Could not create folder:
    echo   %~1
    exit /b 1
)
exit /b 0

:find_python
if defined PYTHON_EXE (
    if exist "%PYTHON_EXE%" exit /b 0
    where "%PYTHON_EXE%" >nul 2>nul
    if not errorlevel 1 exit /b 0
    echo ERROR: The requested Python executable was not found:
    echo   %PYTHON_EXE%
    exit /b 1
)

for %%I in ("%COMFY_ROOT%\.venv\Scripts\python.exe") do if exist "%%~fI" set "PYTHON_EXE=%%~fI"
if defined PYTHON_EXE exit /b 0

for %%I in ("%COMFY_ROOT%\python_embeded\python.exe") do if exist "%%~fI" set "PYTHON_EXE=%%~fI"
if defined PYTHON_EXE exit /b 0

for %%I in ("%COMFY_ROOT%\..\python_embeded\python.exe") do if exist "%%~fI" set "PYTHON_EXE=%%~fI"
if defined PYTHON_EXE exit /b 0

for %%I in ("%SCRIPT_DIR%\.venv\Scripts\python.exe") do if exist "%%~fI" set "PYTHON_EXE=%%~fI"
if defined PYTHON_EXE exit /b 0

where python >nul 2>nul
if not errorlevel 1 (
    set "PYTHON_EXE=python"
    exit /b 0
)

where py >nul 2>nul
if not errorlevel 1 (
    set "PYTHON_EXE=py"
    set "PYTHON_ARGS=-3"
    exit /b 0
)

echo ERROR: No Python executable was found.
echo Install Python or use the ComfyUI .venv / python_embeded distribution.
exit /b 1

:run_python
"%PYTHON_EXE%" %PYTHON_ARGS% %*
exit /b %errorlevel%

:install_python_deps
echo.
echo Installing Python dependencies...
call :check_python_not_busy
if errorlevel 1 exit /b 1

call :run_python -m pip --version
if errorlevel 1 (
    echo ERROR: pip is not available in the selected Python environment.
    exit /b 1
)

call :run_python -m pip install --upgrade pip
if errorlevel 1 exit /b 1

call :run_python -m pip install -r "%SCRIPT_DIR%requirements.txt"
if errorlevel 1 (
    echo.
    echo ERROR: Python dependency installation failed.
    echo If the error mentions WinError 5 or access denied, close ComfyUI and any process using the portable Python folder, then rerun install.bat.
    exit /b 1
)

exit /b 0

:check_python_not_busy
if not exist "%PYTHON_EXE%" exit /b 0

set "RUNNING_COUNT="
for /f %%I in ('powershell -NoProfile -Command "$ErrorActionPreference = ''SilentlyContinue''; $path = [System.IO.Path]::GetFullPath('%PYTHON_EXE%'); @((Get-Process ^| Where-Object { $_.Path -eq $path })).Count"') do set "RUNNING_COUNT=%%I"

if not defined RUNNING_COUNT exit /b 0
if "%RUNNING_COUNT%"=="0" exit /b 0

echo ERROR: The selected Python executable is already in use:
echo   %PYTHON_EXE%
echo Close ComfyUI or any other process using that Python environment, then rerun install.bat.
exit /b 1

:ensure_ffmpeg
echo.
echo Checking ffmpeg...
where ffmpeg >nul 2>nul
if not errorlevel 1 (
    for /f "delims=" %%I in ('where ffmpeg 2^>nul') do (
        set "FFMPEG_EXE=%%~fI"
        goto :set_ffmpeg_env
    )
)

if exist "%COMFY_ROOT%\ffmpeg.exe" (
    set "FFMPEG_EXE=%COMFY_ROOT%\ffmpeg.exe"
    goto :set_ffmpeg_env
)

call :ensure_dir "%COMFY_ROOT%\tools"
if errorlevel 1 exit /b 1

set "FFMPEG_ZIP=%DOWNLOAD_ROOT%\ffmpeg-release-essentials.zip"
set "FFMPEG_EXTRACT_DIR=%COMFY_ROOT%\tools\ffmpeg"

call :download_file "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip" "%FFMPEG_ZIP%"
if errorlevel 1 exit /b 1

if exist "%FFMPEG_EXTRACT_DIR%" rmdir /s /q "%FFMPEG_EXTRACT_DIR%"
mkdir "%FFMPEG_EXTRACT_DIR%"

tar -xf "%FFMPEG_ZIP%" -C "%FFMPEG_EXTRACT_DIR%"
if errorlevel 1 (
    echo ERROR: Could not extract ffmpeg archive.
    exit /b 1
)

set "FFMPEG_EXE="
for /r "%FFMPEG_EXTRACT_DIR%" %%I in (ffmpeg.exe) do (
    set "FFMPEG_EXE=%%~fI"
    goto :copy_ffmpeg_binaries
)

echo ERROR: ffmpeg.exe was not found after extraction.
exit /b 1

:copy_ffmpeg_binaries
copy /Y "%FFMPEG_EXE%" "%COMFY_ROOT%\ffmpeg.exe" >nul
if errorlevel 1 (
    echo ERROR: Could not copy ffmpeg.exe into %COMFY_ROOT%
    exit /b 1
)

for %%N in (ffprobe.exe ffplay.exe) do (
    for /r "%FFMPEG_EXTRACT_DIR%" %%I in (%%N) do copy /Y "%%~fI" "%COMFY_ROOT%\%%N" >nul
)

set "FFMPEG_EXE=%COMFY_ROOT%\ffmpeg.exe"

:set_ffmpeg_env
echo Using ffmpeg:
echo   %FFMPEG_EXE%
setx VHS_FORCE_FFMPEG_PATH "%FFMPEG_EXE%" >nul
setx IMAGEIO_FFMPEG_EXE "%FFMPEG_EXE%" >nul
exit /b 0

:install_models
echo.
echo Downloading bundled LTX workflow models...
echo This can take a while and needs substantial disk space.

call :ensure_dir "%MODELS_ROOT%\checkpoints"
if errorlevel 1 exit /b 1
call :ensure_dir "%MODELS_ROOT%\text_encoders"
if errorlevel 1 exit /b 1
call :ensure_dir "%MODELS_ROOT%\vae"
if errorlevel 1 exit /b 1
call :ensure_dir "%MODELS_ROOT%\loras"
if errorlevel 1 exit /b 1
call :ensure_dir "%MODELS_ROOT%\loras\ltx2"
if errorlevel 1 exit /b 1
call :ensure_dir "%MODELS_ROOT%\latent_upscale_models"
if errorlevel 1 exit /b 1

call :download_file "https://huggingface.co/Lightricks/LTX-2.3-fp8/resolve/main/ltx-2.3-22b-dev-fp8.safetensors?download=true" "%MODELS_ROOT%\checkpoints\ltx-2.3-22b-dev-fp8.safetensors"
if errorlevel 1 exit /b 1

call :download_file "https://huggingface.co/Comfy-Org/ltx-2/resolve/main/split_files/text_encoders/gemma_3_12B_it_fp4_mixed.safetensors?download=true" "%MODELS_ROOT%\text_encoders\gemma_3_12B_it_fp4_mixed.safetensors"
if errorlevel 1 exit /b 1

call :download_file "https://huggingface.co/Kijai/LTX2.3_comfy/resolve/main/text_encoders/ltx-2.3_text_projection_bf16.safetensors?download=true" "%MODELS_ROOT%\text_encoders\ltx-2.3_text_projection_bf16.safetensors"
if errorlevel 1 exit /b 1

call :download_file "https://huggingface.co/Kijai/LTX2.3_comfy/resolve/main/vae/LTX23_audio_vae_bf16.safetensors?download=true" "%MODELS_ROOT%\vae\LTX23_audio_vae_bf16.safetensors"
if errorlevel 1 exit /b 1

call :download_file "https://huggingface.co/Kijai/LTX2.3_comfy/resolve/main/vae/LTX23_video_vae_bf16.safetensors?download=true" "%MODELS_ROOT%\vae\LTX23_video_vae_bf16.safetensors"
if errorlevel 1 exit /b 1

call :download_file "https://huggingface.co/Kijai/LTX2.3_comfy/resolve/main/vae/taeltx2_3.safetensors?download=true" "%MODELS_ROOT%\vae\taeltx2_3.safetensors"
if errorlevel 1 exit /b 1

call :download_file "https://huggingface.co/Lightricks/LTX-2.3/resolve/main/ltx-2.3-spatial-upscaler-x2-1.1.safetensors?download=true" "%MODELS_ROOT%\latent_upscale_models\ltx-2.3-spatial-upscaler-x2-1.1.safetensors"
if errorlevel 1 exit /b 1

call :download_file "https://huggingface.co/Lightricks/LTX-2.3/resolve/main/ltx-2.3-spatial-upscaler-x1.5-1.0.safetensors?download=true" "%MODELS_ROOT%\latent_upscale_models\ltx-2.3-spatial-upscaler-x1.5-1.0.safetensors"
if errorlevel 1 exit /b 1

call :download_file "https://huggingface.co/Lightricks/LTX-2.3/resolve/main/ltx-2.3-22b-distilled-lora-384.safetensors?download=true" "%MODELS_ROOT%\loras\ltx-2.3-22b-distilled-lora-384.safetensors"
if errorlevel 1 exit /b 1

call :ensure_alias "%MODELS_ROOT%\loras\ltx-2.3-22b-distilled-lora-384.safetensors" "%MODELS_ROOT%\loras\ltx2\ltx-2.3-22b-distilled-lora-dynamic_fro09_avg_rank_105_bf16.safetensors"
if errorlevel 1 exit /b 1

set "VERIFY_FAILED=0"
echo.
echo Verifying model files...
call :verify_exists "%MODELS_ROOT%\checkpoints\ltx-2.3-22b-dev-fp8.safetensors" "FP8 checkpoint"
call :verify_exists "%MODELS_ROOT%\text_encoders\gemma_3_12B_it_fp4_mixed.safetensors" "Gemma text encoder"
call :verify_exists "%MODELS_ROOT%\text_encoders\ltx-2.3_text_projection_bf16.safetensors" "Text projection"
call :verify_exists "%MODELS_ROOT%\vae\LTX23_audio_vae_bf16.safetensors" "Audio VAE"
call :verify_exists "%MODELS_ROOT%\vae\LTX23_video_vae_bf16.safetensors" "Video VAE"
call :verify_exists "%MODELS_ROOT%\vae\taeltx2_3.safetensors" "TAE"
call :verify_exists "%MODELS_ROOT%\latent_upscale_models\ltx-2.3-spatial-upscaler-x2-1.1.safetensors" "x2 latent upscaler"
call :verify_exists "%MODELS_ROOT%\latent_upscale_models\ltx-2.3-spatial-upscaler-x1.5-1.0.safetensors" "x1.5 latent upscaler"
call :verify_exists "%MODELS_ROOT%\loras\ltx-2.3-22b-distilled-lora-384.safetensors" "Distilled LoRA"
call :verify_exists "%MODELS_ROOT%\loras\ltx2\ltx-2.3-22b-distilled-lora-dynamic_fro09_avg_rank_105_bf16.safetensors" "Workflow LoRA alias"

if "%VERIFY_FAILED%"=="1" exit /b 1
exit /b 0

:ensure_alias
set "SOURCE_FILE=%~1"
set "ALIAS_FILE=%~2"

if not exist "%SOURCE_FILE%" (
    echo ERROR: Alias source file is missing:
    echo   %SOURCE_FILE%
    exit /b 1
)

call :ensure_dir "%~dp2"
if errorlevel 1 exit /b 1

if exist "%ALIAS_FILE%" exit /b 0

mklink /H "%ALIAS_FILE%" "%SOURCE_FILE%" >nul 2>nul
if errorlevel 1 copy /Y "%SOURCE_FILE%" "%ALIAS_FILE%" >nul
if errorlevel 1 (
    echo ERROR: Could not create workflow alias:
    echo   %ALIAS_FILE%
    exit /b 1
)
exit /b 0

:verify_exists
if exist "%~1" (
    echo   OK     %~2: %~1
    exit /b 0
)

echo   MISSING %~2: %~1
set "VERIFY_FAILED=1"
exit /b 0

:download_file
set "URL=%~1"
set "DEST=%~2"

if exist "%DEST%" (
    echo Found existing file:
    echo   %DEST%
    exit /b 0
)

call :ensure_dir "%~dp2"
if errorlevel 1 exit /b 1

echo.
echo Downloading:
echo   %DEST%
curl.exe -L --fail --progress-bar -C - -o "%DEST%" "%URL%"
if errorlevel 1 (
    echo ERROR: Download failed for:
    echo   %DEST%
    exit /b 1
)
exit /b 0