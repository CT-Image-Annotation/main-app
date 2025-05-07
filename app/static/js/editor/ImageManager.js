export function ImageManager() {
    let canvas, ctx;
    let regions = [];
  
    function createCanvas(width, height) {
      canvas = document.createElement("canvas");
      canvas.width = width;
      canvas.height = height;
      canvas.style.border = "1px solid black";
      ctx = canvas.getContext("2d");
      return canvas;
    }
  
    function getElement() {
      const container = document.createElement("div");
      container.className = "image-layer";
      container.style.position = "relative";
  
      const sourceImg = document.querySelector("#slide-img");
  
      if (!sourceImg) {
        container.innerText = "Image #slide-img not found.";
        return container;
      }
  
      const renderCanvas = () => {
        const w = sourceImg.naturalWidth;
        const h = sourceImg.naturalHeight;
        const canvasEl = createCanvas(w, h);
        ctx.drawImage(sourceImg, 0, 0, w, h);
        container.appendChild(canvasEl);
      };
  
      if (sourceImg.complete) {
        renderCanvas();
      } else {
        sourceImg.addEventListener("load", renderCanvas);
      }  
  
      return container;
    }

    function addRegion(region) {
        regions.push(region);
    }

    function setRegions(regions2) {
        regions = regions2
    }

    return {
      getElement,
      getCanvas: () => canvas,
      getContext: () => ctx,
      getRegions: () => regions,
      addRegion,
      setRegions,
    };
  }
  