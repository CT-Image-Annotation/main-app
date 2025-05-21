export function CursorManager(imageManager) {
  let activeTool = null;
  const canvas = imageManager.getCanvas();
  const ctx = imageManager.getContext();

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
        ctx.strokeStyle = 'cyan';
        ctx.fillRect(x, y, w, h);
        ctx.strokeRect(x, y, w, h);
      }
      else if (region.type === 'mask') {
        const w = canvas.width;
        ctx.fillStyle = region.color ? hexToRGBA(region.color, 0.3) : 'rgba(255,0,0,0.3)';
        for (let i = 0; i < region.mask.length; i++) {
          if (region.mask[i]) {
            const px = i % w;
            const py = Math.floor(i / w);
            ctx.fillRect(px, py, 1, 1);
          }
        }
      }
    });
  }

  // Convert hex color to rgba string
  function hexToRGBA(hex, alpha) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r},${g},${b},${alpha})`;
  }

  const tools = [
    {
      name: 'drawRect',
      startX: null,
      startY: null,
      onMouseDown(e) {
        this.startX = e.offsetX;
        this.startY = e.offsetY;
      },
      onMouseMove(e) {
        if (this.startX === null) return;
        redrawAnnotations();
        const x = Math.min(this.startX, e.offsetX);
        const y = Math.min(this.startY, e.offsetY);
        const w = Math.abs(e.offsetX - this.startX);
        const h = Math.abs(e.offsetY - this.startY);
        ctx.fillStyle = 'rgba(0,255,255,0.3)';
        ctx.strokeStyle = 'cyan';
        ctx.fillRect(x, y, w, h);
        ctx.strokeRect(x, y, w, h);
      },
      onMouseUp(e) {
        if (this.startX === null) return;
        const x1 = this.startX, y1 = this.startY;
        const x2 = e.offsetX, y2 = e.offsetY;
        const x = Math.min(x1, x2);
        const y = Math.min(y1, y2);
        const w = Math.abs(x2 - x1);
        const h = Math.abs(y2 - y1);
        imageManager.addRegion({ type: 'box', x1: x, y1: y, x2: x + w, y2: y + h });
        this.startX = this.startY = null;
        redrawAnnotations();
      }
    },
    {
      name: 'Freehand',
      color: '#ff0000',
      points: [],
      drawing: false,
      onMouseDown(e) {
        this.drawing = true;
        this.points = [{ x: e.offsetX, y: e.offsetY }];
      },
      onMouseMove(e) {
        if (!this.drawing) return;
        this.points.push({ x: e.offsetX, y: e.offsetY });
        redrawAnnotations();
        ctx.beginPath();
        ctx.moveTo(this.points[0].x, this.points[0].y);
        this.points.forEach((p, i) => { if (i > 0) ctx.lineTo(p.x, p.y); });
        ctx.strokeStyle = this.color;
        ctx.stroke();
      },
      onMouseUp(e) {
        if (!this.drawing) return;
        this.drawing = false;
        // Create mask
        const off = document.createElement('canvas'); off.width = canvas.width; off.height = canvas.height;
        const offCtx = off.getContext('2d');
        offCtx.beginPath();
        offCtx.moveTo(this.points[0].x, this.points[0].y);
        this.points.forEach(p => offCtx.lineTo(p.x, p.y));
        offCtx.closePath();
        offCtx.fillStyle = '#fff'; offCtx.fill();
        const data = offCtx.getImageData(0, 0, off.width, off.height).data;
        const mask = new Uint8Array(off.width * off.height);
        for (let i = 0; i < mask.length; i++) mask[i] = data[i*4+3] > 0 ? 1 : 0;
        imageManager.addRegion({ type: 'mask', mask, color: this.color });
        redrawAnnotations();
      }
    },
    {
      name: 'Eraser',
      size: 20,
      onMouseDown(e) {
        const x = e.offsetX, y = e.offsetY;
        const regions = imageManager.getRegions();
        const w = canvas.width;
        // Remove region containing click
        for (let i = regions.length - 1; i >= 0; i--) {
          const r = regions[i]; let inside = false;
          if (r.type === 'box') inside = x >= r.x1 && x <= r.x2 && y >= r.y1 && y <= r.y2;
          else if (r.type === 'mask') inside = r.mask[y*w + x] === 1;
          if (inside) regions.splice(i, 1);
        }
        redrawAnnotations();
      },
      onMouseMove() {},
      onMouseUp() {}
    }
  ];

  function setActiveTool(toolName) {
    const found = tools.find(t => t.name === toolName);
    if (found) activeTool = found;
  }

  function bindCanvas(c) {
    const eventMap = {
      mousedown: 'onMouseDown',
      mousemove: 'onMouseMove',
      mouseup:   'onMouseUp'
    };
    Object.entries(eventMap).forEach(([evt, handler]) => {
      c.addEventListener(evt, e => activeTool?.[handler]?.(e));
    });
  }

  function showOptions(container) { container.innerHTML = ''; }
  function getRegions()     { return imageManager.getRegions(); }

  return { setActiveTool, bindCanvas, showOptions, getRegions };
}
