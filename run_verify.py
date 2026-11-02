import subprocess
python_exe = r"H:\My Drive\Sahil Sangare\Practice\Daily-Market-Regime-Engine\.venv\Scripts\python.exe"
print("Running via subprocess...")
res = subprocess.run([python_exe, "verify_env.py"], capture_output=True, text=True)
print("Exit code:", res.returncode)
print("STDOUT:", res.stdout)
print("STDERR:", res.stderr)
