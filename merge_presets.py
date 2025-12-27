import yaml
from pathlib import Path

PRESETS_DIR = Path(".historic_files/presets")          # adjust if needed
OUTPUT_FILE = Path("config.yaml")

BASE_CONFIG = {
    "version": 1,
    "defaults": {
        "obs": {"auto_start": True},
        "prompts": {"confirm": True},
    },
    "presets": {},
}

def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def main():
    if not PRESETS_DIR.exists():
        raise SystemExit(f"Preset dir not found: {PRESETS_DIR}")

    config = BASE_CONFIG.copy()
    presets = {}

    for file in sorted(PRESETS_DIR.glob("*.yaml")):
        data = load_yaml(file)

        key = data["game"]["key"]
        presets[key] = {
            "game": {
                "name": data["game"]["name"],
                "category": data["game"]["category"],
            },
            "defaults": data.get("defaults", {}),
            "tags": data.get("tags", []),
        }

    config["presets"] = presets

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        yaml.safe_dump(
            config,
            f,
            sort_keys=False,
            allow_unicode=True,
        )

    print(f"✓ Merged {len(presets)} presets into {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
