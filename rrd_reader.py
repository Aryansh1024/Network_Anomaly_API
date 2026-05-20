import subprocess
import pandas as pd

def fetch_rrd(file_path: str, ds_name: str, hours_back: int = 24) -> pd.DataFrame:
    """
    Reads data from an RRD file using the rrdtool command-line tool.
    Returns a pandas DataFrame with columns: timestamp, value.
    """
    
    # 1. Ask rrdtool for the EXACT last timestamp recorded in this specific file
    last_cmd = subprocess.run(
        ["rrdtool", "last", file_path],
        capture_output=True,
        text=True
    )
    
    if last_cmd.returncode != 0:
        raise RuntimeError(f"Failed to read RRD last update time: {last_cmd.stderr.strip()}")
        
    RRD_END = int(last_cmd.stdout.strip())
    RRD_START = RRD_END - (hours_back * 3600)

    # 2. Loop through standard CFs to find the one that works
    supported_cfs = ["AVERAGE", "MAX", "LAST", "MIN"]
    result = None
    
    for cf in supported_cfs:
        result = subprocess.run(
            [
                "rrdtool", "fetch", file_path, cf,
                "--start", str(RRD_START),
                "--end",   str(RRD_END),
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            break 

    if result.returncode != 0:
        raise RuntimeError(f"rrdtool failed on all CFs. Last error: {result.stderr.strip()}")

    # 3. Parse the text output
    lines = [l.strip() for l in result.stdout.strip().splitlines() if l.strip()]

    ds_names = lines[0].split()
    if ds_name not in ds_names:
        raise ValueError(f"'{ds_name}' not found in RRD. Available: {ds_names}")

    col_idx = ds_names.index(ds_name)
    rows = []

    for line in lines[1:]:
        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            ts = int(parts[0].rstrip(":"))
            raw = parts[1 + col_idx]
            if raw.lower() not in ("nan", "-nan"):
                rows.append({
                    "timestamp": pd.Timestamp(ts, unit="s"),
                    "value": float(raw),
                })
        except (ValueError, IndexError):
            continue

    df = pd.DataFrame(rows)
    return df