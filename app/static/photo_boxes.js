const photoInput = document.getElementById("photos");
const photoBoxes = document.getElementById("photo-boxes");

function addPhotoBox(file) {
    const preview = document.createElement("img");
    preview.src = URL.createObjectURL(file);
    preview.alt = "";
    preview.addEventListener("error", () => preview.remove());

    const label = document.createElement("label");
    label.textContent = file.name;

    const input = document.createElement("input");
    input.name = "photo_names";
    input.maxLength = 100;
    input.placeholder = "Name (optional)";
    label.appendChild(input);

    const box = document.createElement("div");
    box.className = "photo-box";
    box.append(preview, label);
    photoBoxes.appendChild(box);
}

function showPhotoBoxes() {
    photoBoxes.innerHTML = "";
    for (const file of photoInput.files) {
        addPhotoBox(file);
    }
}

photoInput.addEventListener("change", showPhotoBoxes);