import os
p = r"H:\My Drive\Sahil Sangare\Practice\Daily-Market-Regime-Engine"
print("Git status:")
os.system(f"cd /d \"{p}\" && git status")
print("\nDirectory tree of src and data:")
for root, dirs, files in os.walk(p):
    # filter out .git and .venv
    dirs[:] = [d for d in dirs if d not in ['.git', '.venv', '__pycache__']]
    rel = os.path.relpath(root, p)
    print(f"[{rel}]")
    for f in files:
        print(f"  {f}")
