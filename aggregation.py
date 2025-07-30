import os
import xml.etree.ElementTree as ET
import json
import re
import csv

def parse_lizard_report(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    xml_start = content.find("<?xml version")
    if xml_start != -1:
        content = content[xml_start:]

    root = ET.fromstring(content)

    test_metrics = {"Nr": [], "NCSS": [], "CCN": []}
    non_test_metrics = {"Nr": [], "NCSS": [], "CCN": []}

    for item in root.findall(".//item"):
        name = item.get("name")
        values = [int(val.text) for val in item.findall("value")[:3]]

        if name and values:
            if re.search(r"\btests?\b", name):
                test_metrics["Nr"].append(values[0])
                test_metrics["NCSS"].append(values[1])
                test_metrics["CCN"].append(values[2])
            else:
                non_test_metrics["Nr"].append(values[0])
                non_test_metrics["NCSS"].append(values[1])
                non_test_metrics["CCN"].append(values[2])

    def compute_average(metrics):
        return {key: sum(vals) / len(vals) if vals else 0 for key, vals in metrics.items()}

    return {
        "test": compute_average(test_metrics),
        "non_test": compute_average(non_test_metrics)
    }

def parse_halstead(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    test_values = {}
    non_test_values = {}

    for file_path, metrics in data.items():
        is_test = "/tests/" in file_path
        category = test_values if is_test else non_test_values

        # Check if the metrics contain the expected structure
        if isinstance(metrics, dict):
            # If "total" key exists, use it; otherwise, use the metrics directly
            metrics_data = metrics.get("total", metrics)

            for metric, value in metrics_data.items():
                if metric not in category:
                    category[metric] = []
                # Convert value to float (or int) if it's a string
                try:
                    value = float(value)  # Convert to float to handle both integers and decimals
                except (ValueError, TypeError):
                    continue  # Skip if conversion fails
                category[metric].append(value)

    def compute_avg(values_dict):
        return {
            metric: sum(values) / len(values) if values else 0
            for metric, values in values_dict.items()
        }

    return {
        "test": compute_avg(test_values),
        "non_test": compute_avg(non_test_values)
    }

def parse_raw_metrics(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    test_values = {}
    non_test_values = {}

    for file_path, metrics in data.items():
        is_test = "/tests/" in file_path
        category = test_values if is_test else non_test_values

        for metric, value in metrics.items():
            if metric not in category:
                category[metric] = []
            category[metric].append(value)

    def compute_avg(values_dict):
        return {metric: sum(values) / len(values) if values else 0 for metric, values in values_dict.items()}

    return {
        "test": compute_avg(test_values),
        "non_test": compute_avg(non_test_values)
    }

def parse_complexity(file_path):
    with open(file_path, "r") as f:
        data = json.load(f)

    test_methods, test_classes = [], []
    non_test_methods, non_test_classes = [], []

    for filename, elements in data.items():
        is_test_file = "/tests/" in filename

  
        if isinstance(elements, list):
            for element in elements:
                if isinstance(element, dict) and "type" in element and "complexity" in element:
                    if element["type"] in ["function", "method"]:
                        if is_test_file:
                            test_methods.append(element["complexity"])
                        else:
                            non_test_methods.append(element["complexity"])
                    elif element["type"] == "class":
                        if is_test_file:
                            test_classes.append(element["complexity"])
                        else:
                            non_test_classes.append(element["complexity"])

    def compute_metrics(methods, classes):
        return {
            "average_method_complexity": sum(methods) / len(methods) if methods else 0,
            "average_class_complexity": sum(classes) / len(classes) if classes else 0,
            "total_methods": len(methods),
            "total_classes": len(classes),
            "max_method_complexity": max(methods) if methods else 0,
            "min_method_complexity": min(methods) if methods else 0,
        }

    return {
        "test": compute_metrics(test_methods, test_classes),
        "non_test": compute_metrics(non_test_methods, non_test_classes)
    }

def main():
    outer_folder = "/Users/promachowdhury/sustainability_mlops/projects-code-metrics"
    files = ["complexity.json", "lizard_report.xml", "halstead.json", "raw_metrics.json"]

    # Automatically find inner folders
    inner_folders = [f.name for f in os.scandir(outer_folder) if f.is_dir()]

    all_data = {}

    for inner_folder in inner_folders:
        folder_path = os.path.join(outer_folder, inner_folder)
        folder_data = {}

        for file in files:
            file_path = os.path.join(folder_path, file)
            if not os.path.exists(file_path):
                continue

            if file == "lizard_report.xml":
                parsed_data = parse_lizard_report(file_path)
            elif file == "halstead.json":
                parsed_data = parse_halstead(file_path)
            elif file == "raw_metrics.json":
                parsed_data = parse_raw_metrics(file_path)
            elif file == "complexity.json":
                parsed_data = parse_complexity(file_path)

            for category, metrics in parsed_data.items():
                for metric, value in metrics.items():
                    folder_data[f"{file}_{category}_{metric}"] = value

        all_data[inner_folder] = folder_data

    fieldnames = set()
    for folder_data in all_data.values():
        fieldnames.update(folder_data.keys())

    # Write to CSV
    csv_file = "metrics_summary.csv"
    with open(csv_file, mode="w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["folder"] + sorted(fieldnames))
        writer.writeheader()

        for folder_name, folder_data in all_data.items():
            row = {"folder": folder_name}
            row.update(folder_data)
            writer.writerow(row)

    print(f"Metrics summary written to {csv_file}")

if __name__ == "__main__":
    main()