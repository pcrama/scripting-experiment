@ECHO OFF
REM Wrapper for python scripts to activate virtual environment (i.e. isolated
REM Python dependencies, see https://docs.python.org/3/library/venv.html)
REM
REM See individual python scripts for usage information and command line help,
REM this script only serves to enable the script-specific python dependencies
REM and hand over the command line arguments to the script.
REM
REM Unfortunately, this script can't handle empty command line parameters.
REM
REM Usage:
REM If you have 'yourscript.py', create wrappers for it that will use this
REM wrapper when in CMD.exe to install the script's dependencies if needed and
REM call the script such that it can find those libraries and a bash wrapper
REM that will call yourscript.py such that it can find those libraries, too
REM (auto-installing from the bash wrapper is not implemented):
REM
REM     WithVirtualEnv.cmd CreateWrapper yourscript.py
REM
REM This will create 2 wrappers: a CMD.exe wrapper yourscript.cmd
REM
REM     @REM Wrapper for yourscript.py to activate virtual environment (i.e. isolated Python dependencies)
REM     @REM
REM     @REM See yourscript.py for usage information and command line help
REM     @REM
REM     @REM Unfortunately, this wrapper script is unable to pass certain special
REM     @REM characters (like `<', `&' or `>') properly.  Please be kind
REM     @CALL "%~dp0WithVirtualEnv.cmd" "%~f0" %*
REM
REM and a git/msys bash wrapper yourscript.sh
REM
REM     #!/bin/sh
REM     # Wrapper for yourscript.py to activate virtual environment (i.e. isolated Python dependencies)
REM     # See yourscript.py for usage information and command line help
REM     activation='<path to virtualenv>/bin/activate'
REM     test -r "$activation" && source "$activation" && exec python3 "$(dirname "$0")/yourscript.py" "$@"
REM     echo 'Please install the virtual environment in <path to virtualenv> and the required libraries yourself'
REM     exit 1

SETLOCAL EnableExtensions
SETLOCAL EnableDelayedExpansion

SET venvname=virtualenv
SET venvdir=%~dp0%venvname%

IF /I [%1] == [CreateWrapper] GOTO createwrapper
GOTO runscript

:createwrapper
IF [%2] == [] (
    ECHO %~n0 CreateWrapper ^<script.py^>^: missing argument
    EXIT /B
)

SET wrappee=%~nx2
SET header=Wrapper for %wrappee% to activate virtual environment (i.e. isolated Python dependencies)
SET seealso=See %wrappee% for usage information and command line help

REM Create CMD.exe wrapper
REM Keep everything but the file extension and add `.cmd'
SET dest=%~dpn2.cmd
ECHO @REM %header%>                                                              "%dest%"
ECHO @REM>>                                                                      "%dest%"
ECHO @REM %seealso%>>                                                            "%dest%"
ECHO @REM>>                                                                      "%dest%"
ECHO @REM Unfortunately, this wrapper script is unable to pass certain special>> "%dest%"
ECHO @REM characters (like `^<^', `^&^' or `^>^') properly.  Please be kind>>    "%dest%"
ECHO @CALL ^"%%^~dp0%~nx0^" ^"%%^~f0^" %%^*>>                                    "%dest%"

REM Create bash wrapper
REM Keep everything but the file extension and add `.sh'
SET dest=%~dpn2.sh
REM Please excuse the awful quoting... I tried many simpler ways to get a
REM proper shebang in the generated script and failed.
SET "shebang=#^!"
ECHO !shebang!/bin/sh>                                                                                          "%dest%"
ECHO # %header%>>                                                                                               "%dest%"
ECHO # %seealso%>>                                                                                              "%dest%"
ECHO activation=^'%venvdir%/bin/activate^'>>                                                                    "%dest%"
ECHO test -r "$activation" ^&^& source "$activation" ^&^& exec python3 ^"$(dirname ^"$0^")/%wrappee%^" ^"$@^">> "%dest%"
ECHO echo ^'Please install the virtual environment in %venvdir% and the required libraries yourself^'>>         "%dest%"
ECHO exit ^1>>                                                                                                  "%dest%"

EXIT /B

REM ----------------------------------------------------------------
:runscript
SET activationscript=%venvdir%\bin\Activate.ps1
IF NOT EXIST "%activationscript%" (
    ECHO One-time python setup: [1] Create virtual environment
    python3 -m venv "!venvdir!"
    ECHO [2] Intall local libraries
    SET requirements=%~dp0python-scripts-requirements.txt
    REM No full path to `pip3' because the activation script put it on the PATH already.
    powershell.exe -ExecutionPolicy RemoteSigned -Command "& { & '!activationscript!'; pip3 install -r '!requirements!' }"
)

REM Initialize accumulator to collect all command line parameters.
SET arguments=

FOR %%A IN (%*) DO (
    IF DEFINED pythonscript (
       REM 2nd, 3rd, etc parameters must be accumulated
       SET arguments=!arguments! '%%A'
    ) ELSE (
        REM First parameter is script name, replace `.cmd' suffix with `.py':
        SET pythonscript=%~dpn1.py
    )
)

REM Quoting is intentional to avoid problems with `&' and `;'.  No full path
REM to python needed because the activation script put it on the PATH already.
SET "powershellcommand=& '%activationscript%'; python3 '%pythonscript%' %arguments%"
powershell.exe -ExecutionPolicy RemoteSigned -Command "& { %powershellcommand%; exit $LastExitCode }"
