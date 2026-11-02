const copyButton = document.getElementById("copy-message");
const readyMessage = document.getElementById("ready-message");

async function copyMessage() {
    readyMessage.select();
    try {
        await navigator.clipboard.writeText(readyMessage.value);
        copyButton.textContent = "Copied";
    } catch (error) {
        copyButton.textContent = "Text selected, copy it by hand";
    }
}

copyButton.addEventListener("click", copyMessage);