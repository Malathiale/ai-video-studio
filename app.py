import os
import shutil
import time
from pathlib import Path
from urllib.parse import urlparse

import streamlit as st
from dotenv import load_dotenv
from gradio_client import Client, handle_file

# ---------------------------------------------------------
# AI VIDEO STUDIO - Wan 2.2 Image-to-Video
# ---------------------------------------------------------

APP_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = APP_DIR / "generated_videos"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(APP_DIR / ".env")
HF_TOKEN = os.getenv("HF_TOKEN", "").strip()

WAN_SPACE = "JCisHERE/wan2-2-i2v-v3"

DEFAULT_NEGATIVE_PROMPT = (
    "blurry, low resolution, flicker, jitter, distorted face, "
    "changing identity, extra eyes, malformed hands, warped anatomy, "
    "duplicate character, unstable background, text, watermark"
)


def connect_wan():
    """Connect to the public Wan 2.2 Hugging Face Space."""
    return Client(WAN_SPACE)

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
        # Gradio file/video outputs commonly use these keys.
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


def save_video(result):
    """Copy the generated video into this app's generated_videos folder."""
    video_source = find_video_file(result)
    if not video_source:
        raise RuntimeError(
            "Wan 2.2 finished, but I could not locate the video file "
            "in the returned result. Please try again."
        )

    filename = f"wan_video_{int(time.time())}.mp4"
    destination = OUTPUT_DIR / filename

    if isinstance(video_source, Path):
        shutil.copy2(video_source, destination)
    else:
        # Some Gradio versions return a downloadable URL.
        import requests

        response = requests.get(video_source, timeout=180)
        response.raise_for_status()
        destination.write_bytes(response.content)

    if destination.stat().st_size == 0:
        destination.unlink(missing_ok=True)
        raise RuntimeError("The downloaded video file is empty.")

    return destination


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
    """Generate a video using the Wan 2.2 Space's /generate_video API."""
    client = connect_wan()
    image_input = handle_file(str(image_path))

    result = client.predict(
        image_input,                 # input_image
        image_input,                 # last_image
        prompt,                      # prompt
        int(steps),                  # steps
        negative_prompt,             # negative_prompt
        float(duration),             # duration_seconds
        1,                           # guidance_scale
        1,                           # guidance_scale_2
        int(seed),                   # seed
        bool(randomize_seed),        # randomize_seed
        int(quality),                # quality (export quality)
        "UniPCMultistep",             # scheduler
        3.0,                         # flow_shift
        16,                          # frame_multiplier
        True,                        # safe_mode
        [],                          # lora_groups
        False,                       # auto_lora_enabled
        True,                        # video_component
        api_name="/generate_video",
    )

    return save_video(result)


# ---------------------------------------------------------
# Streamlit user interface
# ---------------------------------------------------------

st.set_page_config(
    page_title="AI Video Studio",
    page_icon="🎬",
    layout="centered",
)

st.title("🎬 AI Video Studio")
st.write("Create a short animated video from an image using Wan 2.2.")

if not HF_TOKEN:
    st.warning(
        "HF_TOKEN was not found. Add your Hugging Face token to the "
        ".env file in the same folder as app.py. Do not paste your token "
        "into this chat or share it with anyone."
    )

uploaded_image = st.file_uploader(
    "Upload your starting image",
    type=["png", "jpg", "jpeg", "webp"],
)

if uploaded_image:
    st.image(uploaded_image, caption="Starting image", use_container_width=True)
st.subheader("Prompt")

st.caption("Example prompt — for reference only:")

st.write(
    "Anime character slowly turns their head to a slight "
    "three-quarter view. Hair moves gently in a light breeze. "
    "Smooth natural motion. Camera stays steady."
)

prompt = st.text_area(
    "Your prompt",
    value="",
    placeholder="Describe the movement you want...",
    height=150,
)
st.subheader("Negative Prompt")

st.caption("Example negative prompt — for reference only:")
st.write(DEFAULT_NEGATIVE_PROMPT)

negative_prompt = st.text_area(
    "Your negative prompt",
    value="",
    placeholder="Write what you want to avoid...",
    height=90,
)

col1, col2 = st.columns(2)

with col1:
    duration = st.selectbox(
        "Video duration (seconds)",
        options=[3, 4, 5],
        index=0,
    )

    steps = st.slider(
        "Generation steps",
        min_value=4,
        max_value=8,
        value=8,
    )

with col2:
    quality = st.slider(
        "Export quality",
        min_value=1,
        max_value=10,
        value=9,
    )

    seed = st.number_input(
        "Seed",
        min_value=0,
        max_value=2_147_483_647,
        value=42,
        step=1,
    )

randomize_seed = st.checkbox("Use a random seed", value=True)

st.caption(
    "Tip: use a clear, high-resolution image and describe one simple movement."
)

if st.button("Generate video", type="primary", use_container_width=True):
    if uploaded_image is None:
        st.error("Please upload an image first.")
    elif not prompt.strip():
        st.error("Please enter a video prompt.")
    elif not HF_TOKEN:
        st.error("Please add HF_TOKEN to your .env file, then restart the app.")
    else:
        temporary_image = APP_DIR / "uploaded_start_image"
        suffix = Path(uploaded_image.name).suffix or ".png"
        temporary_image = temporary_image.with_suffix(suffix)
        temporary_image.write_bytes(uploaded_image.getvalue())

        try:
            with st.spinner(
                "Generating your video with Wan 2.2. This may take several minutes..."
            ):
                generated_video = generate_with_wan(
                    image_path=temporary_image,
                    prompt=prompt.strip(),
                    negative_prompt=negative_prompt.strip(),
                    duration=duration,
                    steps=steps,
                    quality=quality,
                    seed=seed,
                    randomize_seed=randomize_seed,
                )

            st.success("Your video is ready!")
            st.video(str(generated_video))
            st.write(f"Saved to: `{generated_video}`")

            with open(generated_video, "rb") as video_file:
                st.download_button(
                    "Download video",
                    data=video_file,
                    file_name=generated_video.name,
                    mime="video/mp4",
                    use_container_width=True,
                )

        except Exception as error:
            st.error("Video generation failed.")
            st.exception(error)

        finally:
            temporary_image.unlink(missing_ok=True)

st.divider()
st.caption("Generated videos are saved in the generated_videos folder.")
