@echo off
setlocal
cd /d "%~dp0"

if exist ".env" (
    for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
        if "%%A"=="SUPABASE_DB_URL" set "SUPABASE_DB_URL=%%B"
    )
)

if "%SUPABASE_DB_URL%"=="" (
    echo SUPABASE_DB_URL is missing. Add the Supabase database connection string to backend\.env.
    exit /b 1
)

where psql >nul 2>nul
if errorlevel 1 (
    echo psql is not installed or not available in PATH.
    exit /b 1
)

psql "%SUPABASE_DB_URL%" -f "migrations\001_init.sql"
