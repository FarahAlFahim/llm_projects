import json

# Define repo_path
repo_path = "/Users/fahim/Desktop/PhD/Projects/hive"

# Load the JSON file
file_path = "ground_truth/methods/Hive.json"

with open(file_path, "r") as f:
    data = json.load(f)

unique_paths = set()

# Extract relative file paths
for methods in data.values():
    for method in methods:
        parts = method.split("org", 1)
        if len(parts) > 1:
            relative_path = parts[0].rstrip(".").replace(".", "/")
            if "test" not in relative_path:
                unique_paths.add(relative_path)

# Construct codebase_dirs list
codebase_dirs = [f"{repo_path}/{path}" for path in sorted(unique_paths)]

# Print the final list
print("codebase_dirs =", codebase_dirs)
