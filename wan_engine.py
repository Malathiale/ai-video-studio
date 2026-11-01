
import shutil
import time
from pathlib import Path

import requests
from gradio_client import Client, handle_file


# --------------------------------------------------
# PROJECT CONFIGURATION
# --------------------------------------------------

APP_DIR = Path(__file__).resolve().parent

OUTPUT_DIR = APP_DIR / "generated_videos"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# New working Wan 2.2 14B Space
WAN_SPACE = "Upsampler/wan-2-2-14b-image-to-video"

DEFAULT_NEGATIVE_PROMPT = (
    "blurry, low resolution, flicker, jitter, distorted face, "
    "changing identity, extra eyes, malformed hands, warped anatomy, "
    "duplicate character, unstable background, text, watermark"
)


# --------------------------------------------------
# CONNECT TO HUGGING FACE
# --------------------------------------------------

def connect_wan():
    """Connect to the Wan 2.2 Hugging Face Space."""
    return Client(WAN_SPACE)


# --------------------------------------------------
# FIND GENERATED VIDEO
# --------------------------------------------------

def find_video_file(value):
    """Find a video filepath inside the Gradio result."""

    if isinstance(value, (str, Path)):
        text_value = str(value)

        if text_value.startswith(("http://", "https://")):
            return text_value

        candidate = Path(text_value)

        if candidate.is_file():
            return candidate

        return None

    if isinstance(value, dict):
        for key in ("video", "path", "name", "url", "value"):
            if key in value:
                found = find_video_file(value[key])

                if found:
                    return found

        for nested in value.values():
            found = find_video_file(nested)

            if found:
                return found

    if isinstance(value, (list, tuple)):
        for item in value:
            found = find_video_file(item)

            if found:
                return found

    return None


# --------------------------------------------------
# SAVE GENERATED VIDEO
# --------------------------------------------------

def save_video(result):
    """Save the generated MP4 inside generated_videos."""

    video_source = find_video_file(result)

    if not video_source:
        raise RuntimeError(
            "Wan 2.2 finished, but the generated video "
            "could not be located."
        )

    filename = f"wan_video_{int(time.time() * 1000)}.mp4"

    destination = OUTPUT_DIR / filename

    if isinstance(video_source, Path):
        shutil.copy2(video_source, destination)

    else:
        response = requests.get(
            video_source,
            timeout=180
        )

        response.raise_for_status()

        destination.write_bytes(response.content)

    if not destination.exists() or destination.stat().st_size == 0:
        destination.unlink(missing_ok=True)

        raise RuntimeError(
            "The downloaded video file is empty."
        )

    return destination


# --------------------------------------------------
# GENERATE VIDEO WITH WAN 2.2
# --------------------------------------------------

def generate_with_wan(
    image_path,
    prompt,
    negative_prompt,
    duration,
    steps,
    quality,
    seed,
    randomize_seed,
):
    """
    Generate a video using the Upsampler Wan 2.2 14B Space.

    The function signature is preserved for compatibility
    with the existing main.py.
    """

    client = connect_wan()

    image_input = handle_file(str(image_path))

    # The Space returns:
    # (generated_video, seed)

    result = client.predict(
        input_image=image_input,
        prompt=str(prompt),
        steps=float(steps),
        negative_prompt=str(
            negative_prompt or DEFAULT_NEGATIVE_PROMPT
        ),
        duration_seconds=float(duration),
        guidance_scale=1,
        guidance_scale_2=1,
        seed=int(seed),
        randomize_seed=bool(randomize_seed),
        end_image=None,
        api_name="/generate_video",
    )

    # Save the generated video locally.
    return save_video(result)
