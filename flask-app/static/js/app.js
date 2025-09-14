// static/js/app.js

document.addEventListener('DOMContentLoaded', () => {
    // 1) Initialize map without default zoom controls
    const map = L.map('map', { zoomControl: false }).setView([39.9526, -75.1652], 13);
    L.tileLayer(
      'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
      {
        attribution:
          '&copy; <a href="https://carto.com/">CARTO</a> contributors, &copy; OpenStreetMap',
        subdomains: 'abcd',
        maxZoom: 19
      }
    ).addTo(map);
    L.control.scale({ imperial: false }).addTo(map);
  
    // 2) Marker cluster
    const markers = L.markerClusterGroup().addTo(map);
  
    // 3) Helpers
    function severityColor(s) {
      return s >= 4 ? '#e31a1c'
           : s >= 3 ? '#fd8d3c'
           : s >= 2 ? '#fecc5c'
           :          '#31a354';
    }
    function makeIcon(sev) {
      const color = severityColor(sev);
      return L.divIcon({
        html: `<div style="
          background:${color};
          width:16px; height:16px;
          border:2px solid white;
          border-radius:50%;
          box-shadow:0 0 2px rgba(0,0,0,0.5);
        "></div>`,
        className: '',
        iconSize: [20,20],
        iconAnchor: [10,10]
      });
    }
  
    // 4) Control variables
    let sevChecks, startEl, endEl, confEl, confValEl, exportCsvBtn, exportGeoBtn, errDiv, zoomInBtn, zoomOutBtn;
  
    // 5) Legend panel with embedded controls + custom zoom + home link
    const legend = L.control({ position: 'topleft' });
    legend.onAdd = () => {
      const w = L.DomUtil.create('div', 'leaflet-control legend tb-panel');
      w.innerHTML = `
        <div class="panel-header">
          <h3>Filters & Export</h3>
        </div>
        <div class="tb-body">
          <div class="filter-group">
            <label>Severity</label>
            <div class="severity-options">
              <label><input type="checkbox" value="1"> 1 – Minor</label>
              <label><input type="checkbox" value="2"> 2 – Low</label>
              <label><input type="checkbox" value="3"> 3 – Medium</label>
              <label><input type="checkbox" value="4"> 4 – High</label>
              <label><input type="checkbox" value="5"> 5 – Critical</label>
            </div>
          </div>
          <div class="filter-group">
            <label>Start Date</label>
            <input type="date" id="start_date"/>
          </div>
          <div class="filter-group">
            <label>End Date</label>
            <input type="date" id="end_date"/>
          </div>
          <div class="filter-group">
            <label>Confidence ≥ <span id="conf_val">0.00</span></label>
            <input type="number" id="confidence" min="0" max="1" step="0.01" value="0.00"/>
          </div>
          <div id="conf-error" class="conf-error"></div>
          <div class="zoom-group">
            <label>Zoom</label>
            <button id="zoom-in">+</button>
            <button id="zoom-out">−</button>
          </div>
          <button class="export-btn" id="export-csv">Export CSV</button>
          <button class="export-btn" id="export-geojson">Export GeoJSON</button>
        </div>
      `;
      L.DomEvent.disableClickPropagation(w);
  
      // grab controls
      sevChecks     = w.querySelectorAll('.severity-options input');
      startEl       = w.querySelector('#start_date');
      endEl         = w.querySelector('#end_date');
      confEl        = w.querySelector('#confidence');
      confValEl     = w.querySelector('#conf_val');
      errDiv        = w.querySelector('#conf-error');
      zoomInBtn     = w.querySelector('#zoom-in');
      zoomOutBtn    = w.querySelector('#zoom-out');
      exportCsvBtn  = w.querySelector('#export-csv');
      exportGeoBtn  = w.querySelector('#export-geojson');
  
      // attach handlers
      sevChecks.forEach(chk => chk.addEventListener('change', fetchAndRender));
      startEl.addEventListener('change', fetchAndRender);
      endEl.addEventListener('change', fetchAndRender);
      confEl.addEventListener('change', () => {
        let v = parseFloat(confEl.value);
        if (isNaN(v) || v < 0 || v > 1) {
          errDiv.textContent = '⚠️ Confidence must be 0.00–1.00';
          errDiv.style.display = 'block';
          v = Math.min(Math.max(v||0,0),1);
          confEl.value = v.toFixed(2);
        } else {
          errDiv.style.display = 'none';
        }
        confValEl.textContent = parseFloat(confEl.value).toFixed(2);
        fetchAndRender();
      });
  
      zoomInBtn.addEventListener('click', () => map.zoomIn());
      zoomOutBtn.addEventListener('click', () => map.zoomOut());
  
      exportCsvBtn.addEventListener('click', () => {
        window.location = '/export?format=csv&' + buildParams();
      });
      exportGeoBtn.addEventListener('click', () => {
        window.location = '/export?format=geojson&' + buildParams();
      });
  
      return w;
    };
    legend.addTo(map);
  
    // 6) Build params
    function buildParams() {
      const params = new URLSearchParams();
      sevChecks.forEach(chk => { if (chk.checked) params.append('severity', chk.value); });
      if (startEl.value) params.set('start_date', startEl.value);
      if (endEl.value)   params.set('end_date', endEl.value);
      const c = parseFloat(confEl.value)||0;
      params.set('conf_min', c.toFixed(2));
      return params.toString();
    }
  
    // 7) Fetch & render
    async function fetchAndRender() {
      try {
        const res = await fetch('/api/potholes?' + buildParams());
        const data = await res.json();
        markers.clearLayers();
        data.forEach(p => {
          const severityText = p.severity >= 4 ? 'Critical' : p.severity >= 3 ? 'High' : p.severity >= 2 ? 'Medium' : 'Low';
          const confidencePercent = Math.round(p.confidence * 100);
          const formattedDate = new Date(p.date).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
          });

          L.marker([p.lat, p.lng], { icon: makeIcon(p.severity) })
            .bindPopup(`
              <div class="popup-header">
                <h4 class="popup-title">🕳️ Pothole Detection</h4>
                <p class="popup-subtitle">ID: ${p.id} • ${formattedDate}</p>
              </div>

              <div class="popup-body">
                <div class="popup-image-container">
                  ${p.image_url
                    ? `<img src="${p.image_url}" class="popup-image" alt="Pothole image" loading="lazy">`
                    : `<div class="popup-image-placeholder">📷</div>`
                  }
                </div>

                <div class="popup-details">
                  <div class="popup-info-grid">
                    <div class="popup-info-item">
                      <div class="popup-info-label">Severity Level</div>
                      <div class="popup-info-value severity">
                        <span class="popup-severity-badge severity-${p.severity}">${severityText}</span>
                      </div>
                    </div>

                    <div class="popup-info-item">
                      <div class="popup-info-label">AI Confidence</div>
                      <div class="popup-info-value">${confidencePercent}%</div>
                      <div class="popup-confidence-bar">
                        <div class="popup-confidence-fill" style="width: ${confidencePercent}%"></div>
                      </div>
                    </div>
                  </div>

                  ${p.description ? `
                    <div class="popup-description">
                      <p class="popup-description-text">${p.description}</p>
                    </div>
                  ` : ''}

                  <div class="popup-actions">
                    <button class="popup-action-btn primary" onclick="window.open('/incidents', '_blank')">
                      📋 View Details
                    </button>
                    <button class="popup-action-btn secondary" onclick="navigator.share ? navigator.share({title: 'Pothole Report', text: 'Found pothole at ${p.lat.toFixed(4)}, ${p.lng.toFixed(4)}'}) : alert('Location: ${p.lat.toFixed(4)}, ${p.lng.toFixed(4)}')">
                      📍 Share
                    </button>
                  </div>
                </div>
              </div>

              <div class="popup-meta">
                <div class="popup-timestamp">
                  🕐 ${formattedDate}
                </div>
                <div class="popup-coordinates">
                  📍 ${p.lat.toFixed(4)}, ${p.lng.toFixed(4)}
                </div>
              </div>
            `)
            .addTo(markers);
        });
      } catch (err) {
        console.error('Error:', err);
      }
    }
  
    // 8) Initial load
    fetchAndRender();
  });
  