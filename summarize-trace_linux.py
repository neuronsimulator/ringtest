# File: summarize_trace.py
import subprocess
import sys
import xml.etree.ElementTree as ET

def summarize_signposts(data):
    """Parse data and summarize durations by signpost name, including min/max."""

    summary = {}

    # Process each row
    for row in data:
        d = row.split()
        # Extract the name (either inline or via ref)
        name = d[0]
        duration = int(d[1])

        # Aggregate in summary
        if name in summary:
            summary[name]["total_duration"] += duration
            summary[name]["count"] += 1
            summary[name]["min_duration"] = min(summary[name]["min_duration"], duration)
            summary[name]["max_duration"] = max(summary[name]["max_duration"], duration)
        else:
            summary[name] = {
                "total_duration": duration,
                "count": 1,
                "min_duration": duration,
                "max_duration": duration
            }

    # Print the summary
    if not summary:
        print("No named signpost intervals found in the trace.")
        return

    print("Summary of Signpost Intervals:")
    print(f"{'Name':<20} {'Total Dur (s)':<15} {'Count':<10} {'Min Dur (us)':<15} {'Max Dur (us)':<15}")
    print("-" * 79)
    for name, data in sorted(summary.items()):
        total_duration_s = data["total_duration"] / 1_000_000_000  # Convert ns to seconds
        count = data["count"]
        min_duration_us = data["min_duration"] / 1_000  # Convert ns to B5s
        max_duration_us = data["max_duration"] / 1_000  # Convert ns to B5s
        print(f"{name:<20} {total_duration_s:<15.6f} {count:<10} {min_duration_us:<15.2f} {max_duration_us:<15.2f}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 summarize_trace_linux.py <trace_file>")
        sys.exit(1)

    trace_file = sys.argv[-1]
    print(trace_file)
    f = open(trace_file, "r")
    print(f)
    data = f.readlines()
    f.close()
    summarize_signposts(data)

if __name__ == "__main__":
    main()

