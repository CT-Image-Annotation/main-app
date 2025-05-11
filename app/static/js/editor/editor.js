import { CursorManager } from './CursorManager.js';
import { ImageManager } from './ImageManager.js';

function setupEditor(editorEl) {
    const imageManager = ImageManager();
    const cursorManager = CursorManager(imageManager);


    const container = document.createElement("div");
    container.style.border = "1px solid #000";
    container.style.padding = "10px";

    const title = document.createElement("h3");
    title.textContent = "Editor UI";

    container.appendChild(title);
    container.appendChild(cursorManager.getElement());
    container.appendChild(imageManager.getElement());

    editorEl.appendChild(container);

    cursorManager.bindCanvas(imageManager.getCanvas());

}

// document.addEventListener("DOMContentLoaded", () => {
//     document.querySelectorAll(".editor").forEach(setupEditor);
// });

window.addEventListener("load", () => {
  const img = document.querySelector("#slide-img");

  function tryInitEditor() {
    if (img.complete && img.naturalWidth > 0) {
      // Image is fully loaded and valid
      document.querySelectorAll(".editor").forEach(setupEditor);
    } else {
      // Wait for it to actually load
      img.addEventListener("load", () => {
        document.querySelectorAll(".editor").forEach(setupEditor);
      });
    }
  }

  tryInitEditor();
});