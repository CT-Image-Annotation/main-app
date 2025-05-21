// Convert a URL like '/process/image/1?t=1234567' to the absolute URL
        let absoluteURL = dataURL;
        if (dataURL.startsWith('/')) {
          absoluteURL = baseUrl + dataURL;
        }
        
        fetch(absoluteURL)
          .then(response => response.blob())
          .then(blob => {
            const reader = new FileReader();
            reader.onloadend = function() {
              callback(reader.result);
            };
            reader.readAsDataURL(blob);
          })
          .catch(error => {
            console.error("Error fetching image:", error);
            const loadingDiv = document.getElementById('loadingIndicator');
            if (loadingDiv) loadingDiv.remove();
            if (runSegmentationBtn) {
              runSegmentationBtn.textContent = "Run Segmentation";
              runSegmentationBtn.disabled = false;
            }
            isProcessing = false;
            alert("Error loading image. Please try again.");
          });
      };
      tempImg.src = dataURL;
    } else {
      console.error("No image data available");
      const loadingDiv = document.getElementById('loadingIndicator');
      if (loadingDiv) loadingDiv.remove();
      if (runSegmentationBtn) {
        runSegmentationBtn.textContent = "Run Segmentation";
        runSegmentationBtn.disabled = false;
      }
      isProcessing = false;
      alert("No image data available. Please load an image first.");
    }
  };
  
  // Get the data URL and then send the segmentation request
  convertImageToDataURL(function(imageDataURL) {
    console.log("Image converted to data URL, length:", imageDataURL ? imageDataURL.length : 0);
    
    // Prepare the request data with the proper data URL
    const requestData = {
      image_data: imageDataURL,
      positive_points: positivePoints,
      negative_points: negativePoints,
      draw_path: drawPath
    };
    
    console.log("Sending segmentation request with data:", {
      "image_data_length": imageDataURL ? imageDataURL.length : 0,
      "positive_points": positivePoints,
      "negative_points": negativePoints,
      "draw_path_length": drawPath ? drawPath.length : 0
    });
    
    // Try absolute URL to ensure correct path
    const baseUrl = window.location.origin; // Get the base URL of the current page
    
    // First try a diagnostic endpoint
    fetch(`${baseUrl}/medsam/debug_segmentation`, {
      method: "POST", 
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(requestData)
    })
    .then(r => r.json())
    .then(debug => {
      console.log("Debug segmentation result:", debug);
      
      // Proceed with actual segmentation only if debug was successful
      if (debug.success) {
        return fetch(`${baseUrl}/medsam/run_segmentation`, {
          method: "POST", 
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify(requestData)
        });
      } else {
        throw new Error(`Debug failed: ${JSON.stringify(debug.steps)}`);
      }
    })
    .then(r => {
      if (!r.ok) {
        return r.text().then(text => {
          console.error("Server response text:", text);
          throw new Error(`Server returned ${r.status}: ${r.statusText}`);
        });
      }
      return r.json();
    })
    .then(d => {
      console.log("Response received:", d);
      
      // Remove loading indicator
      const loadingIndicator = document.getElementById('loadingIndicator');
      if (loadingIndicator) loadingIndicator.remove();
      
      // Reset button state
      if (runSegmentationBtn) {
        runSegmentationBtn.textContent = "Run Segmentation";
        runSegmentationBtn.disabled = false;
      }
      isProcessing = false;
      
      if (!d.success) {
        alert(`Server error: ${d.error || "Unknown error"}`);
        return;
      }
      
      if (d.overlay) {
        // Reset mask arrays before adding new masks
        allMasks = [];
        allScores = [];
        currentMaskIndex = 0;
        
        // Check if multiple masks are returned
        if (d.all_masks && d.all_scores && d.all_masks.length > 0) {
          console.log("Received multiple masks:", d.all_masks.length);
          
          // Store all masks and scores
          allMasks = d.all_masks;
          allScores = d.all_scores;
          
          // Sort masks by size (number of true pixels) - smallest first
          const maskSizes = allMasks.map(mask => mask.filter(Boolean).length);
          console.log("Mask sizes:", maskSizes);
          
          // Create array to hold the original indices
          const indices = Array.from({ length: allMasks.length }, (_, i) => i);
          
          // Sort indices by mask sizes
          indices.sort((a, b) => maskSizes[a] - maskSizes[b]);
          
          // Reorder masks and scores based on size
          allMasks = indices.map(i => allMasks[i]);
          allScores = indices.map(i => allScores[i]);
          
          // Start with the smallest mask (S)
          currentMaskIndex = 0;
          
          console.log("Masks reordered by size: S, M, L");
          
          // Display the smallest mask
          updateMaskDisplay();
        } else {
          // Handle single mask case (legacy support)
          console.log("Received single mask");
          
          // Create a new image element for the overlay
          const ov = new Image();
          ov.crossOrigin = "Anonymous";
          
          // Set onload before setting src
          ov.onload = () => {
            console.log("Overlay image loaded, dimensions:", ov.width, "x", ov.height);
            
            // If we have the original image, use that instead of the previously loaded image
            if (d.original) {
              const originalImg = new Image();
              originalImg.onload = () => {
                img = originalImg;
                
                // Clear the canvas
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                
                // Draw in proper order: first original image, then overlay
                ctx.drawImage(img, 0, 0);
                ctx.drawImage(ov, 0, 0);
                
                console.log("Overlay displayed, confidence score:", d.score);
                
                // Hide mask navigation
                if (maskNavigation) {
                  maskNavigation.style.display = "none";
                }
                
                // Explicitly draw selections on top AFTER overlay
                drawSelectionsOnTop();
              };
              originalImg.src = d.original;
            } else {
              // Clear the canvas
              ctx.clearRect(0, 0, canvas.width, canvas.height);
              
              // Draw in proper order: first original image, then overlay
              ctx.drawImage(img, 0, 0);
              ctx.drawImage(ov, 0, 0);
              
              console.log("Overlay displayed, confidence score:", d.score);
              
              // Hide mask navigation
              if (maskNavigation) {
                maskNavigation.style.display = "none";
              }
              
              // Explicitly draw selections on top AFTER overlay
              drawSelectionsOnTop();
            }
          };
          
          ov.onerror = (e) => {
            console.error("Error loading overlay image:", e);
            alert("Error displaying segmentation result");
            isProcessing = false;
          };
          
          // Set the source after defining handlers
          ov.src = d.overlay;
          
          // Store mask separately if available
          if (d.mask) {
            const maskImg = new Image();
            maskImg.src = d.mask;
            console.log("Received separate mask image");
            
            // You can use this maskImg in your application if needed
            // For example, store it in a global variable
            window.currentMaskImage = maskImg;
          }
        }
      } else {
        console.error("No overlay in response:", d);
        alert("Error: No segmentation mask received");
        isProcessing = false;
      }
    })
    .catch(err => {
      // Remove loading indicator
      const loadingIndicator = document.getElementById('loadingIndicator');
      if (loadingIndicator) loadingIndicator.remove();
      
      console.error("Fetch error:", err);
      alert("Error during segmentation: " + err.message);
      if (runSegmentationBtn) {
        runSegmentationBtn.textContent = "Run Segmentation";
        runSegmentationBtn.disabled = false;
      }
      isProcessing = false;
    });
  });
}

function clearSelections() {
  points = [];
  currentBox = null;
  drawingPath = [];
  
  // Reset mask state
  allMasks = [];
  allScores = [];
  currentMaskIndex = 0;
  if (maskNavigation) {
    maskNavigation.style.display = "none";
  }
  
  updatePointsList();
  updateBoxInfo();
  updateSegmentationButtonState();
  if (img.src) {
    redrawCanvas();
  }
}

function resetView() {
  if (dataURL) {
    // Reset mask state when resetting the view
    allMasks = [];
    allScores = [];
    currentMaskIndex = 0;
    if (maskNavigation) {
      maskNavigation.style.display = "none";
    }
    
    redrawCanvas();
  }
}

// Initialize the module
function initialize() {
  console.log("Initializing segmentation tools...");
  
  // Check if fileInput exists, if not, create a dummy one
  if (!document.getElementById('fileInput')) {
    fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.id = 'fileInput';
    fileInput.style.display = 'none';
    document.body.appendChild(fileInput);
  } else {
    fileInput = document.getElementById('fileInput');
  }
  
  // Find and initialize UI elements
  runSegmentationBtn = document.getElementById("runSegmentation");
  clearSelectionsBtn = document.getElementById("clearSelections");
  pointsList = document.getElementById("pointsList");
  boxInfo = document.getElementById("boxInfo");
  claheBtn = document.getElementById("claheBtn");
  resetBtn = document.getElementById("resetBtn");
  
  maskNavigation = document.getElementById("maskNavigation");
  maskInfo = document.getElementById("maskInfo");
  prevMaskBtn = document.getElementById("prevMask");
  nextMaskBtn = document.getElementById("nextMask");
  
  // Setup canvas event listeners
  if (canvas) {
    canvas.addEventListener("mousedown", handleCanvasMouseDown);
    canvas.addEventListener("mousemove", handleCanvasMouseMove);
    canvas.addEventListener("mouseup", handleCanvasMouseUp);
    canvas.addEventListener("mouseleave", handleCanvasMouseLeave);
    canvas.addEventListener("click", handleCanvasClick);
  } else {
    console.error("Canvas element not found! Segmentation tools initialization failed.");
    return;
  }
  
  // Setup button event handlers
  if (claheBtn) {
    claheBtn.onclick = applyClahe;
  }
  
  if (resetBtn) {
    resetBtn.onclick = resetView;
  }
  
  if (runSegmentationBtn) {
    runSegmentationBtn.onclick = runSegmentation;
  }
  
  if (clearSelectionsBtn) {
    clearSelectionsBtn.onclick = clearSelections;
  }
  
  // Setup mask navigation
  if (prevMaskBtn) {
    prevMaskBtn.addEventListener("click", () => {
      if (allMasks.length > 1) {
        currentMaskIndex = (currentMaskIndex - 1 + allMasks.length) % allMasks.length;
        updateMaskDisplay();
      }
    });
  }

  if (nextMaskBtn) {
    nextMaskBtn.addEventListener("click", () => {
      if (allMasks.length > 1) {
        currentMaskIndex = (currentMaskIndex + 1) % allMasks.length;
        updateMaskDisplay();
      }
    });
  }
  
  // Set up selection mode radio buttons
  document.querySelectorAll('input[name="selectionType"]').forEach(radio => {
    radio.addEventListener('change', e => {
      selectionMode = e.target.value;
      
      // Update cursor based on selection mode
      if (selectionMode === "draw") {
        canvas.style.cursor = "pointer";
      } else {
        canvas.style.cursor = "crosshair";
      }
    });
  });
  
  // Initialize UI with null checks
  if (pointsList) updatePointsList();
  if (boxInfo) updateBoxInfo();
  if (runSegmentationBtn) updateSegmentationButtonState();
  
  // Check model status
  checkModelStatus();
  
  console.log("Segmentation tools initialized successfully");
}

// Export functions to global scope immediately
// This ensures they're available as soon as the script loads
window.initializeSegmentationTools = initialize;
window.initializeImageNavigation = initializeImageNavigation;
window.loadImage = loadImage;
window.calculateWeightedAveragePoint = calculateWeightedAveragePoint;
window.updatePointsList = updatePointsList;
window.updateBoxInfo = updateBoxInfo;
window.updateSegmentationButtonState = updateSegmentationButtonState;
window.redrawCanvas = redrawCanvas;
window.drawSelectionsOnTop = drawSelectionsOnTop;
window.updateMaskDisplay = updateMaskDisplay;
window.runSegmentation = runSegmentation;

// Auto-initialize on DOMContentLoaded
document.addEventListener('DOMContentLoaded', initialize);// DOM Element References - initialized immediately
let fileInput = null; // This will be initialized later or created if missing
const canvas = document.getElementById("canvas");
const ctx = canvas.getContext("2d");
let runSegmentationBtn = document.getElementById("runSegmentation");
let clearSelectionsBtn = document.getElementById("clearSelections");
let pointsList = document.getElementById("pointsList");
let boxInfo = document.getElementById("boxInfo");
let claheBtn = document.getElementById("claheBtn");
let resetBtn = document.getElementById("resetBtn");

// These elements will be initialized in DOMContentLoaded
let maskNavigation;
let maskInfo;
let prevMaskBtn;
let nextMaskBtn;

// State Variables
let img = new Image(), dataURL = null;
let selectionMode = "draw"; // Default selection mode to match HTML
let boxStart = null;
let currentBox = null; // Store the current box
let points = []; // Store points as {x, y, label}
let isProcessing = false; // Flag to prevent multiple concurrent requests

// Drawing state variables
let isDrawing = false;
let drawingPath = []; // Store draw path points for weighted average calculation

// Multi-mask variables
let allMasks = []; // Store all available masks
let allScores = []; // Store scores for all masks
let currentMaskIndex = 0; // Current mask index being displayed

// Navigation variables
let fileIds = [];
let urlTemplate = "";
let currentFileIndex = 0;

// Function to update the displayed mask
function updateMaskDisplay() {
  if (!img.src || allMasks.length === 0) {
    if (maskNavigation) {
      maskNavigation.style.display = "none";
    }
    return;
  }
  
  // Show the navigation controls if they exist
  if (maskNavigation) {
    maskNavigation.style.display = "flex";
  }
  
  // Get size label based on index (S, M, L)
  const sizeLabels = ["S", "M", "L"];
  const sizeLabel = sizeLabels[currentMaskIndex % sizeLabels.length];
  
  // Update mask info text with size label
  if (maskInfo) {
    maskInfo.textContent = `Mask ${sizeLabel} (${allScores[currentMaskIndex].toFixed(3)})`;
  }
  
  // Get current mask
  const mask = allMasks[currentMaskIndex];
  
  // Create overlay canvas
  const overlayCanvas = createOverlay(mask);
  
  // Draw the result
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(img, 0, 0);
  ctx.drawImage(overlayCanvas, 0, 0);
  
  // Redraw selections on top
  drawSelectionsOnTop();
  
  console.log("Updated display to show mask", sizeLabel);
}

// Helper function to create an overlay Image from a mask
function createOverlay(mask) {
  // Create a canvas to draw the overlay
  const overlayCanvas = document.createElement('canvas');
  overlayCanvas.width = canvas.width;
  overlayCanvas.height = canvas.height;
  const overlayCtx = overlayCanvas.getContext('2d');
  
  // Draw the original image
  overlayCtx.drawImage(img, 0, 0);
  
  // Get image data
  const imageData = overlayCtx.getImageData(0, 0, canvas.width, canvas.height);
  const data = imageData.data;
  
  // Apply the mask with red highlight
  for (let y = 0; y < canvas.height; y++) {
    for (let x = 0; x < canvas.width; x++) {
      const idx = y * canvas.width + x;
      const pixelIdx = idx * 4;
      
      if (mask[idx]) {
        // Apply semi-transparent red overlay (RGBA)
        data[pixelIdx] = Math.round(data[pixelIdx] * 0.4 + 255 * 0.6);     // R
        data[pixelIdx + 1] = Math.round(data[pixelIdx + 1] * 0.4);         // G
        data[pixelIdx + 2] = Math.round(data[pixelIdx + 2] * 0.4);         // B
        // Alpha remains unchanged
      }
    }
  }
  
  // Put the modified image data back
  overlayCtx.putImageData(imageData, 0, 0);
  
  return overlayCanvas;
}

// Helper function to draw mask contours
function drawContours(ctx, mask, width, height) {
  ctx.strokeStyle = "yellow";
  ctx.lineWidth = 2;
  
  // Simple edge detection algorithm - more efficient approach
  const visited = new Set();
  
  for (let y = 1; y < height - 1; y++) {
    for (let x = 1; x < width - 1; x++) {
      const idx = y * width + x;
      
      // Skip if already visited or not part of mask
      if (visited.has(idx) || !mask[idx]) continue;
      
      // Check if this is an edge pixel
      const top = (y - 1) * width + x;
      const bottom = (y + 1) * width + x;
      const left = y * width + (x - 1);
      const right = y * width + (x + 1);
      
      const isEdge = !mask[top] || !mask[bottom] || !mask[left] || !mask[right];
      
      if (isEdge) {
        ctx.beginPath();
        ctx.arc(x, y, 1, 0, Math.PI * 2);
        ctx.stroke();
        visited.add(idx);
      }
    }
  }
}

// Function to draw selections on top of the canvas
function drawSelectionsOnTop() {
  // Draw box if exists
  if (currentBox) {
    ctx.strokeStyle = "blue";
    ctx.lineWidth = 2;
    ctx.strokeRect(
      currentBox[0], 
      currentBox[1], 
      currentBox[2] - currentBox[0], 
      currentBox[3] - currentBox[1]
    );
  }
  
  // Draw only visible points
  points.forEach(point => {
    if (!point.hidden) {
      ctx.beginPath();
      ctx.arc(point.x, point.y, 6, 0, 2 * Math.PI);
      ctx.fillStyle = point.label === 1 ? 'green' : 'red';
      ctx.fill();
      ctx.strokeStyle = 'white';
      ctx.lineWidth = 2;
      ctx.stroke();
    }
  });
}

// UI Update Functions
function updatePointsList() {
  if (!pointsList) return;
  
  pointsList.innerHTML = '<strong>Points:</strong> ';
  
  // Count visible and hidden points
  const visiblePoints = points.filter(p => !p.hidden);
  const hiddenPoints = points.filter(p => p.hidden);
  
  // No points at all
  if (points.length === 0) {
    pointsList.innerHTML += '<span>No points selected</span>';
    return;
  }
  
  // Display drawing info if we have hidden points
  if (hiddenPoints.length > 0) {
    const drawingInfo = document.createElement('span');
    drawingInfo.classList.add('point-item');
    drawingInfo.classList.add('positive');
    drawingInfo.textContent = `Drawing selection applied`;
    
    const removeBtn = document.createElement('button');
    removeBtn.textContent = 'x';
    removeBtn.style.marginLeft = '3px';
    removeBtn.onclick = () => {
      // Remove all hidden points
      points = points.filter(p => !p.hidden);
      updatePointsList();
      redrawCanvas();
      updateSegmentationButtonState();
    };
    
    drawingInfo.appendChild(removeBtn);
    pointsList.appendChild(drawingInfo);
  }
  
  // Then list visible points
  if (visiblePoints.length === 0 && hiddenPoints.length > 0) {
    // Only show the drawing info, already added above
  } else if (visiblePoints.length === 0) {
    pointsList.innerHTML += '<span>No points selected</span>';
  } else {
    // Display visible points
    visiblePoints.forEach((point, index) => {
      const pointEl = document.createElement('span');
      pointEl.classList.add('point-item');
      pointEl.classList.add(point.label === 1 ? 'positive' : 'negative');
      pointEl.textContent = `(${point.x},${point.y}) - ${point.label === 1 ? 'Include' : 'Exclude'}`;
      
      const removeBtn = document.createElement('button');
      removeBtn.textContent = 'x';
      removeBtn.style.marginLeft = '3px';
      removeBtn.onclick = () => {
        // Remove this specific point
        const pointIndex = points.indexOf(point);
        if (pointIndex !== -1) {
          points.splice(pointIndex, 1);
          updatePointsList();
          redrawCanvas();
          updateSegmentationButtonState();
        }
      };
      
      pointEl.appendChild(removeBtn);
      pointsList.appendChild(pointEl);
    });
  }
}

function updateBoxInfo() {
  if (!boxInfo) return;
  
  if (currentBox) {
    boxInfo.innerHTML = `<strong>Box:</strong> <span class="box-info">(${currentBox[0]},${currentBox[1]}) to (${currentBox[2]},${currentBox[3]})</span> `;
    
    const removeBtn = document.createElement('button');
    removeBtn.textContent = 'x';
    removeBtn.onclick = () => {
      currentBox = null;
      updateBoxInfo();
      redrawCanvas();
      updateSegmentationButtonState();
    };
    
    boxInfo.appendChild(removeBtn);
  } else {
    boxInfo.innerHTML = '<strong>Box:</strong> <span>No box selected</span>';
  }
}

function updateSegmentationButtonState() {
  // Enable the Run Segmentation button if there's either a box or at least one point
  if (runSegmentationBtn) {
    runSegmentationBtn.disabled = (points.length === 0 && !currentBox);
  }
}

function redrawCanvas() {
  if (!img.src) return;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(img, 0, 0);
  
  // If we have masks, display the current one
  if (allMasks.length > 0) {
    updateMaskDisplay();
    return;
  }
  
  // Otherwise, just draw selections
  drawSelectionsOnTop();
}

// Calculate weighted average point from a drawing path
function calculateWeightedAveragePoint(path) {
  if (path.length === 0) return null;
  
  // Simple average if we have few points
  if (path.length < 3) {
    let sumX = 0, sumY = 0;
    path.forEach(point => {
      sumX += point.x;
      sumY += point.y;
    });
    return {
      x: Math.round(sumX / path.length),
      y: Math.round(sumY / path.length)
    };
  }
  
  // For longer paths, calculate a weighted average
  // We'll use a simple distance-based weighting
  let totalWeight = 0;
  let weightedSumX = 0;
  let weightedSumY = 0;
  
  // Calculate the center of mass of all points as a reference
  let centerX = 0, centerY = 0;
  path.forEach(point => {
    centerX += point.x;
    centerY += point.y;
  });
  centerX /= path.length;
  centerY /= path.length;
  
  // Calculate weighted average - give more weight to points farther from center
  path.forEach(point => {
    // Distance from center (weight)
    const dx = point.x - centerX;
    const dy = point.y - centerY;
    const distance = Math.sqrt(dx * dx + dy * dy);
    const weight = distance + 1; // Add 1 to avoid zero weights
    
    totalWeight += weight;
    weightedSumX += point.x * weight;
    weightedSumY += point.y * weight;
  });
  
  // Return the weighted average point
  return {
    x: Math.round(weightedSumX / totalWeight),
    y: Math.round(weightedSumY / totalWeight)
  };
}

// Load image function for the image navigator
function loadImage(index) {
  if (!fileIds || fileIds.length === 0 || !urlTemplate) {
    console.error("Image navigation not properly initialized");
    return;
  }
  
  currentFileIndex = index;
  const fileId = fileIds[index];
  const url = urlTemplate.replace('0', fileId) + `?t=${Date.now()}`;
  
  // Create an image object to load the file
  const newImg = new Image();
  newImg.onload = () => {
    // Set canvas dimensions to match image
    canvas.width = newImg.width;
    canvas.height = newImg.height;
    
    // Set container dimensions if it exists
    const wrapper = canvas.parentElement;
    if (wrapper) {
      wrapper.style.width = newImg.width + 'px';
      wrapper.style.height = newImg.height + 'px';
    } else {
      console.warn("Canvas parent element not found, cannot set wrapper dimensions");
    }
    
    // Update the global image
    img = newImg;
    dataURL = url;
    
    // Draw the image
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0);
    
    // Reset segmentation UI elements
    points = [];
    currentBox = null;
    allMasks = [];
    allScores = [];
    drawingPath = [];
    
    // Update UI
    updatePointsList();
    updateBoxInfo();
    updateSegmentationButtonState();
    
    // Hide mask navigation
    if (maskNavigation) {
      maskNavigation.style.display = 'none';
    }
    
    // Update UI elements
    const currentIndexEl = document.getElementById('current-index');
    const slider = document.getElementById('image-slider');
    
    if (currentIndexEl) {
      currentIndexEl.textContent = index + 1;
    }
    
    if (slider) {
      slider.value = index + 1;
    }
  };
  
  newImg.onerror = () => console.error('Failed to load image:', url);
  newImg.src = url;
}

// Initialize image navigation
function initializeImageNavigation(ids, template) {
  fileIds = ids;
  urlTemplate = template;
  
  const prevBtn = document.getElementById('prev');
  const nextBtn = document.getElementById('next');
  const slider = document.getElementById('image-slider');
  
  if (prevBtn) {
    prevBtn.addEventListener('click', () => {
      const newIndex = (currentFileIndex - 1 + fileIds.length) % fileIds.length;
      loadImage(newIndex);
    });
  }
  
  if (nextBtn) {
    nextBtn.addEventListener('click', () => {
      const newIndex = (currentFileIndex + 1) % fileIds.length;
      loadImage(newIndex);
    });
  }
  
  if (slider) {
    slider.addEventListener('input', () => {
      const newIndex = +slider.value - 1;
      loadImage(newIndex);
    });
  }
  
  // Load the first image
  if (fileIds.length > 0) {
    loadImage(0);
  }
}

// CLAHE button handler
function applyClahe() {
  if (!dataURL) return;
  
  // Try absolute URL to ensure correct path
  const baseUrl = window.location.origin; // Get the base URL of the current page
  
  fetch(`${baseUrl}/medsam/apply_clahe`, {
    method: "POST", 
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({image: dataURL})
  })
  .then(r => r.json())
  .then(d => {
    dataURL = d.image;
    img.src = dataURL;
    img.onload = () => {
      redrawCanvas();
    };
  })
  .catch(err => {
    console.error("Error applying CLAHE:", err);
  });
}

// Mouse event handling for drawing and other selection modes
function handleCanvasMouseDown(e) {
  if (!dataURL) return;
  
  const r = canvas.getBoundingClientRect();
  const x = e.clientX - r.left;
  const y = e.clientY - r.top;
  
  if (selectionMode === "box") {
    boxStart = {x, y};
  } else if (selectionMode === "draw") {
    isDrawing = true;
    drawingPath = [{x, y}]; // Start a new drawing path
    
    // Start drawing visually
    ctx.save(); // Save the current canvas state
    ctx.strokeStyle = "rgba(0, 255, 0, 0.5)"; // Semi-transparent green
    ctx.lineWidth = 3;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.beginPath();
    ctx.moveTo(x, y);
  }
}

function handleCanvasMouseMove(e) {
  if (!dataURL) return;
  
  const r = canvas.getBoundingClientRect();
  const x = e.clientX - r.left;
  const y = e.clientY - r.top;
  
  if (selectionMode === "box" && boxStart) {
    redrawCanvas();
    ctx.strokeStyle = "blue";
    ctx.lineWidth = 2;
    ctx.strokeRect(boxStart.x, boxStart.y, x - boxStart.x, y - boxStart.y);
  } else if (selectionMode === "draw" && isDrawing) {
    // Add point to the drawing path
    drawingPath.push({x, y});
    
    // Visualize the drawing
    ctx.lineTo(x, y);
    ctx.stroke();
  }
}

function handleCanvasMouseUp(e) {
  if (!dataURL) return;
  
  const r = canvas.getBoundingClientRect();
  const x = e.clientX - r.left;
  const y = e.clientY - r.top;
  
  if (selectionMode === "box" && boxStart) {
    // Store the box coordinates
    currentBox = [
      Math.min(boxStart.x, x), 
      Math.min(boxStart.y, y),
      Math.max(boxStart.x, x), 
      Math.max(boxStart.y, y)
    ];
    
    updateBoxInfo();
    redrawCanvas();
    updateSegmentationButtonState();
    boxStart = null;
    
    // Auto-run segmentation after box selection
    if (dataURL && currentBox) {
      // Only run if box has reasonable size (more than 10x10 pixels)
      if ((currentBox[2] - currentBox[0]) > 10 && (currentBox[3] - currentBox[1]) > 10) {
        console.log("Auto-running segmentation after box selection");
        // Use a small timeout to let the UI update first
        setTimeout(() => {
          if (runSegmentationBtn) runSegmentationBtn.click();
        }, 100);
      }
    }
  } else if (selectionMode === "draw" && isDrawing) {
    // End drawing
    isDrawing = false;
    ctx.restore(); // Restore canvas state
    
    // Calculate weighted average point from the drawing
    const avgPoint = calculateWeightedAveragePoint(drawingPath);
    
    if (avgPoint) {
      // Store the point internally but don't display it
      // We'll use a special property to mark this as a hidden point
      const hiddenPoint = {x: avgPoint.x, y: avgPoint.y, label: 1, hidden: true};
      points.push(hiddenPoint);
      
      // Update segmentation button state without redrawing canvas
      updateSegmentationButtonState();
      
      // Auto-run segmentation with the new point
      console.log("Auto-running segmentation after drawing, using hidden point:", avgPoint);
      updatePointsList(); // Add this to show the drawing selection in the UI
      setTimeout(() => {
        if (runSegmentationBtn) runSegmentationBtn.click();
      }, 100);
    }
  }
}

// Handle mouse leaving the canvas while drawing
function handleCanvasMouseLeave() {
  if (selectionMode === "draw" && isDrawing) {
    isDrawing = false;
    ctx.restore(); // Restore canvas state
    
    // Calculate weighted average point and add it if the path is long enough
    if (drawingPath.length > 5) {
      const avgPoint = calculateWeightedAveragePoint(drawingPath);
      if (avgPoint) {
        // Add as hidden point
        points.push({x: avgPoint.x, y: avgPoint.y, label: 1, hidden: true});
        updatePointsList(); // Update UI to show drawing was applied
        updateSegmentationButtonState();
      }
    }
    
    // Clear the drawing path
    drawingPath = [];
  }
}

function handleCanvasClick(e) {
  if ((selectionMode === "positive" || selectionMode === "negative") && dataURL) {
    const r = canvas.getBoundingClientRect();
    const x = Math.round(e.clientX - r.left);
    const y = Math.round(e.clientY - r.top);
    const label = selectionMode === "positive" ? 1 : 0;
    
    // Add point to list
    points.push({x, y, label});
    updatePointsList();
    redrawCanvas();
    updateSegmentationButtonState();
  }
}

// Check and load model functionality
function checkModelStatus() {
  const baseUrl = window.location.origin;
  return fetch(`${baseUrl}/medsam/model_status`)
    .then(response => response.json())
    .then(status => {
      console.log("Model status:", status);
      
      // If model is not loaded but can be reloaded, show a button
      if (!status.loaded && status.can_reload) {
        showModelLoadButton();
      }
      
      return status;
    })
    .catch(error => {
      console.error("Error checking model status:", error);
      return { loaded: false, error: error.message };
    });
}

function reloadModel() {
  const loadingMsg = document.createElement('div');
  loadingMsg.id = 'modelLoadingMsg';
  loadingMsg.innerHTML = 'Loading model, this may take a minute...';
  loadingMsg.style.position = 'fixed';
  loadingMsg.style.top = '50%';
  loadingMsg.style.left = '50%';
  loadingMsg.style.transform = 'translate(-50%, -50%)';
  loadingMsg.style.padding = '20px';
  loadingMsg.style.background = 'rgba(0,0,0,0.8)';
  loadingMsg.style.color = 'white';
  loadingMsg.style.borderRadius = '10px';
  loadingMsg.style.zIndex = '10000';
  document.body.appendChild(loadingMsg);
  
  const baseUrl = window.location.origin;
  return fetch(`${baseUrl}/medsam/reload_model`, { method: 'POST' })
    .then(response => response.json())
    .then(result => {
      document.body.removeChild(loadingMsg);
      
      if (result.success) {
        alert('Model loaded successfully!');
        
        // Hide the load model button if visible
        const loadBtn = document.getElementById('loadModelBtn');
        if (loadBtn) loadBtn.style.display = 'none';
        
        return true;
      } else {
        alert(`Failed to load model: ${result.error || 'Unknown error'}`);
        return false;
      }
    })
    .catch(error => {
      document.body.removeChild(loadingMsg);
      alert(`Error reloading model: ${error.message}`);
      return false;
    });
}

function showModelLoadButton() {
  // Check if button already exists
  if (document.getElementById('loadModelBtn')) return;
  
  const btn = document.createElement('button');
  btn.id = 'loadModelBtn';
  btn.textContent = 'Load Segmentation Model';
  btn.style.position = 'fixed';
  btn.style.top = '10px';
  btn.style.right = '10px';
  btn.style.zIndex = '9999';
  btn.style.padding = '10px 15px';
  btn.style.background = '#007bff';
  btn.style.color = 'white';
  btn.style.border = 'none';
  btn.style.borderRadius = '5px';
  btn.style.cursor = 'pointer';
  
  btn.addEventListener('click', () => {
    reloadModel();
  });
  
  document.body.appendChild(btn);
}

function runSegmentation() {
  if ((points.length === 0 && !currentBox) || !dataURL || isProcessing) return;
  
  // Set processing flag to prevent multiple concurrent requests
  isProcessing = true;
  
  // Show loading indicator
  if (runSegmentationBtn) {
    runSegmentationBtn.textContent = "Processing...";
    runSegmentationBtn.disabled = true;
  }
  
  // Create loading indicator
  const loadingDiv = document.createElement('div');
  loadingDiv.id = 'loadingIndicator';
  loadingDiv.style.position = 'absolute';
  loadingDiv.style.top = '50%';
  loadingDiv.style.left = '50%';
  loadingDiv.style.transform = 'translate(-50%, -50%)';
  loadingDiv.style.background = 'rgba(0,0,0,0.7)';
  loadingDiv.style.color = 'white';
  loadingDiv.style.padding = '15px';
  loadingDiv.style.borderRadius = '5px';
  loadingDiv.style.zIndex = '1000';
  loadingDiv.textContent = 'Processing segmentation...';
  document.body.appendChild(loadingDiv);
  
  // Extract positive and negative points for the new API format
  const positivePoints = points
    .filter(p => p.label === 1)
    .map(p => [p.x, p.y]);
  
  const negativePoints = points
    .filter(p => p.label === 0)
    .map(p => [p.x, p.y]);
  
  // Get drawing path if applicable
  const drawPath = drawingPath.length > 0 ? drawingPath.map(p => [p.x, p.y]) : null;
  
  // Convert the image to a data URL if it's not already
  // This is necessary because the MedSAM controller expects a data URL
  const convertImageToDataURL = (callback) => {
    if (dataURL && dataURL.startsWith('data:')) {
      // If it's already a data URL, use it directly
      callback(dataURL);
    } else if (img && img.complete) {
      // If we have the image loaded, convert it to a data URL
      const canvas = document.createElement('canvas');
      canvas.width = img.width;
      canvas.height = img.height;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(img, 0, 0);
      const dataUrl = canvas.toDataURL('image/png');
      callback(dataUrl);
    } else if (dataURL) {
      // If we have a URL but not a data URL, load the image and convert it
      const tempImg = new Image();
      tempImg.crossOrigin = "Anonymous";
      tempImg.onload = function() {
        const canvas = document.createElement('canvas');
        canvas.width = tempImg.width;
        canvas.height = tempImg.height;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(tempImg, 0, 0);
        const dataUrl = canvas.toDataURL('image/png');
        callback(dataUrl);
      };
      tempImg.onerror = function() {
        // If loading fails, try to get the image via the server
        console.log("Failed to load image directly, trying through server...");
        const baseUrl = window.location.origin;
        
        // Convert a URL like '/