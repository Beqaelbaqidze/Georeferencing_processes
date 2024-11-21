import { Map, View } from 'ol';
import TileLayer from 'ol/layer/Tile';
import VectorLayer from 'ol/layer/Vector';
import VectorSource from 'ol/source/Vector';
import GeoJSON from 'ol/format/GeoJSON';
import OSM from 'ol/source/OSM';
import { fromLonLat, toLonLat } from 'ol/proj';
import { Point } from 'ol/geom';
import Feature from 'ol/Feature';
import { Style, Circle, Fill, Stroke } from 'ol/style';

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
    fill: new Fill({ color: 'rgba(0, 0, 255, 0.1)' }),
  }),
});
map.addLayer(layerVector);

const controlPointsSource = new VectorSource();
const controlPointsLayer = new VectorLayer({
  source: controlPointsSource,
  style: new Style({
    image: new Circle({
      radius: 5,
      fill: new Fill({ color: 'red' }),
      stroke: new Stroke({ color: 'black', width: 1 }),
    }),
  }),
});
map.addLayer(controlPointsLayer);

// DOM Elements
const fileInput = document.getElementById('fileInput');
const uploadButton = document.getElementById('uploadButton');
const georeferenceButton = document.getElementById('georeferenceButton');
const layersList = document.getElementById('layersList');
const customLabel = document.querySelector('.custom-file-input');

// Update file input label
fileInput.addEventListener('change', () => {
  const fileName = fileInput.files[0]?.name || 'Choose File';
  customLabel.textContent = fileName;
});

// Variables for georeferencing
let controlPoints = [];
let isSelectingLayerPoint = false;

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
  processingMsg.textContent = 'Processing... maybe take 2-5 minutes';
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

// Add control points
map.on('click', (event) => {
  if (!isSelectingLayerPoint) return;

  const coords = toLonLat(event.coordinate);
  const controlPoint = new Feature(new Point(event.coordinate));
  controlPointsSource.addFeature(controlPoint);

  controlPoints.push(coords);

  if (controlPoints.length >= 6) {
    isSelectingLayerPoint = false;
    alert('Control points selected. Ready to georeference.');
  }
});

// Georeferencing process
georeferenceButton.addEventListener('click', () => {
  if (controlPoints.length < 6) {
    alert('Select at least 3 pairs of control points before applying georeferencing.');
    isSelectingLayerPoint = true;
    alert('Select 3 pairs of points: click on the map and then on the layer.');
  } else {
    applyGeoreferencing();
  }
});

// Georeference function
function applyGeoreferencing() {
  const mapPoints = controlPoints
    .filter((_, index) => index % 2 === 0) // Even indices (map points)
    .map((coords) => coords);

  const layerPoints = controlPoints
    .filter((_, index) => index % 2 !== 0) // Odd indices (layer points)
    .map((coords) => coords);

  if (mapPoints.length !== layerPoints.length || mapPoints.length < 3) {
    alert('Invalid control points. Please select at least 3 valid pairs.');
    return;
  }

  const matrix = computeAffineTransform(layerPoints, mapPoints);

  // Apply transformation to layer features
  const features = layerSource.getFeatures();
  features.forEach((feature) => {
    const geometry = feature.getGeometry();
    geometry.applyTransform((coords) => {
      const [x, y] = coords;
      const transformedCoords = applyMatrixTransform(matrix, x, y);
      coords[0] = transformedCoords[0];
      coords[1] = transformedCoords[1];
    });
  });

  layerSource.refresh();
  alert('Georeferencing applied.');
}

// Compute affine transformation
function computeAffineTransform(sourcePoints, targetPoints) {
  const n = sourcePoints.length;
  const A = [];
  const B = [];

  for (let i = 0; i < n; i++) {
    const [x, y] = sourcePoints[i];
    const [xPrime, yPrime] = targetPoints[i];
    A.push([x, y, 1, 0, 0, 0]);
    A.push([0, 0, 0, x, y, 1]);
    B.push(xPrime);
    B.push(yPrime);
  }

  const AT = numeric.transpose(A);
  const ATA = numeric.dot(AT, A);
  const ATB = numeric.dot(AT, B);
  const affineParams = numeric.solve(ATA, ATB); // Returns [a, b, tx, c, d, ty]
  return affineParams;
}

// Apply affine transformation matrix
function applyMatrixTransform(matrix, x, y) {
  const [a, b, tx, c, d, ty] = matrix;
  const newX = a * x + b * y + tx;
  const newY = c * x + d * y + ty;
  return [newX, newY];
}
