/* ==========================================================================
   PORTO DE WEATHER — FRONTEND JAVASCRIPT
   Handles dynamic data binding, Chart.js trends, filtering, pagination and interactive UI
   ========================================================================== */

// Weather Code mapping to Lucide Icons & Descriptions
const WMO_WEATHER_CODES = {
    0: { desc: "Clear Sky", icon: "sun" },
    1: { desc: "Mainly Clear", icon: "cloud-sun" },
    2: { desc: "Partly Cloudy", icon: "cloud-sun" },
    3: { desc: "Overcast", icon: "cloud" },
    45: { desc: "Foggy", icon: "cloud-fog" },
    48: { desc: "Depositing Rime Fog", icon: "cloud-fog" },
    51: { desc: "Light Drizzle", icon: "cloud-drizzle" },
    53: { desc: "Moderate Drizzle", icon: "cloud-drizzle" },
    55: { desc: "Dense Drizzle", icon: "cloud-drizzle" },
    61: { desc: "Slight Rain", icon: "cloud-rain" },
    63: { desc: "Moderate Rain", icon: "cloud-rain" },
    65: { desc: "Heavy Rain", icon: "cloud-heavy-rain" },
    80: { desc: "Slight Rain Showers", icon: "cloud-rain" },
    81: { desc: "Moderate Rain Showers", icon: "cloud-rain" },
    82: { desc: "Violent Rain Showers", icon: "cloud-heavy-rain" },
    95: { desc: "Thunderstorm", icon: "cloud-lightning" },
    96: { desc: "Thunderstorm with Hail", icon: "cloud-lightning" },
    99: { desc: "Severe Thunderstorm", icon: "cloud-lightning" }
};

// Global state
let dashboardData = null; // latest_conditions.json
let dailySummariesData = []; // daily_summaries.json
let filteredDailySummaries = []; // filtered summaries
let tableCurrentPage = 1;
const tablePageSize = 10;

let trendChart = null;

// Pagination and filters for live conditions cards
let visibleCitiesLimit = 24;
let filteredCities = [];

// Helper to format timestamps to readable strings
function formatDateTime(isoString) {
    if (!isoString) return "N/A";
    const date = new Date(isoString);
    return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
    });
}

// Map AQI to CSS class and label
function getAqiInfo(aqi) {
    if (aqi <= 50) return { label: "Good", class: "aqi-good" };
    if (aqi <= 100) return { label: "Moderate", class: "aqi-moderate" };
    if (aqi <= 150) return { label: "Sensitive", class: "aqi-unhealthy-sens" };
    return { label: "Unhealthy", class: "aqi-unhealthy" };
}

// ──────────────────────────────────────────────────────────────
// DATA INITIALIZATION & RENDERING
// ──────────────────────────────────────────────────────────────

async function loadDashboardData() {
    try {
        const response = await fetch('data/latest_conditions.json');
        if (!response.ok) throw new Error('Data file not found or corrupted.');
        
        dashboardData = await response.json();
        
        updateMetadata();
        renderSummaryMetrics();
        setupCitySelector();
        applyCityFilters(true); // reset pagination and render
        renderAqiAlerts();
        
        // Load table summaries in the background
        loadDailySummaries();
        
        // Initial chart load
        updateTrendsChart();
        
    } catch (err) {
        console.error('Error loading dashboard data:', err);
        document.getElementById('live-conditions-grid').innerHTML = `
            <div class="empty-state">
                <i data-lucide="alert-octagon" class="color-red"></i>
                <p>Failed to load dashboard data. Make sure the python runner has successfully run once.</p>
            </div>
        `;
        lucide.createIcons();
    }
}

function updateMetadata() {
    const meta = dashboardData.metadata;
    document.getElementById('pipeline-last-ingest').innerText = formatDateTime(meta.generated_at);
    document.getElementById('pipeline-cities-count').innerText = meta.cities_count;
}

function renderSummaryMetrics() {
    const latest = dashboardData.latest_conditions;
    if (!latest || latest.length === 0) return;
    
    // Average Temperature
    const avgTemp = latest.reduce((sum, c) => sum + c.temperature_c, 0) / latest.length;
    document.getElementById('metric-avg-temp').innerText = avgTemp.toFixed(1);
    
    // Average AQI
    const avgAqi = latest.reduce((sum, c) => sum + c.aqi_value, 0) / latest.length;
    const aqiInfo = getAqiInfo(avgAqi);
    document.getElementById('metric-avg-aqi').innerText = Math.round(avgAqi);
    document.getElementById('metric-aqi-status').innerText = aqiInfo.label;
    document.getElementById('metric-aqi-status').className = `aqi-lbl ${aqiInfo.class}`;
    
    // Active Air Alerts (latest hour AQI > 100)
    const alertCount = latest.filter(c => c.aqi_value > 100).length;
    document.getElementById('metric-alerts-count').innerText = alertCount;
    document.getElementById('alert-badge-count').innerText = alertCount;
    if (alertCount > 0) {
        document.getElementById('metric-alerts-subtext').innerText = `${alertCount} cities unhealthy!`;
        document.getElementById('metric-alerts-subtext').className = "metric-change color-red animate-pulse";
    } else {
        document.getElementById('metric-alerts-subtext').innerText = "All cities healthy";
        document.getElementById('metric-alerts-subtext').className = "metric-change text-muted";
    }
    
    // Total Precipitation
    const totalRain = latest.reduce((sum, c) => sum + c.precipitation_mm, 0);
    document.getElementById('metric-total-rain').innerText = totalRain.toFixed(1);
}

// ──────────────────────────────────────────────────────────────
// LIVE CONDITIONS FILTERS & PAGINATION
// ──────────────────────────────────────────────────────────────

function applyCityFilters(resetLimit = false) {
    if (!dashboardData) return;
    if (resetLimit) {
        visibleCitiesLimit = 24;
    }
    
    const query = document.getElementById('city-search-input').value.toLowerCase();
    const island = document.getElementById('filter-island').value;
    const aqiFilter = document.getElementById('filter-aqi').value;
    const sort = document.getElementById('sort-by').value;
    
    let cities = [...dashboardData.latest_conditions];
    
    // 1. Search Query filter
    if (query) {
        cities = cities.filter(c => 
            c.city_name.toLowerCase().includes(query) || 
            (c.province && c.province.toLowerCase().includes(query)) ||
            (c.island && c.island.toLowerCase().includes(query))
        );
    }
    
    // 2. Island filter
    if (island !== 'all') {
        cities = cities.filter(c => c.island === island);
    }
    
    // 3. AQI Category filter
    if (aqiFilter !== 'all') {
        cities = cities.filter(c => {
            if (aqiFilter === 'good') return c.aqi_value <= 50;
            if (aqiFilter === 'moderate') return c.aqi_value > 50 && c.aqi_value <= 100;
            if (aqiFilter === 'sensitive') return c.aqi_value > 100 && c.aqi_value <= 150;
            if (aqiFilter === 'unhealthy') return c.aqi_value > 150;
            return true;
        });
    }
    
    // 4. Sorting
    cities.sort((a, b) => {
        if (sort === 'name') {
            return a.city_name.localeCompare(b.city_name);
        } else if (sort === 'temp-desc') {
            return b.temperature_c - a.temperature_c;
        } else if (sort === 'temp-asc') {
            return a.temperature_c - b.temperature_c;
        } else if (sort === 'aqi-desc') {
            return b.aqi_value - a.aqi_value;
        } else if (sort === 'aqi-asc') {
            return a.aqi_value - b.aqi_value;
        }
        return 0;
    });
    
    filteredCities = cities;
    
    // Update count labels
    document.getElementById('total-cities-count').innerText = dashboardData.latest_conditions.length;
    document.getElementById('displayed-cities-count').innerText = filteredCities.length;
    
    renderCityCards();
}

function renderCityCards() {
    const grid = document.getElementById('live-conditions-grid');
    grid.innerHTML = '';
    
    const slice = filteredCities.slice(0, visibleCitiesLimit);
    
    if (slice.length === 0) {
        grid.innerHTML = `
            <div class="empty-state">
                <i data-lucide="search-slash"></i>
                <p>No cities found matching the filters.</p>
            </div>
        `;
        document.getElementById('btn-load-more').style.display = 'none';
        lucide.createIcons();
        return;
    }
    
    slice.forEach(city => {
        const aqi = getAqiInfo(city.aqi_value);
        const wmo = WMO_WEATHER_CODES[city.wmo_weather_code] || { desc: "Cloudy", icon: "cloud" };
        
        const card = document.createElement('div');
        card.className = 'city-card';
        card.style.cursor = 'pointer';
        card.innerHTML = `
            <div class="city-card-header">
                <div class="city-card-title">
                    <h3>${city.city_name}</h3>
                    <span>${city.province} (${city.island})</span>
                </div>
                <div class="weather-badge">
                    <i data-lucide="${wmo.icon}"></i> ${wmo.desc}
                </div>
            </div>
            
            <div class="city-card-temp-aqi">
                <div class="city-temp">${city.temperature_c.toFixed(1)}°C</div>
                <div class="city-aqi-indicator">
                    <div class="aqi-val">${city.aqi_value}</div>
                    <span class="aqi-lbl ${aqi.class}">AQI ${aqi.label}</span>
                </div>
            </div>
            
            <div class="city-details-grid">
                <div class="detail-item">
                    <i data-lucide="droplets"></i> Hum: ${city.humidity_pct}%
                </div>
                <div class="detail-item">
                    <i data-lucide="wind"></i> Wind: ${city.wind_speed_kmh} km/h
                </div>
                <div class="detail-item">
                    <i data-lucide="sun"></i> UV Index: ${city.uv_index}
                </div>
                <div class="detail-item">
                    <i data-lucide="activity"></i> PM2.5: ${city.pm2_5_ugm3} µg/m³
                </div>
            </div>
        `;
        
        // Interactive click event to load city trends
        card.addEventListener('click', () => {
            document.getElementById('chart-city-selector').value = city.city_name;
            updateTrendsChart();
            document.querySelector('.chart-card').scrollIntoView({ behavior: 'smooth', block: 'center' });
        });
        
        grid.appendChild(card);
    });
    
    // Manage Load More button
    const btnLoadMore = document.getElementById('btn-load-more');
    if (filteredCities.length > visibleCitiesLimit) {
        btnLoadMore.style.display = 'inline-flex';
    } else {
        btnLoadMore.style.display = 'none';
    }
    
    lucide.createIcons();
}

function renderAqiAlerts() {
    const alertList = document.getElementById('dashboard-alerts-list');
    alertList.innerHTML = '';
    
    const alerts = dashboardData.active_alerts;
    
    if (!alerts || alerts.length === 0) {
        alertList.innerHTML = `
            <div class="empty-state">
                <i data-lucide="smile" class="color-green"></i>
                <p>Air quality across all cities is healthy right now!</p>
            </div>
        `;
        lucide.createIcons();
        return;
    }
    
    alerts.forEach(alert => {
        const item = document.createElement('div');
        item.className = 'alert-item';
        item.innerHTML = `
            <div class="alert-item-info">
                <h4>${alert.city_name} (${alert.province})</h4>
                <span>${formatDateTime(alert.observed_at)}</span>
            </div>
            <div class="alert-item-badge">
                <div class="aq-val">${alert.aqi_value}</div>
                <div class="aq-lbl">${alert.aqi_category}</div>
            </div>
        `;
        alertList.appendChild(item);
    });
    
    lucide.createIcons();
}

// ──────────────────────────────────────────────────────────────
// DAILY SUMMARY TABLE (Asynchronous & Paginated)
// ──────────────────────────────────────────────────────────────

async function loadDailySummaries() {
    try {
        const response = await fetch('data/daily_summaries.json');
        if (!response.ok) throw new Error('Summaries not found.');
        dailySummariesData = await response.json();
        
        tableCurrentPage = 1;
        renderSummaryTable();
    } catch (err) {
        console.error('Error loading daily summaries:', err);
    }
}

function renderSummaryTable() {
    const tbody = document.getElementById('summary-table-body');
    if (!tbody) return;
    tbody.innerHTML = '';
    
    const query = document.getElementById('table-search-input').value.toLowerCase();
    filteredDailySummaries = dailySummariesData.filter(row => 
        row.city_name.toLowerCase().includes(query) || 
        (row.province && row.province.toLowerCase().includes(query)) ||
        (row.island && row.island.toLowerCase().includes(query))
    );
    
    const totalRows = filteredDailySummaries.length;
    const totalPages = Math.max(1, Math.ceil(totalRows / tablePageSize));
    
    if (tableCurrentPage > totalPages) {
        tableCurrentPage = totalPages;
    }
    if (tableCurrentPage < 1) {
        tableCurrentPage = 1;
    }
    
    document.getElementById('table-page-num').innerText = tableCurrentPage;
    document.getElementById('table-page-total').innerText = totalPages;
    
    document.getElementById('btn-table-prev').disabled = (tableCurrentPage === 1);
    document.getElementById('btn-table-next').disabled = (tableCurrentPage === totalPages);
    
    if (totalRows === 0) {
        tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; padding: 24px;">No summary data found.</td></tr>`;
        return;
    }
    
    const start = (tableCurrentPage - 1) * tablePageSize;
    const end = start + tablePageSize;
    const pageRows = filteredDailySummaries.slice(start, end);
    
    pageRows.forEach(row => {
        const aqiClass = row.max_aqi_value <= 50 ? 'aqi-good' : 
                         row.max_aqi_value <= 100 ? 'aqi-moderate' : 
                         row.max_aqi_value <= 150 ? 'aqi-unhealthy-sens' : 'aqi-unhealthy';
        
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${row.city_name}</strong><br><span class="text-muted" style="font-size:0.75rem;">${row.province || ''}</span></td>
            <td>${row.island || 'N/A'}</td>
            <td>${row.observed_date}</td>
            <td>${row.avg_temperature_c}°C</td>
            <td><span class="color-blue">${row.min_temperature_c}</span> / <span class="color-red">${row.max_temperature_c}</span></td>
            <td>${row.avg_humidity_pct}%</td>
            <td>${row.total_precipitation_mm} mm</td>
            <td><strong>${row.max_aqi_value}</strong></td>
            <td><span class="aqi-lbl ${aqiClass}">${row.worst_aqi_category}</span></td>
        `;
        tbody.appendChild(tr);
    });
}

// ──────────────────────────────────────────────────────────────
// CHART SETUP (Dynamic loading from Shards)
// ──────────────────────────────────────────────────────────────

function setupCitySelector() {
    const selector = document.getElementById('chart-city-selector');
    selector.innerHTML = '';
    
    const latest = dashboardData.latest_conditions;
    latest.forEach((city, index) => {
        const opt = document.createElement('option');
        opt.value = city.city_name;
        opt.innerText = city.city_name;
        if (index === 0) opt.selected = true;
        selector.appendChild(opt);
    });
}

async function updateTrendsChart() {
    const selectedCity = document.getElementById('chart-city-selector').value;
    if (!selectedCity || !dashboardData) return;
    
    const filename = selectedCity.toLowerCase().replace(/ /g, "_").replace(/'/g, "").replace(/-/g, "_") + ".json";
    
    try {
        const response = await fetch(`data/trends/${filename}`);
        if (!response.ok) throw new Error(`Trends for ${selectedCity} not found.`);
        const data = await response.json();
        
        const cityTrends = data.hourly_trends;
        const labels = cityTrends.map(t => {
            const d = new Date(t.observed_at);
            return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false });
        });
        
        const temps = cityTrends.map(t => t.temperature_c);
        const aqis = cityTrends.map(t => t.aqi_value);
        const rollingTemp = cityTrends.map(t => t.rolling_avg_temp_24h);
        
        const ctx = document.getElementById('temp-trend-chart').getContext('2d');
        
        if (trendChart) {
            trendChart.destroy();
        }
        
        trendChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Temperature (°C)',
                        data: temps,
                        borderColor: '#60a5fa',
                        backgroundColor: 'rgba(96, 165, 250, 0.1)',
                        yAxisID: 'y-temp',
                        tension: 0.3,
                        borderWidth: 2,
                        fill: true
                    },
                    {
                        label: '24h Rolling Avg Temp (°C)',
                        data: rollingTemp,
                        borderColor: '#a78bfa',
                        borderDash: [5, 5],
                        yAxisID: 'y-temp',
                        tension: 0.3,
                        borderWidth: 2,
                        fill: false
                    },
                    {
                        label: 'Air Quality (AQI)',
                        data: aqis,
                        borderColor: '#34d399',
                        backgroundColor: 'rgba(52, 211, 153, 0.05)',
                        yAxisID: 'y-aqi',
                        tension: 0.3,
                        borderWidth: 2,
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            color: '#9ca3af',
                            font: {
                                family: 'Inter'
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: {
                            color: 'rgba(255, 255, 255, 0.05)'
                        },
                        ticks: {
                            color: '#9ca3af'
                        }
                    },
                    'y-temp': {
                        type: 'linear',
                        position: 'left',
                        grid: {
                            color: 'rgba(255, 255, 255, 0.05)'
                        },
                        ticks: {
                            color: '#60a5fa'
                        },
                        title: {
                            display: true,
                            text: 'Temperature (°C)',
                            color: '#60a5fa'
                        }
                    },
                    'y-aqi': {
                        type: 'linear',
                        position: 'right',
                        grid: {
                            drawOnChartArea: false
                        },
                        ticks: {
                            color: '#34d399'
                        },
                        title: {
                            display: true,
                            text: 'AQI Value',
                            color: '#34d399'
                        }
                    }
                }
            }
        });
    } catch (err) {
        console.error('Error loading trends:', err);
    }
}

// ──────────────────────────────────────────────────────────────
// LISTENERS & EVENT HANDLING
// ──────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    loadDashboardData();
    
    // Refresh button
    document.getElementById('btn-refresh').addEventListener('click', () => {
        const btn = document.getElementById('btn-refresh');
        btn.disabled = true;
        btn.innerHTML = `<i data-lucide="loader-2" class="spin"></i> Refreshing...`;
        lucide.createIcons();
        
        loadDashboardData().finally(() => {
            btn.disabled = false;
            btn.innerHTML = `<i data-lucide="rotate-cw"></i> Refresh Data`;
            lucide.createIcons();
        });
    });
    
    // Toolbar search and filters
    document.getElementById('city-search-input').addEventListener('input', () => applyCityFilters(true));
    document.getElementById('filter-island').addEventListener('change', () => applyCityFilters(true));
    document.getElementById('filter-aqi').addEventListener('change', () => applyCityFilters(true));
    document.getElementById('sort-by').addEventListener('change', () => applyCityFilters(true));
    
    document.getElementById('btn-load-more').addEventListener('click', () => {
        visibleCitiesLimit += 24;
        renderCityCards();
    });
    
    // Trend City selector change
    document.getElementById('chart-city-selector').addEventListener('change', updateTrendsChart);
    
    // Live Search on Mart Table
    document.getElementById('table-search-input').addEventListener('input', () => {
        tableCurrentPage = 1;
        renderSummaryTable();
    });
    
    // Mart Table pagination
    document.getElementById('btn-table-prev').addEventListener('click', () => {
        if (tableCurrentPage > 1) {
            tableCurrentPage--;
            renderSummaryTable();
        }
    });
    
    document.getElementById('btn-table-next').addEventListener('click', () => {
        const totalPages = Math.ceil(filteredDailySummaries.length / tablePageSize);
        if (tableCurrentPage < totalPages) {
            tableCurrentPage++;
            renderSummaryTable();
        }
    });
});
