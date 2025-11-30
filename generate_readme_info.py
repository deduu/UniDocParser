import tomllib
import json
from pathlib import Path

def extract_project_info(pyproject_path="pyproject.toml", lock_path="poetry.lock"):
    project_info = {}

    with open(pyproject_path, "rb") as f:
        pyproject = tomllib.load(f)

    poetry_cfg = pyproject.get("tool", {}).get("poetry", {})

    # Core metadata
    project_info["name"] = poetry_cfg.get("name")
    project_info["version"] = poetry_cfg.get("version")
    project_info["description"] = poetry_cfg.get("description")
    project_info["authors"] = poetry_cfg.get("authors", [])
    project_info["license"] = poetry_cfg.get("license")
    project_info["readme"] = poetry_cfg.get("readme")

    # Dependencies
    project_info["dependencies"] = poetry_cfg.get("dependencies", {})
    project_info["dev_dependencies"] = (
        pyproject.get("tool", {})
        .get("poetry", {})
        .get("group", {})
        .get("dev", {})
        .get("dependencies", {})
    )

    # Python requirement lives in dependencies as "python"
    project_info["python_requires"] = project_info["dependencies"].get("python")

    # Lock file existence
    project_info["lock_file"] = Path(lock_path).exists()

    return project_info

if __name__ == "__main__":
    info = extract_project_info()
    print(json.dumps(info, indent=2))
