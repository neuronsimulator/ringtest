# File: summarize_trace.py
import subprocess
import sys
import xml.etree.ElementTree as ET

def export_trace(trace_file):
    """Run xcrun xctrace export and return the XML output as a string."""
    cmd = [
        "xcrun", "xctrace", "export",
        "--input", trace_file,
        "--xpath", '//table[@schema="os-signpost-interval"]'
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running xcrun xctrace export: {e}")
        sys.exit(1)

def summarize_signposts(xml_data):
    """Parse XML data and summarize durations by signpost name, including min/max."""
    # Parse XML from string
    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError as e:
        print(f"Error parsing XML: {e}")
        return

    # Build reference tables for string and duration
    refs = {}
    for elem in root.iter():
        if elem.tag in ("string", "duration") and "id" in elem.attrib:
            refs[elem.attrib["id"]] = elem.text

    # Dictionary to store total durations, counts, min, and max
    summary = {}

    # Process each row
    for row in root.findall(".//row"):
        # Extract the name (either inline or via ref)
        name_elem = row.find(".//string")
        if name_elem is None:
            continue
        if "ref" in name_elem.attrib:
            name = refs.get(name_elem.attrib["ref"])
        else:
            name = name_elem.text
        if name is None:
            continue  # Skip unnamed intervals

        # Extract the duration (either inline or via ref)
        duration_elem = row.find(".//duration")
        if duration_elem is None or (duration_elem.text is None and "ref" not in duration_elem.attrib):
            continue
        if "ref" in duration_elem.attrib:
            duration_text = refs.get(duration_elem.attrib["ref"])
        else:
            duration_text = duration_elem.text
        if duration_text is None:
            continue
        duration = int(duration_text)  # Duration in nanoseconds

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
        print("Usage: python3 summarize_trace.py <trace_file>")
        sys.exit(1)

    trace_file = sys.argv[1]
    xml_data = export_trace(trace_file)
    summarize_signposts(xml_data)

if __name__ == "__main__":
    main()

