// CursorManager.js (uses global Annotorious via createImageAnnotator)

export function CursorManager(imageManager) {
  let activeTool = null;
  const canvas = imageManager.getCanvas();
  const ctx    = imageManager.getContext();
  let anno     = null;

  // Use global Annotorious loaded via <script> tag
  const { Annotorious } = window;

  // Redraw stored regions (boxes and masks)
  function redrawAnnotations() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const regions = imageManager.getRegions();
    regions.forEach(region => {
      if (region.type === 'box') {
        const x = region.x1;
        const y = region.y1;
        const w = region.x2 - region.x1;
        const h = region.y2 - region.y1;
        ctx.fillStyle = 'rgba(0,255,255,0.3)';
        ctx.fillRect(x, y, w, h);
        ctx.strokeStyle = 'cyan';
        ctx.lineWidth   = 2;
        ctx.strokeRect(x, y, w, h);
      }
      // handle other region types if any
    });
  }

  // Disable/enable canvas-based tools when Annotorious is active
  function disableCanvasTools() {
    canvas.style.pointerEvents = 'none';
  }
  function enableCanvasTools() {
    canvas.style.pointerEvents = 'auto';
  }

  // Initialize Annotorious for rectangle drawing using createImageAnnotator
  function initAnnotorious() {
    if (!anno) {
      const imgEl = document.getElementById('annotatable-image');
      anno = Annotorious.createImageAnnotator(imgEl, {
        drawingEnabled: true,
        formatter: null
      });
            // Determine and switch to the rectangle drawing tool
      const available = anno.listDrawingTools();
      console.log('🛠️ Available drawing tools:', available);
      const rect = available.find(t => ['rect','rectangle'].includes(t)) || available[0];
      console.log('🛠️ Selecting drawing tool:', rect);
      anno.setDrawingTool(rect);
      // Listen for newly created annotations
      anno.on('createAnnotation', annotation => {
        const sel = annotation.target.selector.value; // 'xywh=pixel:x,y,w,h'
        const m   = sel.match(/xywh=pixel:(\d+),(\d+),(\d+),(\d+)/);
        if (m) {
          const [ , x, y, w, h ] = m;
          imageManager.addRegion({ type: 'box', x1: Number(x), y1: Number(y), x2: Number(x) + Number(w), y2: Number(y) + Number(h) });
          redrawAnnotations();
        }
        // Remove from Annotorious overlay, since we draw manually
        anno.removeAnnotation(annotation);
      });
    }
  }

  // Destroy Annotorious instance
  function destroyAnnotorious() {
    if (anno) {
      anno.destroy();
      anno = null;
    }
  }

  // Freehand drawing tool definition
  const freehandTool = {
    name: 'Freehand',
    color: '#ff0000',
    points: [],
    onMouseDown(e) {
      this.points = [{ x: e.offsetX, y: e.offsetY }];
    },
    onMouseMove(e) {
      if (!this.points.length) return;
      this.points.push({ x: e.offsetX, y: e.offsetY });
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      redrawAnnotations();
      ctx.strokeStyle = this.color;
      ctx.lineWidth   = 2;
      ctx.beginPath();
      ctx.moveTo(this.points[0].x, this.points[0].y);
      this.points.forEach(p => ctx.lineTo(p.x, p.y));
      ctx.stroke();
    },
    onMouseUp(e) {
      if (!this.points.length) return;
      imageManager.addRegion({ type: 'poly', points: this.points });
      this.points = [];
      redrawAnnotations();
    }
  };

  // Eraser tool definition
  const eraserTool = {
    name: 'Eraser',
    onMouseDown(e) {
      const x = e.offsetX, y = e.offsetY;
      const kept = imageManager.getRegions().filter(r => {
        if (r.type === 'box') {
          return !(x >= r.x1 && x <= r.x2 && y >= r.y1 && y <= r.y2);
        }
        return true;
      });
      if (imageManager.setRegions) imageManager.setRegions(kept);
      redrawAnnotations();
    }
  };

  const tools = [ freehandTool, eraserTool ];

  function setActiveTool(name) {
    activeTool = tools.find(t => t.name === name) || null;
    if (activeTool?.name !== 'Freehand') freehandTool.points = [];
  }

  function bindCanvas(c) {
    const eventMap = { mousedown: 'onMouseDown', mousemove: 'onMouseMove', mouseup: 'onMouseUp' };
    Object.entries(eventMap).forEach(([evt, handler]) => {
      c.addEventListener(evt, e => activeTool?.[handler]?.(e));
    });
  }

  function showOptions(container) {
    container.innerHTML = '';
  }

  function getRegions() {
    return imageManager.getRegions();
  }

  return {
    setActiveTool,
    bindCanvas,
    showOptions,
    getRegions,
    redrawAnnotations,
    disableCanvasTools,
    enableCanvasTools,
    initAnnotorious,
    destroyAnnotorious
  };
}
