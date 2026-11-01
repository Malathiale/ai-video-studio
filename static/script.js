
document.addEventListener("DOMContentLoaded", function () {
    const imageUpload = document.getElementById("imageUpload");
    const imagePreview = document.getElementById("imagePreview");
    const promptInput = document.getElementById("prompt");
    const negativePromptInput = document.getElementById("negativePrompt");
    const durationInput = document.getElementById("duration");
    const stepsInput = document.getElementById("steps");
    const qualityInput = document.getElementById("quality");
    const seedInput = document.getElementById("seed");
    const generateBtn = document.getElementById("generateBtn");
    const videoGallery = document.getElementById("videoGallery");

    const STORAGE_KEY = "aiVideoStudioCreations";
    let selectedImage = null;

    // Load saved gallery entries from this browser.
    function getSavedVideos() {
        try {
            const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
            return Array.isArray(saved) ? saved : [];
        } catch (error) {
            console.error("Could not load saved gallery:", error);
            return [];
        }
    }

    // Save gallery entries in this browser.
    function saveVideos(videos) {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(videos));
        } catch (error) {
            console.error("Could not save gallery:", error);
        }
    }

    // Display the gallery.
    function renderGallery() {
        if (!videoGallery) return;

        const videos = getSavedVideos();
        videoGallery.replaceChildren();

        if (videos.length === 0) {
            const emptyMessage = document.createElement("div");
            emptyMessage.className = "gallery-empty";

            const heading = document.createElement("h3");
            heading.textContent = "Your gallery is waiting";

            const message = document.createElement("p");
            message.textContent =
                "Generate your first video and it will appear here.";

            emptyMessage.append(heading, message);
            videoGallery.appendChild(emptyMessage);
            return;
        }

        videos.forEach(function (item) {
            const card = document.createElement("article");
            card.className = "gallery-card";

            const video = document.createElement("video");
            video.src = item.video_url;
            video.controls = true;
            video.preload = "metadata";
            video.playsInline = true;

            const title = document.createElement("h3");
            title.textContent = item.filename || "My AI Video";

            const date = document.createElement("p");
            date.className = "gallery-date";
            date.textContent = item.created_at
                ? new Date(item.created_at).toLocaleString()
                : "";

            const download = document.createElement("a");
            download.href = item.video_url;
            download.download = item.filename || "generated-video.mp4";
            download.textContent = "Download Video";
            download.className = "gallery-download";

            card.append(video, title, date, download);
            videoGallery.appendChild(card);
        });
    }

    // Show the saved gallery immediately when the page opens.
    renderGallery();

    // Handle image upload and preview.
    imageUpload.addEventListener("change", function () {
        const file = imageUpload.files[0];

        if (!file) return;

        if (!["image/png", "image/jpeg", "image/webp"].includes(file.type)) {
            alert("Please select a PNG, JPG, or WEBP image.");
            imageUpload.value = "";
            selectedImage = null;
            return;
        }

        selectedImage = file;

        const img = document.createElement("img");
        img.src = URL.createObjectURL(file);
        img.alt = "Selected image";
        img.style.width = "100%";
        img.style.height = "100%";
        img.style.objectFit = "contain";

        imagePreview.replaceChildren(img);
    });

    // Generate a new video.
    generateBtn.addEventListener("click", async function () {
        if (!selectedImage) {
            alert("Please upload an image first.");
            return;
        }

        if (!promptInput.value.trim()) {
            alert("Please enter a video prompt.");
            promptInput.focus();
            return;
        }

        const formData = new FormData();
        formData.append("image", selectedImage);
        formData.append("prompt", promptInput.value.trim());
        formData.append("negative_prompt", negativePromptInput.value.trim());
        formData.append("duration", durationInput.value);
        formData.append("steps", stepsInput.value);
        formData.append("quality", qualityInput.value);
        formData.append("seed", seedInput.value);
        formData.append("randomize_seed", "false");

        generateBtn.disabled = true;
        generateBtn.textContent = "Generating...";

        let status = document.getElementById("generationStatus");

        if (!status) {
            status = document.createElement("p");
            status.id = "generationStatus";
            generateBtn.insertAdjacentElement("afterend", status);
        }

        status.textContent = "Sending request to Wan 2.2. Please wait...";

        try {
            const response = await fetch("/generate", {
                method: "POST",
                body: formData
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.detail || "Generation failed.");
            }

            if (!result.success || !result.video_url) {
                throw new Error("The server did not return a video.");
            }

            // Show the newest generated video.
            let output = document.getElementById("generatedVideo");

            if (!output) {
                output = document.createElement("div");
                output.id = "generatedVideo";
                output.className = "panel";
                document.querySelector(".workspace").appendChild(output);
            }

            output.replaceChildren();

            const heading = document.createElement("h2");
            heading.textContent = "Your Generated Video";

            const video = document.createElement("video");
            video.src = result.video_url;
            video.controls = true;
            video.playsInline = true;
            video.style.width = "100%";

            const download = document.createElement("a");
            download.href = result.video_url;
            download.download = result.filename || "generated-video.mp4";
            download.textContent = "Download Video";

            output.append(heading, video, download);

            // Add the new video to the saved gallery.
            const savedVideos = getSavedVideos();

            const newVideo = {
                video_url: result.video_url,
                filename: result.filename || "generated-video.mp4",
                created_at: new Date().toISOString()
            };

            // Avoid adding the same video twice.
            const alreadySaved = savedVideos.some(function (item) {
                return item.video_url === newVideo.video_url;
            });

            if (!alreadySaved) {
                savedVideos.unshift(newVideo);
                saveVideos(savedVideos);
            }

            renderGallery();

            status.textContent =
                "Video generated successfully! It has been added to My Creations.";

        } catch (error) {
            status.textContent = "Error: " + error.message;
            console.error(error);
        } finally {
            generateBtn.disabled = false;
            generateBtn.textContent = "Generate Video ↗";
        }
    });
});
