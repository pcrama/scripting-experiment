@REM Wrapper for git_show_head.py to activate virtual environment (i.e. isolated Python dependencies)
@REM
@REM See git_show_head.py for usage information and command line help
@REM
@REM Unfortunately, this wrapper script is unable to pass certain special
@REM characters (like `<', `&' or `>') properly.  Please be kind
@CALL "%~dp0WithVirtualEnv.cmd" "%~f0" %*
