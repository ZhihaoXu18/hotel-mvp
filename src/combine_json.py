import json
import math

base_path = "/Users/zhihaoxu/Desktop/Project:Code/hotel-mvp/data_out/"

files = {
    "business_summary": "business_summary.json",
    "optimization_results": "optimization_results.json",
    "scenario_results": "scenario_results.json",
    "optimization_ab_results": "optimization_ab_results.json",
    "scenario_ab_results": "scenario_ab_results.json"
}

def clean_json(obj):
    if isinstance(obj, dict):
        return {k: clean_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_json(v) for v in obj]
    elif isinstance(obj, float) and math.isnan(obj):
        return None
    else:
        return obj

results = {}

for key, filename in files.items():
    with open(base_path + filename, "r", encoding="utf-8") as f:
        results[key] = json.load(f)

results = clean_json(results)

output_path = base_path + "results.json"

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=4, ensure_ascii=False)

print("Combined results JSON saved:")
print(output_path)