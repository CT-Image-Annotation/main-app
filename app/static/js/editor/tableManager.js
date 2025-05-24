/**
 * Simple Annotations Table Manager
 * Handles clickable rows, color selection, and row highlighting
 */

class SimpleAnnotationsTable {
    constructor(options = {}) {
        this.tableId = options.tableId || 'annotations-table';
        this.tbodyId = options.tbodyId || 'annotations-tbody';
        this.selectedRowId = null;
        this.onRowSelect = options.onRowSelect || null;
        this.onColorChange = options.onColorChange || null;
        this.onRowDelete = options.onRowDelete || null;
        
        this.init();
    }

    /**
     * Initialize the table manager
     */
    init() {
        this.setupEventListeners();
    }

    /**
     * Set up event listeners for table interactions
     */
    setupEventListeners() {
        const tbody = document.getElementById(this.tbodyId);
        if (!tbody) return;

        // Handle row clicks, color picker clicks, and delete clicks
        tbody.addEventListener('click', (e) => {
            const row = e.target.closest('tr');
            if (!row) return;

            if (e.target.classList.contains('color-box')) {
                // Color box clicked - open color picker
                this.openColorPicker(e.target, row);
            } else if (e.target.closest('.delete-btn')) {
                // Delete button clicked
                this.deleteRow(row);
            } else {
                // Row clicked - select row
                this.selectRow(row);
            }
        });
    }

    /**
     * Select a table row and highlight it
     * @param {HTMLElement} row - The table row element
     */
    selectRow(row) {
        // Remove previous selection
        this.clearSelection();
        
        // Add selection to clicked row
        row.classList.add('selected-row');
        this.selectedRowId = row.getAttribute('data-id');
        
        // Get row data
        const rowData = this.getRowData(row);
        
        // Trigger callback if provided
        if (this.onRowSelect) {
            this.onRowSelect(rowData);
        }
        
        return rowData;
    }

    /**
     * Clear current row selection
     */
    clearSelection() {
        const currentSelected = document.querySelector(`#${this.tbodyId} .selected-row`);
        if (currentSelected) {
            currentSelected.classList.remove('selected-row');
        }
        this.selectedRowId = null;
    }

    /**
     * Get data from a table row
     * @param {HTMLElement} row - The table row element
     * @returns {Object} Row data object
     */
    getRowData(row) {
        const id = row.getAttribute('data-id');
        const colorBox = row.querySelector('.color-box');
        const color = colorBox.style.backgroundColor || colorBox.getAttribute('data-color');
        const label = row.querySelector('.label-text').textContent;
        
        return {
            id: id,
            color: this.rgbToHex(color) || color,
            label: label
        };
    }

    /**
     * Get currently selected row data
     * @returns {Object|null} Selected row data or null if none selected
     */
    getSelectedRowData() {
        if (!this.selectedRowId) return null;
        
        const selectedRow = document.querySelector(`tr[data-id="${this.selectedRowId}"]`);
        return selectedRow ? this.getRowData(selectedRow) : null;
    }

    /**
     * Get selected row color
     * @returns {string|null} Hex color of selected row or null if none selected
     */
    getSelectedColor() {
        const selectedData = this.getSelectedRowData();
        return selectedData ? selectedData.color : null;
    }

    /**
     * Open color picker for a row
     * @param {HTMLElement} colorBox - The color box element
     * @param {HTMLElement} row - The table row element
     */
    openColorPicker(colorBox, row) {
        // Create a temporary color input similar to brush-color
        const colorInput = document.createElement('input');
        colorInput.type = 'color';
        colorInput.value = this.rgbToHex(colorBox.style.backgroundColor) || '#000000';
        
        // Style it exactly like the brush-color input
        colorInput.style.width = '30px';
        colorInput.style.height = '30px';
        colorInput.style.position = 'absolute';
        colorInput.style.border = 'none';
        colorInput.style.borderRadius = '4px';
        colorInput.style.cursor = 'pointer';
        colorInput.style.zIndex = '9999';
        
        // Position it below the color box
        const rect = colorBox.getBoundingClientRect();
        colorInput.style.left = rect.left + 'px';
        colorInput.style.top = (rect.bottom + window.scrollY + 5) + 'px';
        
        // Add to document
        document.body.appendChild(colorInput);
        
        // Handle color changes
        const handleChange = () => {
            const newColor = colorInput.value;
            colorBox.style.backgroundColor = newColor;
            colorBox.setAttribute('data-color', newColor);
            
            // Trigger callback if provided
            if (this.onColorChange) {
                const rowData = this.getRowData(row);
                this.onColorChange(rowData, row);
            }
        };
        
        // Handle cleanup
        const cleanup = () => {
            if (document.body.contains(colorInput)) {
                document.body.removeChild(colorInput);
            }
            document.removeEventListener('click', outsideClick);
        };
        
        const outsideClick = (e) => {
            if (!colorInput.contains(e.target) && e.target !== colorBox) {
                cleanup();
            }
        };
        
        // Add event listeners
        colorInput.addEventListener('change', handleChange);
        colorInput.addEventListener('input', handleChange); // Real-time updates
        colorInput.addEventListener('blur', cleanup); // Remove when focus is lost
        
        // Focus and click the input to open color picker immediately
        colorInput.focus();
        colorInput.click();
        
        // Add outside click listener after a brief delay
        setTimeout(() => {
            document.addEventListener('click', outsideClick);
        }, 100);
    }

    /**
     * Delete a table row
     * @param {HTMLElement} row - The table row element
     */
    deleteRow(row) {
        const rowData = this.getRowData(row);
        
        // Clear selection if this row is selected
        if (this.selectedRowId === rowData.id) {
            this.clearSelection();
        }
        
        // Remove the row
        row.remove();
        
        // Trigger callback if provided
        if (this.onRowDelete) {
            this.onRowDelete(rowData);
        }
    }

    /**
     * Add a new row to the table
     * @param {Object} data - Row data {id, color, label}
     * @returns {HTMLElement} The created row element
     */
    addRow(data) {
        const tbody = document.getElementById(this.tbodyId);
        const row = this.createRow(data);
        tbody.appendChild(row);
        return row;
    }

    /**
     * Create a new table row element
     * @param {Object} data - Row data {id, color, label}
     * @returns {HTMLElement} The created row element
     */
    createRow(data) {
        const row = document.createElement('tr');
        row.setAttribute('data-id', data.id);
        row.style.cursor = 'pointer';
        
        row.innerHTML = `
            <td>${data.id}</td>
            <td>
                <div class="color-box" 
                     style="width: 30px; height: 30px; background-color: ${data.color}; 
                            border: 2px solid #ccc; border-radius: 4px; cursor: pointer; 
                            display: inline-block;" 
                     data-color="${data.color}"
                     title="Click to change color"></div>
            </td>
            <td class="label-text">${data.label}</td>
            <td>
                <button class="btn btn-sm btn-outline-danger delete-btn" title="Delete">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        `;
        
        return row;
    }

    /**
     * Select row by ID
     * @param {string|number} id - Row ID to select
     */
    selectRowById(id) {
        const row = document.querySelector(`tr[data-id="${id}"]`);
        if (row) {
            this.selectRow(row);
        }
    }

    /**
     * Update row color by ID
     * @param {string|number} id - Row ID
     * @param {string} color - New hex color
     */
    updateRowColor(id, color) {
        const row = document.querySelector(`tr[data-id="${id}"]`);
        if (row) {
            const colorBox = row.querySelector('.color-box');
            colorBox.style.backgroundColor = color;
            colorBox.setAttribute('data-color', color);
        }
    }

    /**
     * Get all rows data
     * @returns {Array} Array of row data objects
     */
    getAllRows() {
        const rows = document.querySelectorAll(`#${this.tbodyId} tr`);
        return Array.from(rows).map(row => this.getRowData(row));
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
}

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SimpleAnnotationsTable;
}