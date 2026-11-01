
from dotenv import load_dotenv
load_dotenv()



import shutil
import uuid
import threading
import webbrowser
import time

from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from wan_engine import (
    APP_DIR,
    OUTPUT_DIR,
    DEFAULT_NEGATIVE_PROMPT,
    generate_with_wan,
)


# --------------------------------------------------
# APP CONFIGURATION
# --------------------------------------------------

app = FastAPI(title="AI Video Studio")

UPLOAD_DIR = APP_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

app.mount(
    "/static",
    StaticFiles(directory=APP_DIR / "static"),
    name="static"
)

templates = Jinja2Templates(
    directory=APP_DIR / "templates"
)


# --------------------------------------------------
# HOME PAGE
# --------------------------------------------------

@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "default_negative_prompt": DEFAULT_NEGATIVE_PROMPT
        }
    )


# --------------------------------------------------
# VIDEO GENERATION
# --------------------------------------------------

@app.post("/generate")
async def generate_video(
    image: UploadFile = File(...),
    prompt: str = Form(...),
    negative_prompt: str = Form(""),
    duration: int = Form(3),
    steps: int = Form(8),
    quality: int = Form(9),
    seed: int = Form(42),
    randomize_seed: bool = Form(True),
):

    if not prompt.strip():
        raise HTTPException(
            status_code=400,
            detail="Please enter a video prompt."
        )

    allowed_extensions = {
        ".png",
        ".jpg",
        ".jpeg",
        ".webp"
    }

    extension = Path(image.filename or "").suffix.lower()

    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Please upload a PNG, JPG, JPEG, or WEBP image."
        )

    if duration not in (3, 4, 5):
        raise HTTPException(
            status_code=400,
            detail="Invalid video duration."
        )

    if not 4 <= steps <= 8:
        raise HTTPException(
            status_code=400,
            detail="Generation steps must be between 4 and 8."
        )

    if not 1 <= quality <= 10:
        raise HTTPException(
            status_code=400,
            detail="Quality must be between 1 and 10."
        )

    temporary_image = (
        UPLOAD_DIR / f"{uuid.uuid4().hex}{extension}"
    )

    try:

        with temporary_image.open("wb") as destination:
            shutil.copyfileobj(
                image.file,
                destination
            )

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

        return {
            "success": True,
            "video_url": f"/videos/{generated_video.name}",
            "filename": generated_video.name
        }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=f"Video generation failed: {error}"
        )

    finally:

        temporary_image.unlink(missing_ok=True)
        await image.close()


# --------------------------------------------------
# DISPLAY AND DOWNLOAD GENERATED VIDEOS
# --------------------------------------------------

@app.get("/videos/{filename}")
async def get_video(filename: str):

    if Path(filename).name != filename:
        raise HTTPException(
            status_code=400,
            detail="Invalid filename."
        )

    video_path = OUTPUT_DIR / filename

    if not video_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Video not found."
        )

    return FileResponse(
        video_path,
        media_type="video/mp4",
        filename=filename
    )


# --------------------------------------------------
# AUTOMATIC BROWSER OPENING
# --------------------------------------------------

def open_browser():
    time.sleep(2)
    webbrowser.open("http://127.0.0.1:8002")


# --------------------------------------------------
# START SERVER
# --------------------------------------------------

if __name__ == "__main__":

    threading.Thread(
        target=open_browser,
        daemon=True
    ).start()

    import uvicorn

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8002
    )
