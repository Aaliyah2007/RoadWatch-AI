from pathlib import Path
import random
import shutil
import yaml

# ============================================================
# SETTINGS
# ============================================================

SOURCE = Path("dataset")
OUTPUT = Path("road_damage_small")

TRAIN_LIMIT = 6000
VALID_LIMIT = 500

random.seed(42)

# Original RDD2022 classes:
# 0 = Alligator Crack
# 1 = Longitudinal Crack
# 2 = Pothole
# 3 = Transverse Crack
#
# New RoadWatch AI classes:
# 0 = crack
# 1 = pothole

CLASS_MAP = {
    0: 0,  # Alligator Crack -> crack
    1: 0,  # Longitudinal Crack -> crack
    2: 1,  # Pothole -> pothole
    3: 0,  # Transverse Crack -> crack
}


# ============================================================
# PREPARE ONE SPLIT
# ============================================================

def prepare_split(split_name, limit):

    source_images = SOURCE / split_name / "images"
    source_labels = SOURCE / split_name / "labels"

    output_images = OUTPUT / split_name / "images"
    output_labels = OUTPUT / split_name / "labels"

    output_images.mkdir(parents=True, exist_ok=True)
    output_labels.mkdir(parents=True, exist_ok=True)

    image_files = [
        p for p in source_images.iterdir()
        if p.is_file()
        and p.suffix.lower() in [".jpg", ".jpeg", ".png", ".bmp", ".webp"]
        and (source_labels / f"{p.stem}.txt").exists()
    ]

    random.shuffle(image_files)

    selected = image_files[:min(limit, len(image_files))]

    print(f"\n{split_name.upper()}")
    print(f"Available images: {len(image_files)}")
    print(f"Selected images:  {len(selected)}")

    copied = 0

    for image_path in selected:

        label_path = source_labels / f"{image_path.stem}.txt"

        new_lines = []

        with open(label_path, "r", encoding="utf-8") as file:
            lines = file.readlines()

        for line in lines:

            parts = line.strip().split()

            if len(parts) != 5:
                continue

            try:
                old_class = int(parts[0])
            except ValueError:
                continue

            if old_class not in CLASS_MAP:
                continue

            new_class = CLASS_MAP[old_class]

            new_line = " ".join(
                [str(new_class)] + parts[1:]
            )

            new_lines.append(new_line)

        # Skip images that contain no valid road-damage labels
        if not new_lines:
            continue

        shutil.copy2(
            image_path,
            output_images / image_path.name
        )

        with open(
            output_labels / label_path.name,
            "w",
            encoding="utf-8"
        ) as file:

            file.write("\n".join(new_lines) + "\n")

        copied += 1

    print(f"Successfully prepared: {copied}")


# ============================================================
# CREATE DATASET
# ============================================================

if OUTPUT.exists():
    print(f"\nRemoving previous output folder: {OUTPUT}")
    shutil.rmtree(OUTPUT)


print("Preparing RoadWatch AI dataset...")
print("This may take several minutes.\n")


prepare_split("train", TRAIN_LIMIT)
prepare_split("valid", VALID_LIMIT)


# ============================================================
# CREATE data.yaml
# ============================================================

yaml_content = {
    "train": "../road_damage_small/train/images",
    "val": "../road_damage_small/valid/images",
    "nc": 2,
    "names": [
        "crack",
        "pothole"
    ]
}

with open(
    OUTPUT / "data.yaml",
    "w",
    encoding="utf-8"
) as file:

    yaml.dump(
        yaml_content,
        file,
        sort_keys=False
    )


# ============================================================
# FINISHED
# ============================================================

print("\n" + "=" * 55)
print("DATASET PREPARATION COMPLETE")
print("=" * 55)

print(f"\nOutput folder:")
print(OUTPUT.resolve())

print("\nClasses:")
print("0 = crack")
print("1 = pothole")

print("\nNext step:")
print("Train the YOLOv8 model using road_damage_small/data.yaml")