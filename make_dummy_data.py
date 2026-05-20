import subprocess
import time
import random
import os

# Ensure the data folder exists
os.makedirs("data", exist_ok=True)

# We will overwrite the broken file with a working one
file_path = "data/192_168_1_186_mem_free_559.rrd" 
now = int(time.time())
start_time = now - (24 * 3600) # Exactly 24 hours ago

print("Creating a structurally perfect RRD file...")
# 1. Create the database architecture (5-minute steps, AVERAGE RRA)
subprocess.run([
    "rrdtool", "create", file_path,
    "--start", str(start_time - 10),
    "--step", "300", 
    "DS:mem_free:GAUGE:600:0:1000000000",
    "RRA:AVERAGE:0.5:1:300"
])

print("Filling it with 24 hours of simulated network data...")
# 2. Feed it data point by data point
for t in range(start_time, now, 300):
    # Base memory usage around 500MB
    val = 500000000 + random.randint(-10000000, 10000000)
    
    # 5% chance to simulate a massive memory leak/spike for your detector
    if random.random() < 0.05: 
        val += 300000000 
        
    subprocess.run(["rrdtool", "update", file_path, f"{t}:{val}"])

print(f"Success! {file_path} is ready for the API.")