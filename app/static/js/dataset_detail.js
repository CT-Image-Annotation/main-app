document.addEventListener('DOMContentLoaded', function() {
  // Assign Jinja2 variables to JS constants at the top
  const dsId = window.datasetId;
  const fileIds = window.fileIds || [];
  let idx = 0;
  const currentIndexEl = document.getElementById('current-index');
  const currentSliceEl = document.getElementById('current-slice');
  const totalSlicesEl = document.getElementById('total-slices');
  const total = fileIds.length;
  const toolbarEl = document.querySelector('.editor-toolbar');
  const imageCanvas = document.getElementById('image-canvas');
  const annotationCanvas = document.getElementById('annotation-canvas');
  const filterForm = document.getElementById('batch-filter-form');
  let contoursVisible = true;
  let currentTool = 'pen';
  let brushSize = 5;
  let brushColor = '#00ff00';
  let drawing = false;
  let startX = 0;
  let startY = 0;
  let lastX = 0;
  let lastY = 0;
  let interpolationEnabled = false;
  let interpolationSlices = 0;
  let annotationHistory = [];
  let redoStack = [];

  // Check Structure Button
  const checkStructureBtn = document.getElementById('check-structure-btn');
  if (checkStructureBtn) {
    checkStructureBtn.addEventListener('click', async function() {
      const infoDiv = document.getElementById('dataset-structure-info');
      const spinner = infoDiv.querySelector('.spinner-border');
      
      try {
        // Show loading spinner
        infoDiv.style.display = 'block';
        spinner.style.display = 'inline-block';
        infoDiv.innerHTML = ''; // Clear previous content
        infoDiv.appendChild(spinner);
        
        const response = await fetch(`/processing/dataset-info/${dsId}`);
        const data = await response.json();
        
        // Hide spinner
        spinner.style.display = 'none';
        
        if (!response.ok) {
          throw new Error(data.error || 'Failed to fetch dataset info');
        }
        
        if (data.error) {
          infoDiv.innerHTML = `
            <div class="card bg-danger text-light p-3">
              <h5>Error</h5>
              <p>${data.error}</p>
              ${data.file_path ? `<p class="small">File path: ${data.file_path}</p>` : ''}
            </div>
          `;
          return;
        }
        
        infoDiv.innerHTML = `
          <div class="card bg-secondary text-light p-3">
            <h5>Dataset Structure Information</h5>
            <p>Type: <strong>${data.is_multi_slice ? 'Multi-slice' : 'Single-slice'}</strong> DICOM</p>
            <p>Total Files: ${data.total_files}</p>
            <p>DICOM Files: ${data.dicom_files}</p>
            <p>Total Slices: ${data.total_slices}</p>
            <hr class="border-light">
            <h6>DICOM Metadata</h6>
            <p>Modality: ${data.modality}</p>
            <p>Image Size: ${data.rows} × ${data.columns} pixels</p>
            <p>Bits Allocated: ${data.bits_allocated}</p>
            <p>Samples per Pixel: ${data.samples_per_pixel}</p>
            ${data.warning ? `<p class="text-warning">${data.warning}</p>` : ''}
            <hr class="border-light">
            <p class="small text-muted">File path: ${data.file_path}</p>
          </div>
        `;
      } catch (error) {
        // Hide spinner
        spinner.style.display = 'none';
        
        console.error('Error checking dataset structure:', error);
        infoDiv.innerHTML = `
          <div class="card bg-danger text-light p-3">
            <h5>Error</h5>
            <p>${error.message}</p>
          </div>
        `;
      }
    });
  }
}); 