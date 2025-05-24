/**
 * Annotations Table Manager
 * A comprehensive JavaScript library for managing annotation tables with CRUD operations
 */

class AnnotationsTableManager {
    constructor(options = {}) {
        this.tableId = options.tableId || 'annotations-table';
        this.tbodyId = options.tbodyId || 'annotations-tbody';
        this.addButtonId = options.addButtonId || 'add-annotation';
        this.counterId = options.counterId || 'annotation-count';
        
        this.annotationCounter = options.initialCounter || 0;
        this.callbacks = options.callbacks || {};
        
        this.init();
    }

    /**
     * Initialize the table manager
     * Sets up event listeners and prepares the table
     */
    init() {
        this.setupEventListeners();
        this.updateAnnotationCount();
        
        // Count existing annotations
        const existingRows = document.querySelectorAll(`#${this.tbodyId} tr`);
        if (existingRows.length > 0) {
            this.annotationCounter = Math.max(...Array.from(existingRows).map(row => 
                parseInt(row.getAttribute('data-annotation-id')) || 0
            ));
        }
    }

    /**
     * Set up all event listeners for table interactions
     */
    setupEventListeners() {
        // Add annotation button
        const addButton = document.getElementById(this.addButtonId);
        if (addButton) {
            addButton.addEventListener('click', () => this.addAnnotation());
        }

        // Delegate events for dynamic elements
        document.addEventListener('click', (e) => this.handleTableClicks(e));
        document.addEventListener('keypress', (e) => this.handleKeyPress(e));
    }

    /**
     * Handle all click events within the table
     * @param {Event} e - The click event
     */
    handleTableClicks(e) {
        if (e.target.closest('.edit-annotation')) {
            this.toggleEditMode(e.target.closest('tr'));
        } else if (e.target.closest('.delete-annotation')) {
            this.deleteAnnotation(e.target.closest('tr'));
        } else if (e.target.classList.contains('color-preview')) {
            this.openColorPicker(e.target);
        }
    }

    /**
     * Handle keyboard events for better UX
     * @param {Event} e - The keypress event
     */
    handleKeyPress(e) {
        if (e.key === 'Enter' && e.target.type === 'text' && !e.target.hasAttribute('readonly')) {
            this.toggleEditMode(e.target.closest('tr'));
        }
    }

    /**
     * Add a new annotation to the table
     * @param {Object} data - Optional data for the new annotation
     * @returns {HTMLElement} The created row element
     */
    addAnnotation(data = {}) {
        this.annotationCounter++;
        
        const annotationData = {
            id: data.id || this.annotationCounter,
            color: data.color || this.generateRandomColor(),
            label: data.label || 'New Annotation'
        };

        const row = this.createAnnotationRow(annotationData);
        const tbody = document.getElementById(this.tbodyId);
        tbody.appendChild(row);
        
        this.updateAnnotationCount();
        
        // Trigger callback if provided
        if (this.callbacks.onAdd) {
            this.callbacks.onAdd(annotationData, row);
        }
        
        return row;
    }

    /**
     * Create a new annotation row element
     * @param {Object} data - Annotation data {id, color, label}
     * @returns {HTMLElement} The created row element
     */
    createAnnotationRow(data) {
        const row = document.createElement('tr');
        row.setAttribute('data-annotation-id', data.id);
        
        row.innerHTML = `
            <td>${data.id}</td>
            <td>
                <div class="d-flex align-items-center gap-2">
                    <div class="color-preview" 
                         style="width: 20px; height: 20px; background-color: ${data.color}; 
                                border-radius: 3px; border: 1px solid #ccc; cursor: pointer;" 
                         title="Click to change color"></div>
                    <small class="text-muted color-hex">${data.color}</small>
                </div>
            </td>
            <td>
                <input type="text" 
                       class="form-control form-control-sm bg-dark text-light border-secondary annotation-label" 
                       value="${data.label}" 
                       readonly>
            </td>
            <td>
                <div class="btn-group-vertical btn-group-sm">
                    <button class="btn btn-outline-warning btn-sm edit-annotation" title="Edit">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-outline-danger btn-sm delete-annotation" title="Delete">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </td>
        `;
        
        return row;
    }

    /**
     * Toggle edit mode for an annotation row
     * @param {HTMLElement} row - The table row element
     */
    toggleEditMode(row) {
        const input = row.querySelector('.annotation-label');
        const editButton = row.querySelector('.edit-annotation');
        const isReadonly = input.hasAttribute('readonly');
        
        if (isReadonly) {
            // Enter edit mode
            input.removeAttribute('readonly');
            input.focus();
            input.select();
            editButton.innerHTML = '<i class="fas fa-save"></i>';
            editButton.classList.remove('btn-outline-warning');
            editButton.classList.add('btn-outline-success');
            editButton.title = 'Save';
        } else {
            // Save and exit edit mode
            input.setAttribute('readonly', true);
            editButton.innerHTML = '<i class="fas fa-edit"></i>';
            editButton.classList.remove('btn-outline-success');
            editButton.classList.add('btn-outline-warning');
            editButton.title = 'Edit';
            
            // Trigger callback if provided
            if (this.callbacks.onEdit) {
                const annotationData = this.getAnnotationData(row);
                this.callbacks.onEdit(annotationData, row);
            }
        }
    }

    /**
     * Delete an annotation from the table
     * @param {HTMLElement} row - The table row element
     * @param {boolean} skipConfirmation - Skip the confirmation dialog
     */
    deleteAnnotation(row, skipConfirmation = false) {
        const shouldDelete = skipConfirmation || confirm('Are you sure you want to delete this annotation?');
        
        if (shouldDelete) {
            const annotationData = this.getAnnotationData(row);
            
            row.remove();
            this.updateAnnotationCount();
            
            // Trigger callback if provided
            if (this.callbacks.onDelete) {
                this.callbacks.onDelete(annotationData);
            }
        }
    }

    /**
     * Open color picker for changing annotation color
     * @param {HTMLElement} colorPreview - The color preview element
     */
    openColorPicker(colorPreview) {
        const input = document.createElement('input');
        input.type = 'color';
        input.value = this.rgbToHex(colorPreview.style.backgroundColor) || '#000000';
        input.style.position = 'absolute';
        input.style.visibility = 'hidden';
        document.body.appendChild(input);
        
        input.addEventListener('change', () => {
            const newColor = input.value;
            colorPreview.style.backgroundColor = newColor;
            
            const hexElement = colorPreview.parentElement.querySelector('.color-hex');
            if (hexElement) {
                hexElement.textContent = newColor;
            }
            
            // Trigger callback if provided
            if (this.callbacks.onColorChange) {
                const row = colorPreview.closest('tr');
                const annotationData = this.getAnnotationData(row);
                this.callbacks.onColorChange(annotationData, row);
            }
            
            document.body.removeChild(input);
        });
        
        input.click();
    }

    /**
     * Get annotation data from a table row
     * @param {HTMLElement} row - The table row element
     * @returns {Object} Annotation data object
     */
    getAnnotationData(row) {
        const id = row.getAttribute('data-annotation-id');
        const colorPreview = row.querySelector('.color-preview');
        const color = this.rgbToHex(colorPreview.style.backgroundColor);
        const label = row.querySelector('.annotation-label').value;
        
        return { id: parseInt(id), color, label };
    }

    /**
     * Get all annotations data from the table
     * @returns {Array} Array of annotation objects
     */
    getAllAnnotations() {
        const rows = document.querySelectorAll(`#${this.tbodyId} tr`);
        return Array.from(rows).map(row => this.getAnnotationData(row));
    }

    /**
     * Load annotations from data array
     * @param {Array} annotations - Array of annotation objects
     * @param {boolean} clearExisting - Clear existing annotations first
     */
    loadAnnotations(annotations, clearExisting = true) {
        if (clearExisting) {
            this.clearAllAnnotations();
        }
        
        annotations.forEach(annotation => {
            this.addAnnotation(annotation);
        });
    }

    /**
     * Clear all annotations from the table
     */
    clearAllAnnotations() {
        const tbody = document.getElementById(this.tbodyId);
        tbody.innerHTML = '';
        this.annotationCounter = 0;
        this.updateAnnotationCount();
    }

    /**
     * Update the annotation counter display
     */
    updateAnnotationCount() {
        const count = document.querySelectorAll(`#${this.tbodyId} tr`).length;
        const counterElement = document.getElementById(this.counterId);
        if (counterElement) {
            counterElement.textContent = count;
        }
    }

    /**
     * Generate a random hex color
     * @returns {string} Random hex color
     */
    generateRandomColor() {
        return '#' + Math.floor(Math.random() * 16777215).toString(16).padStart(6, '0');
    }

    /**
     * Convert RGB color to hex format
     * @param {string} rgb - RGB color string
     * @returns {string} Hex color string
     */
    rgbToHex(rgb) {
        if (!rgb || rgb.indexOf('rgb') === -1) return rgb;
        
        const values = rgb.match(/\d+/g);
        if (!values || values.length < 3) return '#000000';
        
        return '#' + values.slice(0, 3).map(x => {
            const hex = parseInt(x).toString(16);
            return hex.length === 1 ? '0' + hex : hex;
        }).join('');
    }

    /**
     * Export annotations to JSON
     * @returns {string} JSON string of all annotations
     */
    exportToJSON() {
        return JSON.stringify(this.getAllAnnotations(), null, 2);
    }

    /**
     * Import annotations from JSON
     * @param {string} jsonString - JSON string of annotations
     */
    importFromJSON(jsonString) {
        try {
            const annotations = JSON.parse(jsonString);
            this.loadAnnotations(annotations);
        } catch (error) {
            console.error('Error importing annotations:', error);
            throw new Error('Invalid JSON format');
        }
    }

    /**
     * Search annotations by label
     * @param {string} searchTerm - Search term
     * @returns {Array} Matching annotations
     */
    searchAnnotations(searchTerm) {
        const allAnnotations = this.getAllAnnotations();
        return allAnnotations.filter(annotation => 
            annotation.label.toLowerCase().includes(searchTerm.toLowerCase())
        );
    }

    /**
     * Highlight rows that match search criteria
     * @param {string} searchTerm - Search term
     */
    highlightSearch(searchTerm) {
        const rows = document.querySelectorAll(`#${this.tbodyId} tr`);
        rows.forEach(row => {
            const label = row.querySelector('.annotation-label').value;
            if (searchTerm && label.toLowerCase().includes(searchTerm.toLowerCase())) {
                row.style.backgroundColor = 'rgba(255, 255, 0, 0.1)';
            } else {
                row.style.backgroundColor = '';
            }
        });
    }

    /**
     * Sort annotations by specified field
     * @param {string} field - Field to sort by ('id', 'label', 'color')
     * @param {boolean} ascending - Sort direction
     */
    sortAnnotations(field, ascending = true) {
        const tbody = document.getElementById(this.tbodyId);
        const rows = Array.from(tbody.querySelectorAll('tr'));
        
        rows.sort((a, b) => {
            let aVal, bVal;
            
            switch (field) {
                case 'id':
                    aVal = parseInt(a.getAttribute('data-annotation-id'));
                    bVal = parseInt(b.getAttribute('data-annotation-id'));
                    break;
                case 'label':
                    aVal = a.querySelector('.annotation-label').value.toLowerCase();
                    bVal = b.querySelector('.annotation-label').value.toLowerCase();
                    break;
                case 'color':
                    aVal = a.querySelector('.color-hex').textContent;
                    bVal = b.querySelector('.color-hex').textContent;
                    break;
                default:
                    return 0;
            }
            
            if (aVal < bVal) return ascending ? -1 : 1;
            if (aVal > bVal) return ascending ? 1 : -1;
            return 0;
        });
        
        // Re-append sorted rows
        rows.forEach(row => tbody.appendChild(row));
    }
}

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AnnotationsTableManager;
}