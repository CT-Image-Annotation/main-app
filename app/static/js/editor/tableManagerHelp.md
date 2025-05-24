# Annotations Table Manager - Function Documentation

## Overview
The `AnnotationsTableManager` is a comprehensive JavaScript class for managing annotation tables with full CRUD (Create, Read, Update, Delete) operations. It provides an intuitive interface for managing medical image annotations or any similar tabular data.

## Constructor

### `new AnnotationsTableManager(options)`
Creates a new instance of the annotations table manager.

**Parameters:**
- `options` (Object): Configuration options
  - `tableId` (string): ID of the table element (default: 'annotations-table')
  - `tbodyId` (string): ID of the table body element (default: 'annotations-tbody')
  - `addButtonId` (string): ID of the add button (default: 'add-annotation')
  - `counterId` (string): ID of the counter element (default: 'annotation-count')
  - `initialCounter` (number): Starting counter value (default: 0)
  - `callbacks` (Object): Event callbacks (see Callbacks section)

**Example:**
```javascript
const annotationManager = new AnnotationsTableManager({
    tableId: 'my-annotations-table',
    callbacks: {
        onAdd: (data, row) => console.log('Added:', data),
        onEdit: (data, row) => console.log('Edited:', data),
        onDelete: (data) => console.log('Deleted:', data)
    }
});
```

---

## Core CRUD Functions

### `addAnnotation(data)`
Adds a new annotation to the table with optional predefined data.

**Parameters:**
- `data` (Object, optional): Annotation data
  - `id` (number): Unique identifier
  - `color` (string): Hex color code
  - `label` (string): Annotation label

**Returns:** HTMLElement - The created table row

**Example:**
```javascript
// Add with default values
const row1 = annotationManager.addAnnotation();

// Add with specific data
const row2 = annotationManager.addAnnotation({
    id: 5,
    color: '#ff0000',
    label: 'Important Area'
});
```

### `deleteAnnotation(row, skipConfirmation)`
Removes an annotation from the table.

**Parameters:**
- `row` (HTMLElement): The table row to delete
- `skipConfirmation` (boolean): Skip confirmation dialog (default: false)

**Example:**
```javascript
const row = document.querySelector('tr[data-annotation-id="3"]');
annotationManager.deleteAnnotation(row, true); // Skip confirmation
```

### `toggleEditMode(row)`
Switches a table row between view and edit modes.

**Parameters:**
- `row` (HTMLElement): The table row to toggle

**Example:**
```javascript
const row = document.querySelector('tr[data-annotation-id="1"]');
annotationManager.toggleEditMode(row);
```

---

## Data Management Functions

### `getAnnotationData(row)`
Extracts annotation data from a table row.

**Parameters:**
- `row` (HTMLElement): The table row

**Returns:** Object with properties: `{id, color, label}`

**Example:**
```javascript
const row = document.querySelector('tr[data-annotation-id="2"]');
const data = annotationManager.getAnnotationData(row);
console.log(data); // {id: 2, color: "#00ff00", label: "Healthy Tissue"}
```

### `getAllAnnotations()`
Retrieves data for all annotations in the table.

**Returns:** Array of annotation objects

**Example:**
```javascript
const allAnnotations = annotationManager.getAllAnnotations();
console.log(allAnnotations);
// [{id: 1, color: "#ff0000", label: "Tumor"}, ...]
```

### `loadAnnotations(annotations, clearExisting)`
Loads multiple annotations into the table.

**Parameters:**
- `annotations` (Array): Array of annotation objects
- `clearExisting` (boolean): Clear existing data first (default: true)

**Example:**
```javascript
const annotations = [
    {id: 1, color: '#ff0000', label: 'Tumor'},
    {id: 2, color: '#00ff00', label: 'Healthy Tissue'}
];
annotationManager.loadAnnotations(annotations);
```

### `clearAllAnnotations()`
Removes all annotations from the table and resets the counter.

**Example:**
```javascript
annotationManager.clearAllAnnotations();
```

---

## Color Management Functions

### `openColorPicker(colorPreview)`
Opens a color picker dialog for changing annotation colors.

**Parameters:**
- `colorPreview` (HTMLElement): The color preview element

**Usage:** Automatically called when user clicks on color swatches

### `generateRandomColor()`
Generates a random hex color code.

**Returns:** String - Random hex color (e.g., "#a3b2c1")

**Example:**
```javascript
const randomColor = annotationManager.generateRandomColor();
console.log(randomColor); // "#7f3a98"
```

### `rgbToHex(rgb)`
Converts RGB color string to hex format.

**Parameters:**
- `rgb` (string): RGB color string (e.g., "rgb(255, 0, 0)")

**Returns:** String - Hex color code

**Example:**
```javascript
const hex = annotationManager.rgbToHex("rgb(255, 0, 0)");
console.log(hex); // "#ff0000"
```

---

## Search and Filter Functions

### `searchAnnotations(searchTerm)`
Searches annotations by label text.

**Parameters:**
- `searchTerm` (string): Text to search for

**Returns:** Array of matching annotation objects

**Example:**
```javascript
const matches = annotationManager.searchAnnotations("tumor");
console.log(matches); // All annotations with "tumor" in the label
```

### `highlightSearch(searchTerm)`
Visually highlights table rows that match the search term.

**Parameters:**
- `searchTerm` (string): Text to search and highlight

**Example:**
```javascript
annotationManager.highlightSearch("tissue");
// Highlights all rows containing "tissue" in the label
```

### `sortAnnotations(field, ascending)`
Sorts the table by a specified field.

**Parameters:**
- `field` (string): Field to sort by ('id', 'label', 'color')
- `ascending` (boolean): Sort direction (default: true)

**Example:**
```javascript
// Sort by label A-Z
annotationManager.sortAnnotations('label', true);

// Sort by ID descending
annotationManager.sortAnnotations('id', false);
```

---

## Import/Export Functions

### `exportToJSON()`
Exports all annotations to JSON format.

**Returns:** String - JSON representation of all annotations

**Example:**
```javascript
const jsonData = annotationManager.exportToJSON();
console.log(jsonData);
// Pretty-printed JSON string of all annotations
```

### `importFromJSON(jsonString)`
Imports annotations from JSON string.

**Parameters:**
- `jsonString` (string): JSON string of annotations

**Throws:** Error if JSON is invalid

**Example:**
```javascript
const jsonData = '[{"id":1,"color":"#ff0000","label":"Test"}]';
try {
    annotationManager.importFromJSON(jsonData);
} catch (error) {
    console.error('Import failed:', error.message);
}
```

---

## Utility Functions

### `updateAnnotationCount()`
Updates the display counter showing total number of annotations.

**Usage:** Automatically called after add/delete operations

### `createAnnotationRow(data)`
Creates a new table row element with annotation data.

**Parameters:**
- `data` (Object): Annotation data `{id, color, label}`

**Returns:** HTMLElement - The created table row

**Example:**
```javascript
const rowElement = annotationManager.createAnnotationRow({
    id: 10,
    color: '#blue',
    label: 'New annotation'
});
```

---

## Event Handling

### `setupEventListeners()`
Initializes all event listeners for table interactions.

**Usage:** Automatically called during initialization

### `handleTableClicks(e)`
Handles all click events within the table using event delegation.

**Parameters:**
- `e` (Event): The click event

### `handleKeyPress(e)`
Handles keyboard events for improved user experience.

**Parameters:**
- `e` (Event): The keypress event

---

## Callbacks

The manager supports several callback functions for custom event handling:

### `onAdd(data, row)`
Called when a new annotation is added.
- `data`: The annotation data object
- `row`: The created table row element

### `onEdit(data, row)`
Called when an annotation is edited and saved.
- `data`: The updated annotation data
- `row`: The table row element

### `onDelete(data)`
Called when an annotation is deleted.
- `data`: The deleted annotation data

### `onColorChange(data, row)`
Called when an annotation's color is changed.
- `data`: The annotation data with new color
- `row`: The table row element

**Example Usage:**
```javascript
const annotationManager = new AnnotationsTableManager({
    callbacks: {
        onAdd: (data, row) => {
            // Send to server
            fetch('/api/annotations', {
                method: 'POST',
                body: JSON.stringify(data)
            });
        },
        onEdit: (data, row) => {
            // Update server
            fetch(`/api/annotations/${data.id}`, {
                method: 'PUT',
                body: JSON.stringify(data)
            });
        },
        onDelete: (data) => {
            // Delete from server
            fetch(`/api/annotations/${data.id}`, {
                method: 'DELETE'
            });
        }
    }
});
```

---

## Usage Examples

### Basic Setup
```javascript
// Initialize the manager
const manager = new AnnotationsTableManager();

// Add some annotations
manager.addAnnotation({color: '#ff0000', label: 'Tumor'});
manager.addAnnotation({color: '#00ff00', label: 'Healthy'});
```

### Advanced Setup with Callbacks
```javascript
const manager = new AnnotationsTableManager({
    callbacks: {
        onAdd: (data) => saveToServer(data),
        onEdit: (data) => updateOnServer(data),
        onDelete: (data) => deleteFromServer(data)
    }
});
```

### Data Operations
```javascript
// Export current annotations
const backup = manager.exportToJSON();

// Clear and reload
manager.clearAllAnnotations();
manager.importFromJSON(backup);

// Search and sort
const results = manager.searchAnnotations('tumor');
manager.sortAnnotations('label', true);
```