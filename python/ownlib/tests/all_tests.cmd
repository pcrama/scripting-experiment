@ECHO OFF
REM Run all tests: unit tests and tests embedded in documentation strings
REM
REM Assumes that
REM - python3.exe is on your PATH
REM - .\__init__.py imports all test cases
REM - ..\ownlib has no sub-directories (except tests\)
SETLOCAL ENABLEEXTENSIONS

CD "%~dp0..\.."

REM Unit tests
"%~dp0..\..\virtualenv\bin\python3.exe" -m unittest -v "%~dp0__init__.py"

REM Doctests
FOR /F %%F in ('dir /b "%~dp0..\*.py"') DO IF NOT %%F == __init__.py "%~dp0..\..\virtualenv\bin\python3.exe" -m doctest "%~dp0..\%%F"
