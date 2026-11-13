import os
p = r"H:\My Drive\Sahil Sangare\Practice\Daily-Market-Regime-Engine"
print("Exists:", os.path.exists(p))
if os.path.exists(p):
    print("Contents:", os.listdir(p))
