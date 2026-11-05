
import os
import re
import shutil
from pathlib import Path
from rapidfuzz import fuzz, process

# ==========================================
# CONFIGURATION
# ==========================================

ROOT_FOLDER = Path(__file__).resolve().parent

OUTPUT_FOLDER = ROOT_FOLDER / "MisterMarquee"
MISSING_FILE = ROOT_FOLDER / "missing.txt"
GAME_LIST_FILE = ROOT_FOLDER / "games.txt"

MATCH_THRESHOLD = 80
MAX_MATCHES = 10

IMAGE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".bmp",
    ".gif", ".webp", ".tif", ".tiff"
}


# ==========================================
# NORMALISE GAME AND IMAGE NAMES
# ==========================================

def clean_name(name):

    name = name.lower()

    name = re.sub(r'\([^)]*\)', ' ', name)
    name = re.sub(r'\[[^]]*\]', ' ', name)

    name = re.sub(r'[^a-z0-9]', ' ', name)
    name = re.sub(r'\s+', ' ', name)

    return name.strip()


# ==========================================
# SAFE WINDOWS FILENAMES
# ==========================================

def safe_filename(name):

    name = re.sub(r'[<>:"/\\|?*]', '', name)

    name = name.strip().rstrip('.')

    return name if name else "Unknown Game"


# ==========================================
# ADVANCED MATCHING
# ==========================================

def match_score(game_name, image_name, **kwargs):

    game = game_name.replace(" ", "")
    image = image_name.replace(" ", "")

    scores = [
        fuzz.WRatio(game_name, image_name),
        fuzz.ratio(game, image),
        fuzz.partial_ratio(game, image),
        fuzz.token_set_ratio(game_name, image_name)
    ]

    # Abbreviation matching
    # Example: Afterburner -> aburner

    if len(game) > len(image):

        if game.startswith(image[0]) and image[1:] in game[1:]:
            scores.append(95)

    elif len(image) > len(game):

        if image.startswith(game[0]) and game[1:] in image[1:]:
            scores.append(95)

    # Contained names

    if len(game) >= 5 and game in image:
        scores.append(90)

    if len(image) >= 5 and image in game:
        scores.append(90)

    return max(scores)


# ==========================================
# READ GAME LIST
# ==========================================

def read_games():

    if not GAME_LIST_FILE.exists():
        raise FileNotFoundError(
            f"Cannot find game list: {GAME_LIST_FILE}"
        )

    content = GAME_LIST_FILE.read_text(
        encoding="utf-8-sig"
    )

    games = re.findall(r'"([^"]+)"', content)

    return list(dict.fromkeys(games))


# ==========================================
# FIND ALL IMAGE FILES
# ==========================================

def find_images():

    images = []

    for folder, dirs, files in os.walk(ROOT_FOLDER):

        # Exclude output folder

        dirs[:] = [
            d for d in dirs
            if (Path(folder) / d).resolve()
            != OUTPUT_FOLDER.resolve()
        ]

        for filename in files:

            image_path = Path(folder) / filename

            if image_path.suffix.lower() in IMAGE_EXTENSIONS:
                images.append(image_path.resolve())

    return images


# ==========================================
# MAIN PROCESSING
# ==========================================

def main():

    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

    games = read_games()
    images = find_images()

    # Create cleaned image names

    image_names = [
        clean_name(image.stem)
        for image in images
    ]

    print()
    print("==========================================")
    print("       MISTER MARQUEE IMAGE FINDER")
    print("==========================================")
    print(f"Games found:  {len(games)}")
    print(f"Images found: {len(images)}")
    print("------------------------------------------")

    missing = []
    copied = 0
    used_images = set()

    # ======================================
    # PROCESS EACH GAME
    # ======================================

    for game in games:

        cleaned_game = clean_name(game)

        matches = process.extract(
            cleaned_game,
            image_names,
            scorer=match_score,
            limit=MAX_MATCHES,
            score_cutoff=MATCH_THRESHOLD
        )

        best_match = None

        # Find highest scoring unused image

        for match_name, score, image_index in matches:

            image_path = images[image_index]

            if image_path not in used_images:

                best_match = (image_path, score)
                break

        # ==================================
        # COPY AND RENAME MATCHING IMAGE
        # ==================================

        if best_match is not None:

            image_path, score = best_match

            # Use game list name for destination filename

            new_filename = (
                safe_filename(game)
                + image_path.suffix.lower()
            )

            destination = OUTPUT_FOLDER / new_filename

            # Prevent overwriting existing files

            counter = 1

            while destination.exists():

                new_filename = (
                    f"{safe_filename(game)}_{counter}"
                    f"{image_path.suffix.lower()}"
                )

                destination = OUTPUT_FOLDER / new_filename

                counter += 1

            try:

                # Check source exists

                if not image_path.is_file():
                    raise FileNotFoundError(
                        f"Source image does not exist: {image_path}"
                    )

                # Copy image using new filename

                shutil.copy2(image_path, destination)

                used_images.add(image_path)
                copied += 1

                print(
                    f"[FOUND {score:5.1f}%] "
                    f"{game} -> {destination.name}"
                )

            except OSError as error:

                print(f"[ERROR] {game}: {error}")
                missing.append(game)

        else:

            missing.append(game)

            print(f"[MISSING] {game}")

    # ======================================
    # SAVE MISSING GAMES
    # ======================================

    MISSING_FILE.write_text(
        "\n".join(missing),
        encoding="utf-8"
    )

    # ======================================
    # FINAL REPORT
    # ======================================

    print()
    print("==========================================")
    print("              RESULTS")
    print("==========================================")

    print(f"Games processed: {len(games)}")
    print(f"Images copied:   {copied}")
    print(f"Games missing:   {len(missing)}")

    print("------------------------------------------")
    print(f"Images folder: {OUTPUT_FOLDER}")
    print(f"Missing list:  {MISSING_FILE}")

    print("==========================================")
    print("              FINISHED!")
    print("==========================================")


# ==========================================
# START PROGRAM
# ==========================================

if __name__ == "__main__":
    main()
