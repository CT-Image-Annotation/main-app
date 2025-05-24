# Simple Annotations Table - Function Documentation

## Overview
The `SimpleAnnotationsTable` class provides a lightweight table with clickable rows, color pickers, and row selection functionality. It's designed specifically for annotation management with color-based selections.

## Constructor

### `new SimpleAnnotationsTable(options)`
Creates a new instance of the simple annotations table.

**Parameters:**
- `options` (Object): Configuration options
  - `tableId` (string): ID of the table element (default: 'annotations-table')
  - `tbodyId` (string): ID of the table body element (default: 'annotations-tbody')
  - `onRowSelect` (function): Callback when a row is selected
  - `onColorChange` (function): Callback when a color is changed
  - `onRowDelete` (function): Callback when a row is deleted

**Example:**
```javascript
const table = new SimpleAnnotationsTable({
    onRowSelect: function(rowData) {
        console.log('Selected:', rowData.color);
        return rowData.color;
    },
    onColorChange: function(rowData, row) {
        console.log('Color changed to:', rowData.color);
    }
});
```

---

## Core Functions

### `selectRow(row)`
Selects a table row and highlights it. Triggers the `onRowSelect` callback.

**Parameters:**
- `row` (HTMLElement): The table row element to select

**Returns:** Object with row data `{id, color, label}`

**Example:**
```javascript
const row = document.querySelector('tr[data-id="1"]');
const selectedData = table.selectRow(row);
console.log(selectedData.color); // "#ff0000"
```

### `getSelectedColor()`
Returns the hex color of the currently selected row.

**Returns:** String - Hex color code or null if no row selected

**Example:**
```javascript
const color = table.getSelectedColor();
console.log(color); // "#ff0000" or null
```

### `getSelectedRowData()`
Returns complete data of the currently selected row.

**Returns:** Object `{id, color, label}` or null if no row selected

**Example:**
```javascript
const data = table.getSelectedRowData();
if (data) {
    console.log(`ID: ${data.id}, Color: ${data.color}, Label: ${data.label}`);
}
```

### `clearSelection()`
Removes the current row selection and highlighting.

**Example:**
```javascript
table.clearSelection();
```

---

## Row Management Functions

### `addRow(data)`
Adds a new row to the table.

**Parameters:**
- `data` (Object): Row data
  - `id` (string/number): Unique identifier
  - `color` (string): Hex color code
  - `label` (string): Annotation label

**Returns:** HTMLElement - The created row

**Example:**
```javascript
const newRow = table.addRow({
    id: 4,
    color: '#ff00ff',
    label: 'New Annotation'
});
```

### `deleteRow(row)`
Deletes a row from the table. Triggers the `onRowDelete` callback.

**Parameters:**
- `row` (HTMLElement): The table row element to delete

**Example:**
```javascript
const row = document.querySelector('tr[data-id="2"]');
table.deleteRow(row);
```

### `selectRowById(id)`
Selects a row by its ID.

**Parameters:**
- `id` (string/number): The row ID to select

**Example:**
```javascript
table.selectRowById(3); // Selects row with ID 3
```

### `updateRowColor(id, color)`
Updates the color of a specific row.

**Parameters:**
- `id` (string/number): Row ID
- `color` (string): New hex color

**Example:**
```javascript
table.updateRowColor(1, '#00ffff'); // Changes row 1 color to cyan
```

---

## Data Functions

### `getRowData(row)`
Extracts data from a table row element.

**Parameters:**
- `row` (HTMLElement): The table row element

**Returns:** Object `{id, color, label}`

**Example:**
```javascript
const row = document.querySelector('tr[data-id="1"]');
const data = table.getRowData(row);
console.log(data); // {id: "1", color: "#ff0000", label: "Tumor"}
```

### `getAllRows()`
Gets data for all rows in the table.

**Returns:** Array of row data objects

**Example:**
```javascript
const allRows = table.getAllRows();
console.log(allRows);
// [{id: "1", color: "#ff0000", label: "Tumor"}, ...]
```

---

## Color Functions

### `openColorPicker(colorBox, row)`
Opens a color picker for changing row colors. Triggers the `onColorChange` callback.

**Parameters:**
- `colorBox` (HTMLElement): The color box element
- `row` (HTMLElement): The table row element

**Usage:** Automatically called when user clicks on color boxes

### `rgbToHex(rgb)`
Converts RGB color string to hex format.

**Parameters:**
- `rgb` (string): RGB color string (e.g., "rgb(255, 0, 0)")

**Returns:** String - Hex color code

**Example:**
```javascript
const hex = table.rgbToHex("rgb(255, 0, 0)");
console.log(hex); // "#ff0000"
```

---

## Callback Functions

### `onRowSelect(rowData)`
Called when a row is clicked and selected.

**Parameters:**
- `rowData` (Object): Selected row data `{id, color, label}`

**Returns:** Should return the color value for convenience

**Example:**
```javascript
onRowSelect: function(rowData) {
    console.log('Selected annotation:', rowData.label);
    console.log('Color to use:', rowData.color);
    
    // Update your drawing tool color
    document.getElementById('brush-color').value = rowData.color;
    
    return rowData.color;
}
```

### `onColorChange(rowData, row)`
Called when a row's color is changed via the color picker.

**Parameters:**
- `rowData` (Object): Updated row data with new color
- `row` (HTMLElement): The table row element

**Example:**
```javascript
onColorChange: function(rowData, row) {
    console.log('Color changed to:', rowData.color);
    
    // Save to server or update other UI elements
    saveAnnotationColor(rowData.id, rowData.color);
}
```

### `onRowDelete(rowData)`
Called when a row is deleted.

**Parameters:**
- `rowData` (Object): Deleted row data

**Example:**
```javascript
onRowDelete: function(rowData) {
    console.log('Deleted annotation:', rowData.label);
    
    // Remove from server
    deleteAnnotationFromServer(rowData.id);
}
```

---

## Global Helper Functions

The HTML page also includes these global functions for easy access:

### `getSelectedAnnotationColor()`
Returns the currently selected annotation color.

**Example:**
```javascript
const currentColor = getSelectedAnnotationColor();
if (currentColor) {
    console.log('Current color:', currentColor);
}
```

### `getSelectedAnnotationData()`
Returns the currently selected annotation data.

**Example:**
```javascript
const selectedData = getSelectedAnnotationData();
if (selectedData) {
    console.log('Selected:', selectedData);
}
```

### `addNewAnnotation(id, color, label)`
Adds a new annotation to the table.

**Example:**
```javascript
addNewAnnotation(5, '#ffff00', 'Yellow Area');
```

### `selectAnnotationById(id)`
Selects an annotation by ID.

**Example:**
```javascript
selectAnnotationById(2); // Selects annotation with ID 2
```

---

## Usage Examples

### Basic Setup
```javascript
// Initialize the table
const table = new SimpleAnnotationsTable({
    onRowSelect: function(rowData) {
        console.log('Selected color:', rowData.color);
        return rowData.color;
    }
});
```

### Integration with Drawing Tools
```javascript
const table = new SimpleAnnotationsTable({
    onRowSelect: function(rowData) {
        // Update brush color when annotation is selected
        const brushColor = document.getElementById('brush-color');
        if (brushColor) {
            brushColor.value = rowData.color;
        }
        
        console.log('Now drawing with color:', rowData.color);
        return rowData.color;
    },
    onColorChange: function(rowData) {
        // Update brush color if this row is currently selected
        if (table.selectedRowId === rowData.id) {
            const brushColor = document.getElementById('brush-color');
            if (brushColor) {
                brushColor.value = rowData.color;
            }
        }
    }
});
```

### Getting Selected Color for Use
```javascript
// When user starts drawing, get the selected color
function startDrawing() {
    const selectedColor = getSelectedAnnotationColor();
    if (selectedColor) {
        // Use this color for drawing
        setDrawingColor(selectedColor);
    } else {
        alert('Please select an annotation first');
    }
}
```

---

## Key Features

1. **Clickable Rows**: Click any row to select it and get its color
2. **Color Pickers**: Click color boxes to change colors with a native color picker
3. **Row Highlighting**: Selected rows are visually highlighted with blue accent
4. **Delete Functionality**: Each row has a delete button
5. **Color Return**: Row selection returns the hex color value for immediate use
6. **Event Callbacks**: Customizable callbacks for all major actions
7. **Simple API**: Easy-to-use functions for common operations