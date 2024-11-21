import { Map, View } from 'ol';
import TileLayer from 'ol/layer/Tile';
import VectorLayer from 'ol/layer/Vector';
import VectorSource from 'ol/source/Vector';
import GeoJSON from 'ol/format/GeoJSON';
import OSM from 'ol/source/OSM';
import { fromLonLat, toLonLat } from 'ol/proj';
import { Point, LineString } from 'ol/geom';
import Feature from 'ol/Feature';
import { Style, Circle, Stroke } from 'ol/style';

// Initialize map
const map = new Map({
  target: 'map',
  layers: [
    new TileLayer({
      source: new OSM(),
    }),
  ],
  view: new View({
    center: fromLonLat([0, 0]),
    zoom: 2,
  }),
});

// Layers
const layerSource = new VectorSource();
const layerVector = new VectorLayer({
  source: layerSource,
  style: new Style({
    stroke: new Stroke({ color: 'blue', width: 2 }),
  }),
});
map.addLayer(layerVector);

const lineSource = new VectorSource();
const lineLayer = new VectorLayer({
  source: lineSource,
  style: new Style({
    stroke: new Stroke({ color: 'red', width: 2 }),
  }),
});
map.addLayer(lineLayer);

// DOM Elements
const fileInput = document.getElementById('fileInput');
const uploadButton = document.getElementById('uploadButton');
const georeferenceButton = document.getElementById('georeferenceButton');
const layersList = document.getElementById('layersList');
const customLabel = document.querySelector('.custom-file-input');

// Variables
let isDrawingLine = false;
let currentLine = [];
let matchedLines = [];

// Update file input label
fileInput.addEventListener('change', () => {
  const fileName = fileInput.files[0]?.name || 'Choose File';
  customLabel.textContent = fileName;
});

// Upload and render GeoJSON
uploadButton.addEventListener('click', async () => {
  if (!fileInput.files.length) {
    alert('Please select a PDF file to upload.');
    return;
  }

  const formData = new FormData();
  formData.append('file', fileInput.files[0]);

  // Indicate processing
  const processingMsg = document.createElement('li');
  processingMsg.textContent = 'Processing...';
  processingMsg.style.color = 'blue';
  layersList.appendChild(processingMsg);

  try {
    const response = await fetch('http://127.0.0.1:5000/upload', {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Error: ${response.statusText}`);
    }

    const geojson = await response.json();

    // Remove "Processing..." message
    layersList.removeChild(processingMsg);

    // Add GeoJSON to map
    const vectorSource = new VectorSource({
      features: new GeoJSON().readFeatures(geojson, {
        dataProjection: 'EPSG:4326',
        featureProjection: 'EPSG:3857',
      }),
    });

    layerSource.clear();
    layerSource.addFeatures(vectorSource.getFeatures());

    // Add layer to sidebar
    const layerItem = document.createElement('li');
    layerItem.textContent = fileInput.files[0].name;
    layerItem.addEventListener('click', () => {
      map.getView().fit(layerSource.getExtent(), { padding: [50, 50, 50, 50] });
    });
    layersList.appendChild(layerItem);
  } catch (error) {
    console.error('Error uploading file:', error);
    layersList.removeChild(processingMsg);

    const errorMsg = document.createElement('li');
    errorMsg.textContent = `Error: ${error.message}`;
    errorMsg.style.color = 'red';
    layersList.appendChild(errorMsg);
  }
});

// Start drawing lines for georeferencing
map.on('click', (event) => {
  if (!isDrawingLine) return;

  const coords = toLonLat(event.coordinate);
  currentLine.push(coords);

  // Draw the line dynamically
  if (currentLine.length > 1) {
    const lineFeature = new Feature(new LineString(currentLine));
    lineSource.clear();
    lineSource.addFeature(lineFeature);
  }
});

// Finish drawing the line
map.on('dblclick', (event) => {
  if (!isDrawingLine) return;

  event.preventDefault();

  if (currentLine.length < 2) {
    alert('A line must have at least two points.');
    return;
  }

  matchedLines.push([...currentLine]);
  currentLine = [];
  lineSource.clear();

  if (matchedLines.length >= 2) {
    isDrawingLine = false;
    alert('Lines selected. Ready to georeference.');
  }
});

// Trigger georeferencing
georeferenceButton.addEventListener('click', () => {
  if (matchedLines.length < 2) {
    alert('Please draw at least two pairs of lines.');
    isDrawingLine = true;
    alert('Draw two pairs of corresponding lines: one for the map, one for the layer.');
  } else {
    applyLineBasedGeoreferencing();
  }
});

// Georeference function
function applyLineBasedGeoreferencing() {
  const mapLine = matchedLines[0];
  const layerLine = matchedLines[1];

  const transformation = computeLineTransformation(layerLine, mapLine);

  // Apply transformation to layer features
  layerSource.getFeatures().forEach((feature) => {
    const geometry = feature.getGeometry();
    geometry.applyTransform((coords) => {
      const [x, y] = coords;
      const transformedCoords = applyLineTransformation(transformation, x, y);
      coords[0] = transformedCoords[0];
      coords[1] = transformedCoords[1];
    });
  });

  layerSource.refresh();
  alert('Georeferencing applied.');
}

// Compute transformation based on lines
function computeLineTransformation(sourceLine, targetLine) {
  const [x1, y1] = sourceLine[0];
  const [x2, y2] = sourceLine[1];
  const [x1Prime, y1Prime] = targetLine[0];
  const [x2Prime, y2Prime] = targetLine[1];

  const angleSource = Math.atan2(y2 - y1, x2 - x1);
  const angleTarget = Math.atan2(y2Prime - y1Prime, x2Prime - x1Prime);
  const rotation = angleTarget - angleSource;

  const scale =
    Math.sqrt((x2Prime - x1Prime) ** 2 + (y2Prime - y1Prime) ** 2) /
    Math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2);

  const translation = [
    x1Prime - scale * (x1 * Math.cos(rotation) - y1 * Math.sin(rotation)),
    y1Prime - scale * (x1 * Math.sin(rotation) + y1 * Math.cos(rotation)),
  ];

  return { scale, rotation, translation };
}

// Apply line-based transformation
function applyLineTransformation({ scale, rotation, translation }, x, y) {
  const [tx, ty] = translation;
  const newX = scale * (x * Math.cos(rotation) - y * Math.sin(rotation)) + tx;
  const newY = scale * (x * Math.sin(rotation) + y * Math.cos(rotation)) + ty;
  return [newX, newY];
}
