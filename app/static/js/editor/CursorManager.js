export function CursorManager(imageManager) {
    let activeCursor = null;
    function getOptionsElement() {
        const wrapper = document.createElement("div");
        const title = document.createElement("h3");
        title.textContent = "Cursor Options";
        wrapper.appendChild(title);
        // Color Picker
        const label = document.createElement("label");
        label.textContent = "Color: ";
        const input = document.createElement("input");
        input.type = "color";
        input.value = this.color;
        input.oninput = (e) => {
          this.color = e.target.value;
        };
        label.appendChild(input);
        wrapper.appendChild(label);
      
        // "Log Regions" Button
        const button = document.createElement("button");
        button.textContent = "ConsoleLog Regions";
        button.style.marginLeft = "10px";
        button.onclick = () => {
          const regions = imageManager.getRegions();
          console.log("Current Regions:", regions);
        };
        wrapper.appendChild(button);
      
        return wrapper;
      }
    function hexToRGBA(hex, alpha) {
        const r = parseInt(hex.slice(1, 3), 16);
        const g = parseInt(hex.slice(3, 5), 16);
        const b = parseInt(hex.slice(5, 7), 16);
        return `rgba(${r},${g},${b},${alpha})`;
    }
  
    const cursors = [
      {
        name: "Selection",
        getOptionsElement,
        onMouseDown: (e) => {
          console.log("Selection tool - down");
        },
        onMouseMove: (e) => {},
        onMouseUp: (e) => {},
      },
      {
        name: "Freehand",
        getOptionsElement,
        color: "#ff0000",
        points: [],
        drawing: false,
        onMouseDown(e) {
          this.drawing = true;
          this.points = [{ x: e.offsetX, y: e.offsetY }];
          const ctx = imageManager.getContext();
          ctx.beginPath();
          ctx.moveTo(e.offsetX, e.offsetY);
        },
        onMouseMove(e) {
          if (!this.drawing) return;
          this.points.push({ x: e.offsetX, y: e.offsetY });
          const ctx = imageManager.getContext();
          ctx.lineTo(e.offsetX, e.offsetY);
          ctx.strokeStyle = this.color;
          ctx.stroke();
        },
        onMouseUp(e) {
          if (!this.drawing) return;
          this.drawing = false;
          const ctx = imageManager.getContext();

          ctx.lineTo(this.points[0].x, this.points[0].y);
          ctx.stroke();
          ctx.fillStyle = hexToRGBA(this.color, 0.2);
          ctx.fill();
          ctx.closePath();
  
          imageManager.addRegion({
            type: "curve",
            points: [...this.points, this.points[0]], // close curve in memory
            color: this.color,
            });
          },
      },
      {
        name: "drawRect",
        getOptionsElement,
        color: "#00aa00",
        start: null,
        onMouseDown(e) {
          this.start = { x: e.offsetX, y: e.offsetY };
        },
        onMouseMove(e) {},
        onMouseUp(e) {
          const end = { x: e.offsetX, y: e.offsetY };
          const x = Math.min(this.start.x, end.x);
          const y = Math.min(this.start.y, end.y);
          const width = Math.abs(end.x - this.start.x);
          const height = Math.abs(end.y - this.start.y);
          const ctx = imageManager.getContext();
          ctx.strokeStyle = this.color;
          ctx.strokeRect(x, y, width, height);
          imageManager.addRegion({
            type: "rect",
            x,
            y,
            width,
            height,
            color: this.color,
          });
        },
      },
      {
        name: "Eraser",
        getOptionsElement,
        size: 20,
        erasing: false,
        onMouseDown(e) {
          this.erasing = true;
          const ctx = imageManager.getContext();
          ctx.save();
          ctx.globalCompositeOperation = 'destination-out';
          ctx.beginPath();
          ctx.arc(e.offsetX, e.offsetY, this.size, 0, 2 * Math.PI);
          ctx.fill();
          ctx.restore();
        },
        onMouseMove(e) {
          if (!this.erasing) return;
          const ctx = imageManager.getContext();
          ctx.save();
          ctx.globalCompositeOperation = 'destination-out';
          ctx.beginPath();
          ctx.arc(e.offsetX, e.offsetY, this.size, 0, 2 * Math.PI);
          ctx.fill();
          ctx.restore();
        },
        onMouseUp(e) {
          this.erasing = false;
        },
      },
    ];
  
    function setActiveTool(name) {
      activeCursor = cursors.find((c) => c.name === name);
    }
  
    function bindCanvas(canvas) {
      canvas.addEventListener("mousedown", (e) => {
        activeCursor?.onMouseDown?.(e);
      });
      canvas.addEventListener("mousemove", (e) => {
        activeCursor?.onMouseMove?.(e);
      });
      canvas.addEventListener("mouseup", (e) => {
        activeCursor?.onMouseUp?.(e);
      });
    }
  
    function getElement() {
        const container = document.createElement("div");
        container.className = "cursor-toolbar";
      
        const buttonsDiv = document.createElement("div");
        const optionsDiv = document.createElement("div");
        optionsDiv.className = "cursor-options";
      
        cursors.forEach((cursor) => {
          const btn = document.createElement("button");
          btn.textContent = cursor.name;
          btn.onclick = () => {
            setActiveTool(cursor.name);
            optionsDiv.innerHTML = ""; // clear old options
            const optionsEl = cursor.getOptionsElement?.();
            if (optionsEl) optionsDiv.appendChild(optionsEl);
          };
          buttonsDiv.appendChild(btn);
        });
      
        container.appendChild(buttonsDiv);
        container.appendChild(optionsDiv);
        return container;
      }
  
    return {
      getElement,
      bindCanvas,
      setActiveTool,
      getRegions: () => imageManager.getRegions(),
    };
  }