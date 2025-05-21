/* static/js/editor/ImageManager.js */
export class ImageManager {
  constructor({ canvasId, prevId, nextId, sliderId, currentIndexId, fileIds, urlTemplate }) {
    this.fileIds = fileIds;
    this.idx = 0;
    this.total = fileIds.length;
    this.urlTemplate = urlTemplate;

    this.canvas = document.getElementById(canvasId);
    this.currentIndexEl = document.getElementById(currentIndexId);
    this.slider = document.getElementById(sliderId);
    this.prevBtn = document.getElementById(prevId);
    this.nextBtn = document.getElementById(nextId);

    this.bindEvents();
    this.updateImage();
  }

  loadImageToCanvas(imageUrl) {
    const img = new Image();
    img.onload = () => {
      const wrapper = this.canvas.parentElement;
      wrapper.style.width = img.width + 'px';
      wrapper.style.height = img.height + 'px';

      this.canvas.width = img.width;
      this.canvas.height = img.height;
      this.canvas.style.width = img.width + 'px';
      this.canvas.style.height = img.height + 'px';

      const ctx = this.canvas.getContext('2d');
      ctx.clearRect(0, 0, img.width, img.height);
      ctx.drawImage(img, 0, 0);
    };
    img.onerror = () => console.error('Failed to load image:', imageUrl);
    img.src = imageUrl;
  }

  updateImage() {
    const fileId = this.fileIds[this.idx];
    const url = this.urlTemplate.replace('0', fileId) + `?t=${Date.now()}`;
    this.currentIndexEl.textContent = this.idx + 1;
    this.slider.value = this.idx + 1;
    this.loadImageToCanvas(url);
  }

  bindEvents() {
    this.prevBtn.addEventListener('click', () => {
      this.idx = (this.idx - 1 + this.total) % this.total;
      this.updateImage();
    });

    this.nextBtn.addEventListener('click', () => {
      this.idx = (this.idx + 1) % this.total;
      this.updateImage();
    });

    this.slider.addEventListener('input', () => {
      this.idx = +this.slider.value - 1;
      this.updateImage();
    });
  }
}
