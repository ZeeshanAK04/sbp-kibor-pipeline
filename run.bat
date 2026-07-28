@echo off
:: SBP Pipeline Launcher
:: Automatically loads variables from .env and executes the pipeline.

cd /d "%~dp0"

:: Read .env file line by line and set variables (skipping comments and empty lines)
for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
    echo %%A | findstr /r "^#" >nul || (
        set "%%A=%%B"
    )
)

:: Execute the script
python main.py
