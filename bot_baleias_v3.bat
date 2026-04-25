@echo off
set PYTHONWARNINGS=ignore
set JOBLIB_START_METHOD=spawn
python bot_baleias_v3.py 2> nul
pause