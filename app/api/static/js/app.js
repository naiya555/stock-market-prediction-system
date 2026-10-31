/**
 * Indian Stock Market Prediction System - Interactive Web Client
 * Phase 13: Web Application & API Layer (Day 34)
 *
 * Implements client-side state management, API communication, DOM rendering,
 * input validation, and real-time status diagnostics without external JS dependencies.
 */

(function () {
  'use strict';

  // -------------------------------------------------------------------------
  // Configuration & Constants
  // -------------------------------------------------------------------------
  const API_BASE = window.location.origin + '/api';

  // Application State
  const AppState = {
    activeTab: 'predict',
    prediction: null,
    lastPredictionPayload: null,
    isPredicting: false,
    predictionRequestId: 0,
    activePredictionAbortController: null,
    catalog: [],
    history: {
      items: [],
      total: 0,
      limit: 25,
      offset: 0,
      symbolFilter: '',
      modelFilter: '',
      isLoading: false,
    },
    events: {
      items: [],
      categoryFilter: '',
      isLoading: false,
    },
    health: {
      status: 'unknown',
      dependencies: {},
      lastEvaluated: null,
      isLoading: false,
    },
  };

  // -------------------------------------------------------------------------
  // Utility Functions
  // -------------------------------------------------------------------------
  function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    const div = document.createElement('div');
    div.textContent = String(str);
    return div.innerHTML;
  }

  function isSafeHttpUrl(urlStr) {
    if (!urlStr || typeof urlStr !== 'string') return false;
    try {
      const parsed = new URL(urlStr);
      return parsed.protocol === 'http:' || parsed.protocol === 'https:';
    } catch (e) {
      return false;
    }
  }

  function formatPriceINR(val) {
    if (val === null || val === undefined || isNaN(val)) return '₹--';
    return '₹' + Number(val).toLocaleString('en-IN', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }

  function formatPercent(val) {
    if (val === null || val === undefined || isNaN(val)) return '--%';
    const pct = Number(val) * 100;
    const sign = pct > 0 ? '+' : '';
    return sign + pct.toFixed(2) + '%';
  }

  function formatDateTimeIST(isoString) {
    if (!isoString) return '--';
    try {
      const dt = new Date(isoString);
      return dt.toLocaleString('en-IN', {
        timeZone: 'Asia/Kolkata',
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
      }) + ' IST';
    } catch (e) {
      return String(isoString);
    }
  }

  function startMarketClock() {
    const clockEl = document.getElementById('market-clock-time');
    if (!clockEl) return;

    function update() {
      const now = new Date();
      const timeStr = now.toLocaleTimeString('en-IN', {
        timeZone: 'Asia/Kolkata',
        hour12: false,
      });
      clockEl.textContent = timeStr + ' IST';
    }
    update();
    setInterval(update, 1000);
  }

  // -------------------------------------------------------------------------
  // API Service Layer
  // -------------------------------------------------------------------------
  const ApiService = {
    async fetchHealth() {
      const res = await fetch(`${API_BASE}/health`, {
        headers: { 'Accept': 'application/json' },
      });
      if (!res.ok && res.status !== 503) {
        throw new Error(`Health API responded with status ${res.status}`);
      }
      return await res.json();
    },

    async fetchInstruments() {
      const res = await fetch(`${API_BASE}/predict/instruments`, {
        headers: { 'Accept': 'application/json' },
      });
      if (!res.ok) {
        throw new Error(`Failed to fetch instrument catalog (HTTP ${res.status})`);
      }
      return await res.json();
    },

    async runPrediction(payload, timeoutMs = 30000) {
      if (AppState.activePredictionAbortController) {
        AppState.activePredictionAbortController.abort();
      }
      const controller = new AbortController();
      AppState.activePredictionAbortController = controller;
      const timer = setTimeout(() => controller.abort(), timeoutMs);

      try {
        const res = await fetch(`${API_BASE}/predict`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
          },
          body: JSON.stringify(payload),
          signal: controller.signal,
        });

        const data = await res.json().catch(() => null);

        if (!data || typeof data !== 'object') {
          throw new Error('Received empty or malformed payload from prediction server.');
        }

        if (!res.ok) {
          let msg = 'Failed to execute prediction.';
          if (data && data.error && data.error.message) {
            msg = data.error.message;
          } else if (data && data.detail) {
            if (Array.isArray(data.detail)) {
              msg = data.detail
                .map((d) => (d.loc ? d.loc.slice(-1)[0] + ': ' : '') + (d.msg || JSON.stringify(d)))
                .join('; ');
            } else if (typeof data.detail === 'string') {
              msg = data.detail;
            } else {
              msg = JSON.stringify(data.detail);
            }
          }
          const err = new Error(msg);
          err.status = res.status;
          err.data = data;
          throw err;
        }

        return data;
      } catch (err) {
        if (err.name === 'AbortError') {
          throw new Error('Prediction request timed out after 30 seconds. The server or market data provider may be busy.');
        }
        if (err instanceof TypeError && /fetch/i.test(err.message)) {
          throw new Error('The prediction service could not be reached. Check that the application server is running, then retry.');
        }
        throw err;
      } finally {
        clearTimeout(timer);
        if (AppState.activePredictionAbortController === controller) {
          AppState.activePredictionAbortController = null;
        }
      }
    },

    async fetchHistory(params) {
      const query = new URLSearchParams();
      if (params.symbol) query.set('symbol', params.symbol);
      if (params.model_name) query.set('model_name', params.model_name);
      query.set('limit', String(params.limit || 25));
      query.set('offset', String(params.offset || 0));

      const res = await fetch(`${API_BASE}/history?${query.toString()}`, {
        headers: { 'Accept': 'application/json' },
      });

      if (!res.ok) {
        throw new Error(`History API error: status ${res.status}`);
      }
      return await res.json();
    },

    async fetchComparison(params = {}) {
      const query = new URLSearchParams();
      if (params.symbol) query.set('symbol', params.symbol);
      query.set('min_verified', String(params.min_verified || 1));

      const res = await fetch(`${API_BASE}/history/compare?${query.toString()}`, {
        headers: { 'Accept': 'application/json' },
      });

      if (!res.ok) {
        throw new Error(`Comparison API error: status ${res.status}`);
      }
      return await res.json();
    },

    async fetchEvents(params) {
      const query = new URLSearchParams();
      if (params.category) query.set('category', params.category);
      query.set('limit', '50');

      const res = await fetch(`${API_BASE}/events?${query.toString()}`, {
        headers: { 'Accept': 'application/json' },
      });

      if (!res.ok) {
        throw new Error(`Events API error: status ${res.status}`);
      }
      return await res.json();
    },

    async fetchChartData(symbol, range = '1m') {
      const query = new URLSearchParams();
      query.set('symbol', symbol);
      query.set('range', range);
      const res = await fetch(`${API_BASE}/predict/chart-data?${query.toString()}`, {
        headers: { 'Accept': 'application/json' },
      });
      if (!res.ok) {
        throw new Error(`Chart data API error: status ${res.status}`);
      }
      return await res.json();
    },

    async sendChatMessage(payload) {
      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      const data = await res.json().catch(() => null);
      if (!res.ok) {
        let msg = `Chat service error (${res.status})`;
        if (data && data.detail) {
          msg = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
        }
        throw new Error(msg);
      }
      return data;
    },
  };

  // -------------------------------------------------------------------------
  // Tab Controller
  // -------------------------------------------------------------------------
  function initNavigationTabs() {
    const tabs = document.querySelectorAll('.nav-tab');
    tabs.forEach((tab) => {
      tab.addEventListener('click', () => {
        const targetId = tab.getAttribute('aria-controls');
        if (!targetId) return;

        // Switch active tab button
        tabs.forEach((t) => {
          t.classList.remove('active');
          t.setAttribute('aria-selected', 'false');
        });
        tab.classList.add('active');
        tab.setAttribute('aria-selected', 'true');

        // Switch panel visibility
        document.querySelectorAll('.tab-panel').forEach((p) => p.classList.remove('active'));
        const activePanel = document.getElementById(targetId);
        if (activePanel) activePanel.classList.add('active');

        // Trigger on-demand data loads
        if (targetId === 'tab-panel-dashboard') {
          loadDashboard();
        } else if (targetId === 'tab-panel-history') {
          loadHistory();
        } else if (targetId === 'tab-panel-events') {
          loadEvents();
        } else if (targetId === 'tab-panel-health') {
          loadHealth();
        }
      });
    });

    // Make health pill clickable to jump directly to Health tab
    const healthPill = document.getElementById('health-pill');
    if (healthPill) {
      healthPill.addEventListener('click', () => {
        const healthTabBtn = document.getElementById('tab-btn-health');
        if (healthTabBtn) healthTabBtn.click();
      });
    }
  }

  // -------------------------------------------------------------------------
  // Stale State Cleanup Helper
  // -------------------------------------------------------------------------
  function clearStalePredictionIfSymbolChanged(newSymbol) {
    if (AppState.prediction && AppState.prediction.symbol !== newSymbol) {
      AppState.prediction = null;
      const heroCard = document.getElementById('result-hero-card');
      const blockedCard = document.getElementById('result-blocked-card');
      const breakdownGrid = document.querySelector('.breakdown-grid');
      const resultsContainer = document.getElementById('prediction-results-container');
      const emptyState = document.getElementById('predict-empty-state');
      if (heroCard) heroCard.style.display = 'none';
      if (blockedCard) blockedCard.style.display = 'none';
      if (breakdownGrid) breakdownGrid.style.display = 'none';
      if (resultsContainer) resultsContainer.style.display = 'none';
      if (emptyState) emptyState.style.display = 'block';
    }
  }

  // -------------------------------------------------------------------------
  // Dashboard Controller
  // -------------------------------------------------------------------------
  // Interactive Dashboard Chart Controller (Phase 5)
  // -------------------------------------------------------------------------
  const ChartState = {
    activeSymbol: 'BHARTIARTL',
    activeRange: '1m',
    zoomLevel: 1.0,
    data: null,
    refreshIntervalId: null,
  };

  function initInteractiveChart() {
    // Instrument selector pills
    const instPills = document.querySelectorAll('#chart-instrument-pills .chart-pill-btn');
    instPills.forEach((btn) => {
      btn.addEventListener('click', () => {
        const sym = btn.getAttribute('data-symbol');
        if (!sym) return;
        ChartState.activeSymbol = sym;
        instPills.forEach((b) => b.classList.remove('active'));
        btn.classList.add('active');
        loadInteractiveChart();
      });
    });

    // Time range selector pills
    const rangePills = document.querySelectorAll('#chart-range-pills .chart-pill-btn');
    rangePills.forEach((btn) => {
      btn.addEventListener('click', () => {
        const rng = btn.getAttribute('data-range');
        if (!rng) return;
        ChartState.activeRange = rng;
        rangePills.forEach((b) => b.classList.remove('active'));
        btn.classList.add('active');
        loadInteractiveChart();
      });
    });

    // Zoom and pan controls
    const zoomInBtn = document.getElementById('btn-chart-zoom-in');
    const zoomOutBtn = document.getElementById('btn-chart-zoom-out');
    const resetBtn = document.getElementById('btn-chart-reset');

    if (zoomInBtn) {
      zoomInBtn.addEventListener('click', () => {
        ChartState.zoomLevel = Math.min(3.0, ChartState.zoomLevel + 0.25);
        renderInteractiveChart();
      });
    }
    if (zoomOutBtn) {
      zoomOutBtn.addEventListener('click', () => {
        ChartState.zoomLevel = Math.max(0.6, ChartState.zoomLevel - 0.25);
        renderInteractiveChart();
      });
    }
    if (resetBtn) {
      resetBtn.addEventListener('click', () => {
        ChartState.zoomLevel = 1.0;
        renderInteractiveChart();
      });
    }

    // Set auto-refresh timer (60s)
    if (ChartState.refreshIntervalId) {
      clearInterval(ChartState.refreshIntervalId);
    }
    ChartState.refreshIntervalId = setInterval(() => {
      if (AppState.activeTab === 'dashboard') {
        loadInteractiveChart();
      }
    }, 60000);
  }

  async function loadInteractiveChart() {
    try {
      const chartData = await ApiService.fetchChartData(ChartState.activeSymbol, ChartState.activeRange);
      ChartState.data = chartData;
      renderInteractiveChart();
    } catch (e) {
      console.warn('Failed to load chart data:', e);
    }
  }

  function renderInteractiveChart() {
    const svg = document.getElementById('dash-trend-svg');
    const tooltip = document.getElementById('chart-tooltip');
    const updatedEl = document.getElementById('chart-last-updated-text');
    const noteEl = document.getElementById('chart-provider-note');
    if (!svg) return;

    if (!ChartState.data || !ChartState.data.data_points || ChartState.data.data_points.length === 0) {
      svg.innerHTML = `
        <text x="350" y="120" fill="#94a3b8" font-size="14" text-anchor="middle" font-family="Inter, sans-serif">
          No market observations available for ${escapeHtml(ChartState.activeSymbol)} in range ${escapeHtml(ChartState.activeRange)}
        </text>
      `;
      return;
    }

    const data = ChartState.data;
    const pts = data.data_points;
    const count = pts.length;

    if (updatedEl && data.last_updated) {
      updatedEl.textContent = `Last updated: ${formatDateTimeIST(data.last_updated)}`;
    }
    if (noteEl && data.note) {
      noteEl.textContent = data.note;
    }

    // Determine min and max price
    let minPrice = Infinity;
    let maxPrice = -Infinity;
    for (let i = 0; i < count; i++) {
      const p = pts[i].close;
      if (p < minPrice) minPrice = p;
      if (p > maxPrice) maxPrice = p;
    }
    if (minPrice === maxPrice) {
      minPrice = minPrice * 0.98;
      maxPrice = maxPrice * 1.02;
    }

    const pricePadding = (maxPrice - minPrice) * 0.08;
    const yMin = Math.max(0, minPrice - pricePadding);
    const yMax = maxPrice + pricePadding;
    const priceSpan = yMax - yMin;

    const W = 700;
    const H = 240;
    const mLeft = 60;
    const mRight = 95;
    const mTop = 25;
    const mBottom = 35;
    const plotW = W - mLeft - mRight;
    const plotH = H - mTop - mBottom;

    // Apply zoom
    const zoom = ChartState.zoomLevel;
    const visibleCount = Math.max(2, Math.round(count / zoom));
    const startIdx = Math.max(0, count - visibleCount);
    const visiblePts = pts.slice(startIdx);
    const visCount = visiblePts.length;

    const coords = visiblePts.map((pt, i) => {
      const x = mLeft + (i / Math.max(1, visCount - 1)) * plotW;
      const y = mTop + (1.0 - (pt.close - yMin) / priceSpan) * plotH;
      return { x, y, pt, idx: startIdx + i };
    });

    let pathD = '';
    let areaD = '';
    coords.forEach((c, i) => {
      if (i === 0) {
        pathD += `M ${c.x.toFixed(1)},${c.y.toFixed(1)}`;
        areaD += `M ${c.x.toFixed(1)},${c.y.toFixed(1)}`;
      } else {
        pathD += ` L ${c.x.toFixed(1)},${c.y.toFixed(1)}`;
        areaD += ` L ${c.x.toFixed(1)},${c.y.toFixed(1)}`;
      }
    });

    const lastCoord = coords[coords.length - 1];
    const firstCoord = coords[0];
    const baselineY = mTop + plotH;
    areaD += ` L ${lastCoord.x.toFixed(1)},${baselineY} L ${firstCoord.x.toFixed(1)},${baselineY} Z`;

    // Compute SMA-10 line
    let smaD = '';
    const smaWindow = 10;
    let smaStarted = false;
    coords.forEach((c) => {
      const fullIdx = c.idx;
      if (fullIdx >= smaWindow - 1) {
        let sum = 0;
        for (let k = fullIdx - smaWindow + 1; k <= fullIdx; k++) {
          sum += pts[k].close;
        }
        const smaVal = sum / smaWindow;
        const smaY = mTop + (1.0 - (smaVal - yMin) / priceSpan) * plotH;
        if (!smaStarted) {
          smaD += `M ${c.x.toFixed(1)},${smaY.toFixed(1)}`;
          smaStarted = true;
        } else {
          smaD += ` L ${c.x.toFixed(1)},${smaY.toFixed(1)}`;
        }
      }
    });

    // Horizontal grid lines
    const gridRows = 4;
    let gridLinesHtml = '';
    for (let g = 0; g <= gridRows; g++) {
      const pRatio = g / gridRows;
      const yPos = mTop + pRatio * plotH;
      const pVal = yMax - pRatio * priceSpan;
      gridLinesHtml += `
        <line x1="${mLeft}" y1="${yPos.toFixed(1)}" x2="${W - 20}" y2="${yPos.toFixed(1)}" stroke="rgba(255,255,255,0.06)" stroke-dasharray="2,2"/>
        <text x="${mLeft - 8}" y="${(yPos + 4).toFixed(1)}" fill="#64748b" font-size="10" text-anchor="end" font-family="JetBrains Mono, monospace">
          ₹${pVal >= 1000 ? Math.round(pVal).toLocaleString('en-IN') : pVal.toFixed(1)}
        </text>
      `;
    }

    // X-axis date labels
    const xLabelCount = Math.min(5, visCount);
    let xLabelsHtml = '';
    for (let xi = 0; xi < xLabelCount; xi++) {
      const idxOnVis = Math.floor((xi * (visCount - 1)) / Math.max(1, xLabelCount - 1));
      const c = coords[idxOnVis];
      if (c && c.pt.timestamp) {
        const dt = new Date(c.pt.timestamp);
        const labelText =
          ChartState.activeRange === 'today'
            ? dt.toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit', hour12: false })
            : dt.toLocaleDateString('en-IN', { timeZone: 'Asia/Kolkata', day: '2-digit', month: 'short' });
        xLabelsHtml += `
          <text x="${c.x.toFixed(1)}" y="${H - 12}" fill="#64748b" font-size="10" text-anchor="middle" font-family="Inter, sans-serif">
            ${labelText}
          </text>
        `;
      }
    }

    // Forward Forecast Point extension
    let forecastHtml = '';
    if (data.forecast_point && data.forecast_point.direction) {
      const fc = data.forecast_point;
      const isUp = fc.direction === 'UP';
      const fcColor = isUp ? '#10b981' : '#f43f5e';
      const fcDelta = isUp ? 0.015 : -0.015;
      const fcPrice = lastCoord.pt.close * (1.0 + fcDelta);
      const fcX = Math.min(W - 25, lastCoord.x + 55);
      const fcY = Math.max(mTop + 10, Math.min(H - mBottom - 10, mTop + (1.0 - (fcPrice - yMin) / priceSpan) * plotH));

      forecastHtml = `
        <!-- Dashed connector to forecast point -->
        <line x1="${lastCoord.x.toFixed(1)}" y1="${lastCoord.y.toFixed(1)}" x2="${fcX.toFixed(1)}" y2="${fcY.toFixed(1)}" stroke="${fcColor}" stroke-width="2" stroke-dasharray="4,4" opacity="0.85"/>
        <!-- Forward forecast node -->
        <circle cx="${fcX.toFixed(1)}" cy="${fcY.toFixed(1)}" r="6" fill="${fcColor}" stroke="#ffffff" stroke-width="2"/>
        <circle cx="${fcX.toFixed(1)}" cy="${fcY.toFixed(1)}" r="10" fill="none" stroke="${fcColor}" stroke-width="1.5" opacity="0.5" stroke-dasharray="2,2"/>
        <!-- Forecast Badge Text -->
        <rect x="${(fcX - 42).toFixed(1)}" y="${(fcY - 24).toFixed(1)}" width="84" height="18" rx="4" fill="rgba(15, 23, 42, 0.9)" stroke="${fcColor}" stroke-width="1"/>
        <text x="${fcX.toFixed(1)}" y="${(fcY - 11).toFixed(1)}" fill="${fcColor}" font-size="9" font-weight="700" text-anchor="middle" font-family="Inter, sans-serif">
          ${isUp ? '▲ FORECAST UP' : '▼ FORECAST DOWN'}
        </text>
      `;
    }

    svg.innerHTML = `
      <defs>
        <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#6366f1" stop-opacity="0.3"/>
          <stop offset="100%" stop-color="#6366f1" stop-opacity="0.0"/>
        </linearGradient>
      </defs>
      ${gridLinesHtml}
      ${xLabelsHtml}
      <path d="${areaD}" fill="url(#chartGradient)"/>
      <path d="${pathD}" fill="none" stroke="#6366f1" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
      ${smaD ? `<path d="${smaD}" fill="none" stroke="#f59e0b" stroke-width="1.5" stroke-dasharray="4,4" opacity="0.8"/>` : ''}
      <circle cx="${lastCoord.x.toFixed(1)}" cy="${lastCoord.y.toFixed(1)}" r="4.5" fill="#10b981" stroke="#ffffff" stroke-width="1.5"/>
      ${forecastHtml}
      <line id="chart-crosshair-x" x1="0" y1="${mTop}" x2="0" y2="${baselineY}" stroke="rgba(255,255,255,0.25)" stroke-dasharray="2,2" style="display:none;"/>
      <circle id="chart-crosshair-dot" cx="0" cy="0" r="5" fill="#6366f1" stroke="#ffffff" stroke-width="2" style="display:none;"/>
    `;

    // Mousemove for hover tooltips
    svg.onmousemove = function (e) {
      const rect = svg.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const svgX = (mouseX / rect.width) * W;

      let closest = coords[0];
      let minDiff = Infinity;
      for (let i = 0; i < coords.length; i++) {
        const diff = Math.abs(coords[i].x - svgX);
        if (diff < minDiff) {
          minDiff = diff;
          closest = coords[i];
        }
      }

      const crosshair = document.getElementById('chart-crosshair-x');
      const dot = document.getElementById('chart-crosshair-dot');
      if (crosshair && dot) {
        crosshair.setAttribute('x1', closest.x.toFixed(1));
        crosshair.setAttribute('x2', closest.x.toFixed(1));
        crosshair.style.display = 'block';
        dot.setAttribute('cx', closest.x.toFixed(1));
        dot.setAttribute('cy', closest.y.toFixed(1));
        dot.style.display = 'block';
      }

      if (tooltip) {
        const pt = closest.pt;
        const dt = new Date(pt.timestamp);
        const timeStr =
          dt.toLocaleString('en-IN', {
            timeZone: 'Asia/Kolkata',
            day: '2-digit',
            month: 'short',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
          }) + ' IST';

        const instEl = document.getElementById('tooltip-instrument');
        const timeEl = document.getElementById('tooltip-time');
        const priceEl = document.getElementById('tooltip-price');
        const changeEl = document.getElementById('tooltip-change');
        const volEl = document.getElementById('tooltip-volume');
        const volRow = document.getElementById('tooltip-vol-row');

        if (instEl) instEl.textContent = `${ChartState.activeSymbol} (${data.instrument_name || 'NSE'})`;
        if (timeEl) timeEl.textContent = timeStr;
        if (priceEl) priceEl.textContent = formatPriceINR(pt.close);
        if (changeEl) {
          const chg = pt.change || 0;
          const pct = pt.change_percent || 0;
          const sign = chg > 0 ? '+' : '';
          changeEl.textContent = `${sign}₹${chg.toFixed(2)} (${sign}${pct.toFixed(2)}%)`;
          changeEl.style.color = chg >= 0 ? '#10b981' : '#f43f5e';
        }
        if (volEl && volRow) {
          if (pt.volume !== null && pt.volume !== undefined) {
            volEl.textContent = Number(pt.volume).toLocaleString('en-IN');
            volRow.style.display = 'flex';
          } else {
            volRow.style.display = 'none';
          }
        }

        const wrapRect = svg.parentElement.getBoundingClientRect();
        let leftPx = e.clientX - wrapRect.left + 15;
        let topPx = e.clientY - wrapRect.top - 10;
        if (leftPx + 220 > wrapRect.width) {
          leftPx = e.clientX - wrapRect.left - 230;
        }
        tooltip.style.left = `${Math.max(10, leftPx)}px`;
        tooltip.style.top = `${Math.max(10, topPx)}px`;
        tooltip.style.display = 'block';
      }
    };

    svg.onmouseleave = function () {
      const crosshair = document.getElementById('chart-crosshair-x');
      const dot = document.getElementById('chart-crosshair-dot');
      if (crosshair) crosshair.style.display = 'none';
      if (dot) dot.style.display = 'none';
      if (tooltip) tooltip.style.display = 'none';
    };
  }

  // -------------------------------------------------------------------------
  // Dashboard Controller
  // -------------------------------------------------------------------------
  function initDashboard() {
    initInteractiveChart();

    const btnAnalyze = document.getElementById('dash-btn-analyze');
    if (btnAnalyze) {
      btnAnalyze.addEventListener('click', () => {
        const tabPredict = document.getElementById('tab-btn-predict');
        if (tabPredict) tabPredict.click();
        const input = document.getElementById('symbol-input');
        if (input) {
          input.value = 'BHARTIARTL';
          input.focus();
        }
      });
    }

    const btnAskAi = document.getElementById('dash-btn-ask-ai');
    if (btnAskAi) {
      btnAskAi.addEventListener('click', () => {
        openChatDrawer('What is the current technical momentum and fundamental outlook for BHARTIARTL?');
      });
    }

    const btnWhyFactors = document.getElementById('btn-dash-why-factors');
    if (btnWhyFactors) {
      btnWhyFactors.addEventListener('click', () => {
        const tabPredict = document.getElementById('tab-btn-predict');
        if (tabPredict) tabPredict.click();
        const whyCard = document.getElementById('res-why-prediction-card');
        if (whyCard) {
          whyCard.scrollIntoView({ behavior: 'smooth' });
        }
      });
    }
  }

  async function loadDashboard() {
    renderDashboardCatalog();
    loadInteractiveChart();

    try {
      const hist = await ApiService.fetchHistory({ symbol: 'BHARTIARTL', limit: 1 });
      if (hist && hist.items && hist.items.length > 0) {
        updateDashboardSnapshot(hist.items[0]);
      }
    } catch (e) {
      console.warn('Could not fetch latest history snapshot for dashboard:', e);
    }
  }

  function renderDashboardCatalog() {
    const grid = document.getElementById('dash-catalog-grid');
    if (!grid) return;
    if (!AppState.catalog || AppState.catalog.length === 0) {
      grid.innerHTML = '<div class="text-muted py-4">Loading instrument catalog...</div>';
      return;
    }

    grid.innerHTML = AppState.catalog.map((inst) => {
      const isReady = inst.capability_status === 'SUPPORTED_AND_READY' || inst.status === 'SUPPORTED';
      let statusBadge = '<span class="badge badge-success">Supported & Ready</span>';
      if (inst.capability_status === 'UNSUPPORTED_BY_CURRENT_MODEL') {
        statusBadge = '<span class="badge badge-warning">No Equity Model</span>';
      } else if (inst.capability_status === 'REQUIRES_SEPARATE_INDEX_PIPELINE' || inst.instrument_type === 'INDEX') {
        statusBadge = '<span class="badge badge-purple">Index Pipeline Required</span>';
      } else if (!isReady) {
        statusBadge = `<span class="badge badge-danger">${escapeHtml(inst.capability_status || inst.status)}</span>`;
      }

      const reasonText = escapeHtml(inst.reason || '');
      const prereqText = inst.actionable_prerequisite ? `<div class="catalog-prereq" style="font-size:0.75rem; color:#94a3b8; margin: 0.5rem 0;"><strong>Prerequisite:</strong> ${escapeHtml(inst.actionable_prerequisite)}</div>` : '';

      return `
        <div class="catalog-card ${isReady ? 'catalog-card-ready' : 'catalog-card-blocked'}">
          <div class="catalog-header" style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
            <div>
              <strong style="color:#f8fafc; font-size:1rem;">${escapeHtml(inst.symbol)}</strong>
              <span class="font-mono text-muted" style="font-size:0.75rem;">(${escapeHtml(inst.instrument_type)})</span>
            </div>
            ${statusBadge}
          </div>
          <div style="font-size:0.85rem; color:#e2e8f0; font-weight:500; margin-bottom:0.25rem;">${escapeHtml(inst.name)}</div>
          <div style="font-size:0.75rem; color:#94a3b8; line-height:1.4;">${reasonText}</div>
          ${prereqText}
          <div style="margin-top:0.75rem;">
            <button type="button" class="btn btn-outline btn-sm btn-select-catalog" data-symbol="${escapeHtml(inst.symbol)}" style="width:100%;">
              ${isReady ? 'Analyze Instrument →' : 'View Capabilities →'}
            </button>
          </div>
        </div>
      `;
    }).join('');

    grid.querySelectorAll('.btn-select-catalog').forEach((btn) => {
      btn.addEventListener('click', () => {
        const sym = btn.getAttribute('data-symbol');
        if (!sym) return;
        const tabPredict = document.getElementById('tab-btn-predict');
        if (tabPredict) tabPredict.click();
        const input = document.getElementById('symbol-input');
        if (input) {
          clearStalePredictionIfSymbolChanged(sym);
          input.value = sym;
          input.focus();
        }
      });
    });
  }

  function updateDashboardSnapshot(pred) {
    if (!pred) return;
    const priceEl = document.getElementById('dash-latest-price');
    const freshEl = document.getElementById('dash-freshness-status');
    const dirIndicator = document.getElementById('dash-dir-indicator');
    const dirIcon = document.getElementById('dash-dir-icon');
    const dirText = document.getElementById('dash-dir-text');
    const probDownVal = document.getElementById('dash-prob-down-val');
    const probUpVal = document.getElementById('dash-prob-up-val');
    const rangeBand = document.getElementById('dash-range-band');
    const modelBadge = document.getElementById('dash-model-badge');

    if (modelBadge && pred.model_name) {
      modelBadge.textContent = pred.model_name.toUpperCase();
    }

    if (pred.raw_result && pred.raw_result.quote_context) {
      const qc = pred.raw_result.quote_context;
      if (priceEl && typeof qc.last_price === 'number') {
        priceEl.textContent = formatPriceINR(qc.last_price);
      }
    }

    if (pred.predicted_direction) {
      const isUp = pred.predicted_direction === 'UP';
      if (dirText) {
        dirText.textContent = pred.predicted_direction;
        dirText.className = isUp ? 'dir-text text-emerald' : 'dir-text text-rose';
      }
      if (dirIcon) {
        dirIcon.textContent = isUp ? '📈' : '📉';
      }
      if (dirIndicator) {
        dirIndicator.className = isUp ? 'direction-indicator-badge up' : 'direction-indicator-badge down';
      }
    }

    const pUp = pred.probability_up;
    if (typeof pUp === 'number') {
      const pDown = 1.0 - pUp;
      if (probUpVal) probUpVal.textContent = `${(pUp * 100).toFixed(1)}%`;
      if (probDownVal) probDownVal.textContent = `${(pDown * 100).toFixed(1)}%`;
    }

    if (pred.raw_result && pred.raw_result.ensemble && pred.raw_result.ensemble.target_range) {
      const tr = pred.raw_result.ensemble.target_range;
      if (rangeBand && typeof tr.lower_bound === 'number' && typeof tr.upper_bound === 'number') {
        rangeBand.textContent = `${formatPriceINR(tr.lower_bound)} — ${formatPriceINR(tr.upper_bound)}`;
      }
    }
  }

  // -------------------------------------------------------------------------
  // Chat Assistant Controller
  // -------------------------------------------------------------------------
  function openChatDrawer(prefilledMessage) {
    const drawer = document.getElementById('chat-drawer');
    if (!drawer) return;
    drawer.classList.add('open');
    drawer.setAttribute('aria-hidden', 'false');
    const input = document.getElementById('chat-input-text');
    if (input) {
      if (prefilledMessage) {
        input.value = prefilledMessage;
        const form = document.getElementById('chat-input-form');
        if (form) form.requestSubmit();
      } else {
        input.focus();
      }
    }
  }

  function closeChatDrawer() {
    const drawer = document.getElementById('chat-drawer');
    if (!drawer) return;
    drawer.classList.remove('open');
    drawer.setAttribute('aria-hidden', 'true');
  }

  function renderMarkdownText(rawText) {
    if (!rawText) return '';
    let escaped = escapeHtml(rawText);

    // Headings
    escaped = escaped.replace(/^###\s+(.*$)/gim, '<h4 style="margin:0.5rem 0 0.25rem 0;color:#f8fafc;font-size:0.92rem;">$1</h4>');
    escaped = escaped.replace(/^##\s+(.*$)/gim, '<h3 style="margin:0.6rem 0 0.3rem 0;color:#f8fafc;font-size:1rem;">$1</h3>');

    // Blockquotes
    escaped = escaped.replace(/^&gt;\s+(.*$)/gim, '<blockquote>$1</blockquote>');

    // Bold and Italic
    escaped = escaped.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    escaped = escaped.replace(/\*(.*?)\*/g, '<em>$1</em>');

    // Inline code
    escaped = escaped.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Bullet lists
    const lines = escaped.split('\n');
    let inList = false;
    const formattedLines = [];
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      if (/^\s*[-*]\s+(.*)/.test(line)) {
        const itemContent = line.replace(/^\s*[-*]\s+/, '');
        if (!inList) {
          formattedLines.push('<ul>');
          inList = true;
        }
        formattedLines.push(`<li>${itemContent}</li>`);
      } else {
        if (inList) {
          formattedLines.push('</ul>');
          inList = false;
        }
        formattedLines.push(line);
      }
    }
    if (inList) formattedLines.push('</ul>');

    // Double line-break paragraphs
    const joined = formattedLines.join('\n');
    return joined
      .split('\n\n')
      .map((p) => p.trim())
      .filter((p) => p.length > 0)
      .map((p) => {
        if (p.startsWith('<h3>') || p.startsWith('<h4>') || p.startsWith('<ul>') || p.startsWith('<blockquote>')) {
          return p;
        }
        return `<p style="margin:0.35rem 0;">${p.replace(/\n/g, '<br>')}</p>`;
      })
      .join('');
  }

  function appendChatMessage(sender, text) {
    const container = document.getElementById('chat-messages-container');
    if (!container) return;

    const msgEl = document.createElement('div');
    msgEl.className = `chat-message ${sender}`;

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';

    if (sender === 'assistant') {
      bubble.innerHTML = renderMarkdownText(text);
    } else {
      const p = document.createElement('p');
      p.textContent = text;
      bubble.appendChild(p);
    }

    const timeSpan = document.createElement('span');
    timeSpan.className = 'message-time';
    const now = new Date();
    timeSpan.textContent = sender === 'user' ? 'You' : `AI Assistant • ${now.toLocaleTimeString('en-IN', { hour12: false, hour: '2-digit', minute: '2-digit' })}`;

    msgEl.appendChild(bubble);
    msgEl.appendChild(timeSpan);
    container.appendChild(msgEl);
    container.scrollTop = container.scrollHeight;
  }

  function initChatModule() {
    const btnOpen = document.getElementById('btn-open-chat');
    const btnClose = document.getElementById('btn-close-chat');
    const btnBlockedAsk = document.getElementById('btn-ask-chat-about-blocked');
    const form = document.getElementById('chat-input-form');
    const input = document.getElementById('chat-input-text');

    if (btnOpen) {
      btnOpen.addEventListener('click', () => openChatDrawer());
    }

    if (btnClose) {
      btnClose.addEventListener('click', () => closeChatDrawer());
    }

    if (btnBlockedAsk) {
      btnBlockedAsk.addEventListener('click', () => {
        const symInput = document.getElementById('symbol-input');
        const sym = (symInput && symInput.value.trim().toUpperCase()) || 'TCS';
        openChatDrawer(`Why is ${sym} blocked and what is required to enable forecasting for it?`);
      });
    }

    document.querySelectorAll('.chat-prompt-pill').forEach((pill) => {
      pill.addEventListener('click', () => {
        const promptText = pill.getAttribute('data-prompt');
        if (promptText) {
          openChatDrawer(promptText);
        }
      });
    });

    if (form) {
      form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const text = input ? input.value.trim() : '';
        if (!text) return;

        appendChatMessage('user', text);
        if (input) input.value = '';

        const container = document.getElementById('chat-messages-container');
        const typingEl = document.createElement('div');
        typingEl.className = 'chat-message assistant typing';
        typingEl.id = 'chat-typing-indicator';
        typingEl.innerHTML = '<div class="message-bubble"><span class="typing-dots">Evaluating evidence...</span></div>';
        if (container) {
          container.appendChild(typingEl);
          container.scrollTop = container.scrollHeight;
        }

        try {
          const activeSymbol = (AppState.prediction && AppState.prediction.symbol)
            || (document.getElementById('symbol-input') && document.getElementById('symbol-input').value.trim().toUpperCase())
            || 'BHARTIARTL';

          const res = await ApiService.sendChatMessage({
            message: text,
            instrument: activeSymbol,
            prediction_context: AppState.prediction ? {
              symbol: AppState.prediction.symbol,
              predicted_direction: AppState.prediction.predicted_direction,
              model_name: AppState.prediction.model_name,
              probability_up: AppState.prediction.probability_up,
              capability_status: AppState.prediction.capability_status,
              actionable_prerequisite: AppState.prediction.actionable_prerequisite,
              reason: AppState.prediction.error_message,
              why_prediction: AppState.prediction.why_prediction,
            } : null,
          });

          if (typingEl && typingEl.parentNode) {
            typingEl.parentNode.removeChild(typingEl);
          }

          appendChatMessage('assistant', res.reply || 'No response returned.');
        } catch (err) {
          if (typingEl && typingEl.parentNode) {
            typingEl.parentNode.removeChild(typingEl);
          }
          appendChatMessage('assistant', `⚠️ ${err.message || 'Error communicating with Chat Assistant. Please check if backend is running.'}`);
        }
      });
    }
  }

  // -------------------------------------------------------------------------
  // Prediction Engine Controller
  // -------------------------------------------------------------------------
  function initPredictionEngine() {
    const form = document.getElementById('prediction-form');
    const symbolInput = document.getElementById('symbol-input');
    const symbolError = document.getElementById('symbol-error');
    const modelSelect = document.getElementById('model-select');
    const mlWeightSlider = document.getElementById('ml-weight-slider');
    const weightDisplay = document.getElementById('weight-display');
    const ensembleWeightsGroup = document.getElementById('ensemble-weights-group');
    const btnPredict = document.getElementById('btn-run-prediction');
    const btnText = document.getElementById('btn-predict-text');
    const alertBanner = document.getElementById('prediction-alert');
    const alertMsg = document.getElementById('alert-message');
    const alertClose = document.getElementById('alert-close-btn');

    // Quick chips
    document.querySelectorAll('.chip').forEach((chip) => {
      chip.addEventListener('click', () => {
        const sym = chip.getAttribute('data-symbol');
        if (sym && symbolInput) {
          clearStalePredictionIfSymbolChanged(sym);
          symbolInput.value = sym;
          symbolInput.focus();
          if (symbolError) symbolError.textContent = '';
        }
      });
    });

    // Clear stale prediction on symbol input change
    if (symbolInput) {
      symbolInput.addEventListener('input', () => {
        clearStalePredictionIfSymbolChanged(symbolInput.value.trim().toUpperCase());
      });
    }

    // Toggle custom weights visibility depending on model
    if (modelSelect && ensembleWeightsGroup) {
      modelSelect.addEventListener('change', () => {
        const isEnsemble = modelSelect.value === 'ensemble';
        ensembleWeightsGroup.style.display = isEnsemble ? 'flex' : 'none';
      });
    }

    // Weight slider display update
    if (mlWeightSlider && weightDisplay) {
      mlWeightSlider.addEventListener('input', () => {
        const mlVal = parseInt(mlWeightSlider.value, 10);
        const llmVal = 100 - mlVal;
        weightDisplay.textContent = `${mlVal}% ML / ${llmVal}% LLM`;
      });
    }

    // Dismiss alert
    if (alertClose && alertBanner) {
      alertClose.addEventListener('click', () => {
        alertBanner.style.display = 'none';
      });
    }

    // Retry prediction action in alert banner
    const alertRetryBtn = document.getElementById('alert-retry-btn');
    if (alertRetryBtn && form) {
      alertRetryBtn.addEventListener('click', () => {
        if (alertBanner) alertBanner.style.display = 'none';
        if (AppState.lastPredictionPayload) {
          if (symbolInput && AppState.lastPredictionPayload.symbol) {
            symbolInput.value = AppState.lastPredictionPayload.symbol;
          }
          if (modelSelect && AppState.lastPredictionPayload.model_name) {
            modelSelect.value = AppState.lastPredictionPayload.model_name;
            if (ensembleWeightsGroup) {
              ensembleWeightsGroup.style.display = modelSelect.value === 'ensemble' ? 'flex' : 'none';
            }
          }
        }
        form.requestSubmit();
      });
    }

    // Switch to supported instrument in blocked card
    const btnSwitchSupported = document.getElementById('btn-switch-to-supported');
    if (btnSwitchSupported) {
      btnSwitchSupported.addEventListener('click', () => {
        clearStalePredictionIfSymbolChanged('BHARTIARTL');
        if (symbolInput) {
          symbolInput.value = 'BHARTIARTL';
          symbolInput.focus();
          if (symbolError) symbolError.textContent = '';
        }
        const blockedCard = document.getElementById('result-blocked-card');
        const emptyState = document.getElementById('predict-empty-state');
        if (blockedCard) blockedCard.style.display = 'none';
        if (emptyState) emptyState.style.display = 'block';
      });
    }

    // Form submission
    if (form) {
      form.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (symbolError) symbolError.textContent = '';
        if (alertBanner) alertBanner.style.display = 'none';

        const rawSymbol = symbolInput ? symbolInput.value.trim().toUpperCase() : '';
        if (!rawSymbol) {
          if (symbolError) symbolError.textContent = 'Please enter an equity ticker symbol (e.g. RELIANCE).';
          if (symbolInput) symbolInput.focus();
          return;
        }

        // Guard against duplicate concurrent submissions
        if (AppState.isPredicting) return;
        AppState.isPredicting = true;

        AppState.predictionRequestId = (AppState.predictionRequestId || 0) + 1;
        const currentReqId = AppState.predictionRequestId;

        const selectedModel = modelSelect ? modelSelect.value : 'ensemble';
        const lookbackInput = document.getElementById('lookback-days-input');
        const maxStaleInput = document.getElementById('max-stale-days-input');
        const persistCheckbox = document.getElementById('persist-checkbox');

        const lookback = lookbackInput ? parseInt(lookbackInput.value, 10) : 1825;
        const maxStale = maxStaleInput ? parseInt(maxStaleInput.value, 10) : 7;
        const shouldPersist = persistCheckbox ? persistCheckbox.checked : true;

        const payload = {
          symbol: rawSymbol,
          model_name: selectedModel,
          lookback_days: isNaN(lookback) ? 1825 : lookback,
          max_stale_days: isNaN(maxStale) ? 7 : maxStale,
          allow_stale_data: true,
          persist: shouldPersist,
        };

        if (selectedModel === 'ensemble' && mlWeightSlider) {
          const mlWeight = parseFloat(mlWeightSlider.value) / 100.0;
          payload.ml_weight = mlWeight;
          payload.llm_weight = Math.round((1.0 - mlWeight) * 100) / 100.0;
        }

        // Cache last submitted payload for exact retry reuse
        AppState.lastPredictionPayload = payload;

        // Set Loading State
        setPredictionLoading(true);

        try {
          const result = await ApiService.runPrediction(payload);
          // Drop stale out-of-order response
          if (currentReqId !== AppState.predictionRequestId) return;
          AppState.prediction = result;
          renderPredictionResult(result);
        } catch (err) {
          if (currentReqId !== AppState.predictionRequestId) return;
          showPredictionError(err.message || 'An unexpected error occurred during prediction inference.');
        } finally {
          if (currentReqId === AppState.predictionRequestId) {
            setPredictionLoading(false);
          }
        }
      });
    }
  }

  function setPredictionLoading(isLoading) {
    AppState.isPredicting = isLoading;
    const btn = document.getElementById('btn-run-prediction');
    const skeleton = document.getElementById('prediction-loading-skeleton');
    const resultsContainer = document.getElementById('prediction-results-container');
    const emptyState = document.getElementById('predict-empty-state');
    const blockedCard = document.getElementById('result-blocked-card');
    const heroCard = document.getElementById('result-hero-card');

    if (btn) {
      btn.disabled = isLoading;
      if (isLoading) {
        btn.classList.add('loading');
        const btnText = document.getElementById('btn-predict-text');
        if (btnText) btnText.textContent = 'Analyzing Market Data...';
      } else {
        btn.classList.remove('loading');
        const btnText = document.getElementById('btn-predict-text');
        if (btnText) btnText.textContent = 'Generate Prediction';
      }
    }

    // Disable / enable quick instrument selection chips during request
    document.querySelectorAll('.chip').forEach((chip) => {
      chip.disabled = isLoading;
    });

    if (isLoading) {
      if (emptyState) emptyState.style.display = 'none';
      if (resultsContainer) resultsContainer.style.display = 'none';
      if (heroCard) heroCard.style.display = 'none';
      if (blockedCard) blockedCard.style.display = 'none';
      if (skeleton) skeleton.style.display = 'flex';
    } else {
      if (skeleton) skeleton.style.display = 'none';
    }
  }

  function showPredictionError(msg, isRetryable = true) {
    const alertBanner = document.getElementById('prediction-alert');
    const alertMsg = document.getElementById('alert-message');
    const alertRetryBtn = document.getElementById('alert-retry-btn');
    const resultsContainer = document.getElementById('prediction-results-container');
    const emptyState = document.getElementById('predict-empty-state');
    const heroCard = document.getElementById('result-hero-card');
    const blockedCard = document.getElementById('result-blocked-card');
    const breakdownGrid = document.querySelector('.breakdown-grid');
    const emptyTitle = document.querySelector('#predict-empty-state .empty-state-title');
    const emptyText = document.querySelector('#predict-empty-state .empty-state-text');

    AppState.prediction = null;
    if (emptyTitle) emptyTitle.textContent = 'Prediction unavailable';
    if (emptyText) emptyText.textContent = 'No prediction was returned. Review the notice above and retry when the service is available.';
    if (alertBanner && alertMsg) {
      alertMsg.textContent = msg;
      if (alertRetryBtn) alertRetryBtn.style.display = isRetryable ? 'inline-block' : 'none';
      alertBanner.style.display = 'flex';
    }
    if (resultsContainer) resultsContainer.style.display = 'none';
    if (heroCard) heroCard.style.display = 'none';
    if (blockedCard) blockedCard.style.display = 'none';
    if (breakdownGrid) breakdownGrid.style.display = 'none';
    if (emptyState) emptyState.style.display = 'block';
  }

  function renderPredictionResult(res) {
    if (!res || typeof res !== 'object') {
      showPredictionError('Received invalid or empty prediction response from server.');
      return;
    }
    const container = document.getElementById('prediction-results-container');
    const emptyState = document.getElementById('predict-empty-state');
    const heroCard = document.getElementById('result-hero-card');
    const blockedCard = document.getElementById('result-blocked-card');
    const breakdownGrid = document.querySelector('.breakdown-grid');
    if (!container) return;

    if (emptyState) emptyState.style.display = 'none';
    container.style.display = 'block';

    // Handle Blocked / Unsupported Instrument or Failed Prediction state
    const isSuccess = res.status === 'SUCCESS' && !!(res.predicted_direction || res.direction);
    if (!isSuccess) {
      if (heroCard) heroCard.style.display = 'none';
      if (breakdownGrid) breakdownGrid.style.display = 'none';
      const whyCard = document.getElementById('res-why-prediction-card');
      if (whyCard) whyCard.style.display = 'none';

      if (blockedCard) {
        blockedCard.style.display = 'block';
        const titleEl = document.getElementById('blocked-card-title');
        const badgeEl = document.getElementById('blocked-card-badge');
        const descEl = document.getElementById('blocked-card-desc');
        const detailsEl = document.getElementById('blocked-card-details');

        const inst = AppState.catalog ? AppState.catalog.find((i) => i.symbol === res.symbol) : null;
        const capStatus = res.capability_status || (inst ? inst.capability_status : (res.status || 'BLOCKED'));
        const prereq = res.actionable_prerequisite || (inst ? inst.actionable_prerequisite : 'Train dedicated model before enabling.');
        const reason = res.error_message || (inst ? inst.reason : `Inference could not be completed. Status: ${res.status || 'UNKNOWN'}`);

        if (titleEl) {
          titleEl.textContent = `${res.symbol || 'Instrument'}: ${capStatus.replace(/_/g, ' ')}`;
        }
        if (badgeEl) {
          badgeEl.textContent = `STATUS - ${res.status || 'UNAVAILABLE'}`;
          badgeEl.className = 'badge ' + (capStatus.includes('INDEX') ? 'badge-purple' : 'badge-warning');
        }
        const msgEl = document.getElementById('blocked-card-message');
        if (msgEl) {
          msgEl.textContent = reason;
        } else if (descEl) {
          descEl.textContent = reason;
        }
        if (detailsEl) {
          detailsEl.innerHTML = `
            <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid var(--border-subtle); border-radius: 6px; padding: 0.85rem; margin-top: 0.75rem;">
              <div style="margin-bottom: 0.5rem;">
                <span style="font-size: 0.72rem; color: var(--text-dim); text-transform: uppercase; font-weight: 700;">Capability Status:</span>
                <span class="font-mono text-bold" style="color: #f59e0b; margin-left: 0.5rem;">${escapeHtml(capStatus)}</span>
              </div>
              <div style="margin-bottom: 0.5rem;">
                <span style="font-size: 0.72rem; color: var(--text-dim); text-transform: uppercase; font-weight: 700;">Actionable Prerequisite:</span>
                <span style="color: #e2e8f0; margin-left: 0.5rem;">${escapeHtml(prereq)}</span>
              </div>
              <div>
                <span style="font-size: 0.72rem; color: var(--text-dim); text-transform: uppercase; font-weight: 700;">Verified Reason:</span>
                <span style="color: #cbd5e1; margin-left: 0.5rem;">${escapeHtml(reason)}</span>
              </div>
            </div>
          `;
        }
      }
      return;
    }

    // Success State: show hero card and breakdown grid, hide blocked card
    if (blockedCard) blockedCard.style.display = 'none';
    if (heroCard) heroCard.style.display = 'block';
    if (breakdownGrid) breakdownGrid.style.display = 'grid';

    const symEl = document.getElementById('res-symbol');
    const instTypeBadge = document.getElementById('res-instrument-type-badge');
    const statusBadge = document.getElementById('res-status-badge');
    const modelBadge = document.getElementById('res-model-badge');
    const tsEl = document.getElementById('res-timestamp');
    const dirBadge = document.getElementById('res-direction-badge');
    const dirIcon = document.getElementById('res-direction-icon');
    const dirText = document.getElementById('res-direction-text');

    // Instrument metadata
    const inst = AppState.catalog ? AppState.catalog.find((i) => i.symbol === res.symbol) : null;
    const isIndex = (inst && inst.instrument_type === 'INDEX') || (res.symbol && (res.symbol.includes('NIFTY') || res.symbol.includes('INDEX')));
    const instType = inst ? inst.instrument_type : (isIndex ? 'INDEX' : 'EQUITY');
    if (symEl) symEl.textContent = res.symbol;
    if (instTypeBadge) {
      instTypeBadge.textContent = `${instType} (NSE)`;
      instTypeBadge.className = 'badge ' + (isIndex ? 'badge-purple' : 'badge-instrument-type');
    }
    if (statusBadge) {
      statusBadge.textContent = res.status || 'SUCCESS';
      statusBadge.className = 'badge badge-status-success';
    }
    if (modelBadge) {
      const modelName = (res.model_name || 'quantitative').toUpperCase();
      const modelVer = res.model_version ? ` (${res.model_version})` : '';
      modelBadge.textContent = `${modelName}${modelVer}`;
      modelBadge.className = 'badge ' + (res.model_name === 'ensemble' ? 'badge-purple' : 'badge-info');
    }
    const routingBadge = document.getElementById('res-routing-badge');
    if (routingBadge) {
      if (res.routing_metadata) {
        routingBadge.textContent = `Auto-Routed: ${res.routing_metadata.pipeline_type || 'Ensemble'}`;
      } else {
        routingBadge.textContent = `Auto-Routed: ${(res.model_name || 'Ensemble').toUpperCase()}`;
      }
    }
    if (tsEl) tsEl.textContent = formatDateTimeIST(res.prediction_timestamp);

    // Uncalibrated Warning Banner
    const uncalBanner = document.getElementById('res-uncalibrated-banner');
    if (uncalBanner) uncalBanner.style.display = 'flex';

    const dir = res.predicted_direction || res.direction;
    const horizonEl = document.getElementById('res-forecast-horizon');
    if (horizonEl) horizonEl.textContent = 'Next Trading Session (Close-to-Close)';

    // 1. Direction Decision & Accessibility (never color alone)
    if (heroCard) {
      heroCard.classList.remove('direction-up', 'direction-down');
      if (dir === 'UP') heroCard.classList.add('direction-up');
      if (dir === 'DOWN') heroCard.classList.add('direction-down');
    }

    if (dirBadge && dirIcon && dirText) {
      dirBadge.className = 'direction-badge';
      if (dir === 'UP') {
        dirBadge.classList.add('up');
        dirIcon.textContent = '↗';
        dirText.textContent = 'PREDICTED UP (Bullish Return)';
        dirBadge.setAttribute('aria-label', 'Predicted Direction: UP (Bullish Return)');
      } else if (dir === 'DOWN') {
        dirBadge.classList.add('down');
        dirIcon.textContent = '↘';
        dirText.textContent = 'PREDICTED DOWN (Bearish Return)';
        dirBadge.setAttribute('aria-label', 'Predicted Direction: DOWN (Bearish Return)');
      } else {
        dirBadge.classList.add('neutral');
        dirIcon.textContent = '⏸';
        dirText.textContent = dir ? `PREDICTED ${dir} (Flat Return)` : 'NEUTRAL (Flat Return)';
        dirBadge.setAttribute('aria-label', `Predicted Direction: ${dir || 'NEUTRAL'}`);
      }
    }

    // 2. Primary Grounded Reason Box
    const reasonTextEl = document.getElementById('res-primary-reason-text');
    if (reasonTextEl) {
      let groundReason = res.reason;
      if (!groundReason && res.explanation && res.explanation.summary) {
        groundReason = res.explanation.summary;
      }
      if (!groundReason && res.ensemble && res.ensemble.llm_reasoning_summary) {
        groundReason = res.ensemble.llm_reasoning_summary;
      }
      if (!groundReason) {
        const pUpVal = typeof res.probability_up === 'number' ? ` (P(UP)=${(res.probability_up * 100).toFixed(1)}%)` : '';
        groundReason = `Quantitative feature analysis projects ${dir || 'neutral'} momentum for ${res.symbol}${pUpVal}, grounded in moving averages, RSI, and MACD technical indicators.`;
      }
      reasonTextEl.textContent = groundReason;
    }

    // 3. Price Strip: Latest Price, Opening Price, Previous Close, Daily Change
    const obsPriceEl = document.getElementById('res-observed-price');
    const obsMetaEl = document.getElementById('res-observed-meta');
    const openPriceEl = document.getElementById('res-opening-price');
    const openStatusEl = document.getElementById('res-opening-status');
    const prevCloseEl = document.getElementById('res-prev-close');
    const dailyChangeEl = document.getElementById('res-daily-change');
    const dailyChangePctEl = document.getElementById('res-daily-change-pct');

    const qc = res.quote_context || res.market_quote || {};
    const lastPrice = typeof qc.last_price === 'number' ? qc.last_price : null;
    const priceTime = qc.price_timestamp;
    const source = qc.source || 'yfinance';
    const sessionState = qc.session_state || 'CLOSED';
    const isDelayed = typeof qc.is_delayed === 'boolean' ? qc.is_delayed : true;

    // Field 4: Latest Price
    if (obsPriceEl) {
      if (typeof lastPrice === 'number') {
        obsPriceEl.textContent = formatPriceINR(lastPrice);
      } else {
        obsPriceEl.textContent = '₹--';
      }
    }
    const forecastMetaEl = document.getElementById('res-forecast-meta');
    if (forecastMetaEl) {
      forecastMetaEl.textContent = 'Price Target: Unsupported / Not Modeled (Direction Only)';
    }
    if (obsMetaEl) {
      const pType = (res.quote_context && res.quote_context.price_type) ? (res.quote_context.price_type || 'LAST_TRADED_PRICE') : 'LAST_TRADED_PRICE';
      const timeStr = priceTime ? formatDateTimeIST(priceTime) : '--';
      const delayLabel = isDelayed ? 'Delayed ~15m' : 'Real-time';
      const stateLabel = sessionState === 'REGULAR_HOURS' ? 'Trading Session Active' : 'Confirmed Close';
      obsMetaEl.textContent = `${delayLabel} • ${pType} • ${stateLabel} • As of ${timeStr}`;
    }

    // Field 3: Session Opening Price
    if (openPriceEl && openStatusEl) {
      if (sessionState === 'REGULAR_HOURS' && typeof qc.open_price === 'number' && qc.open_price > 0) {
        openPriceEl.textContent = formatPriceINR(qc.open_price);
        openStatusEl.textContent = 'Observed Session Open';
        openStatusEl.style.color = '#10b981';
      } else {
        openPriceEl.textContent = 'Unavailable / Pre-Market';
        openStatusEl.textContent = 'Not yet observed (Before Open)';
        openStatusEl.style.color = '#94a3b8';
      }
    }

    // Previous Close
    if (prevCloseEl) {
      if (typeof qc.previous_close === 'number' && qc.previous_close > 0) {
        prevCloseEl.textContent = formatPriceINR(qc.previous_close);
      } else {
        prevCloseEl.textContent = '₹--';
      }
    }

    // Compact Daily Change & %
    if (dailyChangeEl && dailyChangePctEl) {
      if (typeof qc.change === 'number' && typeof qc.change_percent === 'number') {
        const sign = qc.change > 0 ? '+' : '';
        dailyChangeEl.textContent = `${sign}₹${Math.abs(qc.change).toFixed(2)}`;
        dailyChangePctEl.textContent = `${sign}${qc.change_percent.toFixed(2)}%`;
        const color = qc.change >= 0 ? '#10b981' : '#f43f5e';
        dailyChangeEl.style.color = color;
        dailyChangePctEl.style.color = color;
      } else {
        dailyChangeEl.textContent = '--';
        dailyChangePctEl.textContent = '--%';
        dailyChangeEl.style.color = '#f8fafc';
        dailyChangePctEl.style.color = '#94a3b8';
      }
    }

    if (dirBadge && dirIcon && dirText) {
      dirBadge.className = 'direction-badge';
      if (dir === 'UP') {
        dirBadge.classList.add('up');
        dirIcon.textContent = '↗';
        dirText.textContent = 'PREDICTED UP (Bullish Return)';
        dirBadge.setAttribute('aria-label', 'Predicted Direction: UP (Bullish Return)');
      } else if (dir === 'DOWN') {
        dirBadge.classList.add('down');
        dirIcon.textContent = '↘';
        dirText.textContent = 'PREDICTED DOWN (Bearish Return)';
        dirBadge.setAttribute('aria-label', 'Predicted Direction: DOWN (Bearish Return)');
      } else {
        dirBadge.classList.add('neutral');
        dirIcon.textContent = '⏸';
        dirText.textContent = dir ? `PREDICTED ${dir} (Flat Return)` : 'NEUTRAL (Flat Return)';
        dirBadge.setAttribute('aria-label', `Predicted Direction: ${dir || 'NEUTRAL'}`);
      }
    }

    // Probabilities Bar - Never substitute 50% for missing probability
    let probUp = null;
    let probDown = null;
    if (typeof res.probability_up === 'number' && !isNaN(res.probability_up)) {
      probUp = res.probability_up;
    } else if (res.probabilities && typeof res.probabilities.UP === 'number' && !isNaN(res.probabilities.UP)) {
      probUp = res.probabilities.UP;
    }

    if (typeof res.probability_down === 'number' && !isNaN(res.probability_down)) {
      probDown = res.probability_down;
    } else if (res.probabilities && typeof res.probabilities.DOWN === 'number' && !isNaN(res.probabilities.DOWN)) {
      probDown = res.probabilities.DOWN;
    } else if (probUp !== null) {
      probDown = 1.0 - probUp;
    }

    const hasProbUp = probUp !== null;
    const hasProbDown = probDown !== null;

    const fillEl = document.getElementById('res-probability-fill');
    const probUpEl = document.getElementById('res-prob-up');
    const probDownEl = document.getElementById('res-prob-down');

    if (hasProbUp) {
      if (fillEl) fillEl.style.width = `${Math.max(0, Math.min(100, probUp * 100)).toFixed(1)}%`;
      if (probUpEl) probUpEl.textContent = `P(UP): ${(probUp * 100).toFixed(1)}% [Uncalibrated]`;
      if (probDownEl) probDownEl.textContent = `P(DOWN): ${(probDown * 100).toFixed(1)}% [Uncalibrated]`;
    } else {
      if (fillEl) fillEl.style.width = '0%';
      if (probUpEl) probUpEl.textContent = 'P(UP): --';
      if (probDownEl) probDownEl.textContent = 'P(DOWN): --';
    }

    // Target Range Box - Only display when supported by actual numerical response
    const targetRangeItem = document.getElementById('target-range-metric-item');
    const rangeLower = document.getElementById('res-range-lower');
    const rangeRef = document.getElementById('res-range-ref');
    const rangeUpper = document.getElementById('res-range-upper');

    if (
      res.ensemble &&
      res.ensemble.target_range &&
      typeof res.ensemble.target_range.reference_price === 'number' &&
      typeof res.ensemble.target_range.lower_bound === 'number' &&
      typeof res.ensemble.target_range.upper_bound === 'number'
    ) {
      const tr = res.ensemble.target_range;
      if (rangeLower) rangeLower.textContent = formatPriceINR(tr.lower_bound);
      if (rangeRef) rangeRef.textContent = formatPriceINR(tr.reference_price);
      if (rangeUpper) rangeUpper.textContent = formatPriceINR(tr.upper_bound);
      if (targetRangeItem) targetRangeItem.style.display = 'flex';
    } else {
      if (targetRangeItem) targetRangeItem.style.display = 'none';
    }

    // Model Limitations & Recommended Next Action Box
    const nextActionEl = document.getElementById('res-next-action-text');
    if (nextActionEl) {
      nextActionEl.textContent = 'Review verified actuals in the History tab once next market session closes (15:30 IST).';
    }

    // Agreement Banner (Ensemble only)
    const agreementBanner = document.getElementById('res-agreement-banner');
    const agreementBadge = document.getElementById('res-agreement-badge');
    const agreementDesc = document.getElementById('res-agreement-desc');
    const agreementIcon = document.getElementById('res-agreement-icon');

    if (res.ensemble && agreementBanner) {
      const status = res.ensemble.agreement_status;
      agreementBanner.style.display = 'flex';
      agreementBanner.className = 'agreement-banner';

      if (status === 'STRONG_AGREEMENT') {
        agreementBanner.classList.add('strong');
        agreementIcon.textContent = '🛡️';
        agreementBadge.textContent = 'STRONG AGREEMENT';
        agreementBadge.className = 'badge badge-success';
        agreementDesc.textContent = 'Both quantitative ML and qualitative LLM exhibit strong consensus for this directional signal.';
      } else if (status === 'DIVERGENCE') {
        agreementBanner.classList.add('divergence');
        agreementIcon.textContent = '⚠️';
        agreementBadge.textContent = 'DIVERGENCE WARNING';
        agreementBadge.className = 'badge badge-warning';
        agreementDesc.textContent = 'Conflicting signals: Quantitative models and qualitative contextual reasoning diverge. Higher market risk detected.';
      } else if (status === 'AGREEMENT') {
        agreementBanner.classList.add('strong');
        agreementIcon.textContent = '🤝';
        agreementBadge.textContent = 'AGREEMENT';
        agreementBadge.className = 'badge badge-info';
        agreementDesc.textContent = 'Both models forecast identical direction.';
      } else {
        agreementIcon.textContent = '📊';
        agreementBadge.textContent = status;
        agreementBadge.className = 'badge badge-info';
        agreementDesc.textContent = `Ensemble status: ${status}.`;
      }
    } else if (agreementBanner) {
      agreementBanner.style.display = 'none';
    }

    // Column 1: ML Breakdown Card (Strictly Quantitative ML Outputs)
    document.getElementById('ml-dir-val').textContent = res.predicted_direction || '--';
    document.getElementById('ml-prob-up-val').textContent = hasProbUp ? `${(res.probability_up * 100).toFixed(1)}%` : '--';
    
    const dq = res.data_quality;
    if (dq) {
      document.getElementById('ml-warmup-val').textContent = dq.warmup_complete ? `Complete (${dq.cleaned_bars} bars)` : `Incomplete (${dq.cleaned_bars}/34)`;
      document.getElementById('ml-input-ts-val').textContent = formatDateTimeIST(dq.latest_bar_timestamp);
      document.getElementById('ml-staleness-val').textContent = dq.is_stale ? `Stale (${dq.stale_days} days)` : 'Fresh (<7d)';
      document.getElementById('audit-bars-fetched').textContent = dq.total_bars_fetched;
      document.getElementById('audit-bars-cleaned').textContent = dq.cleaned_bars;
    }

    // Model Diagnostic Attributes List - Never fabricate tree split factors
    const mlFactorsList = document.getElementById('ml-factors-list');
    if (mlFactorsList) {
      mlFactorsList.innerHTML = '';
      const li1 = document.createElement('li');
      li1.textContent = `Model Architecture: ${res.model_name || 'quantitative'} (${res.model_version || 'v1'})`;
      const li2 = document.createElement('li');
      li2.textContent = `Probability Calibration: ${res.probability_calibration || 'uncalibrated'}`;
      mlFactorsList.appendChild(li1);
      mlFactorsList.appendChild(li2);
    }

    // Column 2: Qualitative LLM Reasoning Card (Strictly Actual API-Returned Reasoning)
    const llmStanceEl = document.getElementById('llm-stance-val');
    const llmConfEl = document.getElementById('llm-conf-val');
    const llmSummaryEl = document.getElementById('llm-summary-text');
    const llmPositiveList = document.getElementById('llm-positive-factors');
    const llmDownsideList = document.getElementById('llm-downside-risks');
    const llmSourcesTags = document.getElementById('llm-sources-tags');

    if (res.ensemble && res.ensemble.llm_reasoning_summary) {
      llmStanceEl.textContent = res.ensemble.llm_direction || '--';
      llmConfEl.textContent = res.ensemble.llm_confidence || 'Not provided';
      llmSummaryEl.textContent = res.ensemble.llm_reasoning_summary;

      // Positive Catalysts
      llmPositiveList.innerHTML = '';
      const pos = res.ensemble.integrated_positive_factors || [];
      if (pos.length > 0) {
        pos.forEach((p) => {
          const li = document.createElement('li');
          li.textContent = p;
          llmPositiveList.appendChild(li);
        });
      } else {
        llmPositiveList.innerHTML = '<li>None returned by API.</li>';
      }

      // Downside Risks
      llmDownsideList.innerHTML = '';
      const risks = res.ensemble.downside_risks || [];
      if (risks.length > 0) {
        risks.forEach((r) => {
          const li = document.createElement('li');
          li.textContent = r;
          llmDownsideList.appendChild(li);
        });
      } else {
        llmDownsideList.innerHTML = '<li>None returned by API.</li>';
      }

      // Citations / Sources
      llmSourcesTags.innerHTML = '';
      const sources = res.ensemble.source_references || [];
      if (sources.length > 0) {
        sources.forEach((s) => {
          const span = document.createElement('span');
          span.className = 'source-tag';
          span.textContent = s;
          llmSourcesTags.appendChild(span);
        });
      } else {
        llmSourcesTags.textContent = 'None returned by API.';
      }
    } else {
      llmStanceEl.textContent = 'Not requested / Not returned';
      llmConfEl.textContent = 'Not requested / Not returned';
      llmSummaryEl.textContent = 'Qualitative LLM reasoning was not returned by the API for this prediction.';
      llmPositiveList.innerHTML = '<li>No qualitative catalysts returned.</li>';
      llmDownsideList.innerHTML = '<li>No qualitative risks returned.</li>';
      llmSourcesTags.textContent = 'None.';
    }

    // Column 3: Audit Card
    document.getElementById('audit-id-val').textContent = res.prediction_id || 'Not Persisted';
    document.getElementById('audit-disclaimer-text').textContent = res.disclaimer || 'Standard research disclaimer.';

    // Section 4: Why This Prediction? Evidence Breakdown
    const whyCard = document.getElementById('res-why-prediction-card');
    const whyInputTs = document.getElementById('why-input-timestamp');
    const whyTechnical = document.getElementById('why-technical-content');
    const whyQualitative = document.getElementById('why-qualitative-content');
    const whySources = document.getElementById('why-sources-content');

    if (whyCard) {
      whyCard.style.display = 'block';
      if (whyInputTs) {
        const inputTs = (res.data_quality && res.data_quality.latest_bar_timestamp) || res.prediction_timestamp;
        whyInputTs.textContent = formatDateTimeIST(inputTs);
      }
      if (whyTechnical) {
        const pUpPct = hasProbUp ? `${(probUp * 100).toFixed(1)}%` : '--%';
        whyTechnical.textContent = `Signal direction: ${dir} with estimated P(UP)=${pUpPct}. Evaluated across 37 technical momentum, volatility, and trend indicators.`;
      }
      if (whyQualitative) {
        if (res.ensemble && res.ensemble.llm_reasoning_summary) {
          whyQualitative.textContent = `${res.ensemble.llm_reasoning_summary} (Model: ${res.ensemble.llm_model_name || 'Gemma 3 12B'})`;
        } else {
          whyQualitative.textContent = 'Qualitative contextual reasoning was not requested or not generated for this model run.';
        }
      }
      if (whySources) {
        const sources = (res.ensemble && res.ensemble.source_references) || [];
        if (sources.length > 0) {
          whySources.innerHTML = sources.map((s) => `<span class="source-tag">${escapeHtml(s)}</span>`).join(' ');
        } else {
          whySources.textContent = 'No external news citations attached.';
        }
      }
    }
  }

  // -------------------------------------------------------------------------
  // Prediction History Controller
  // -------------------------------------------------------------------------
  function initHistoryModule() {
    const btnRefresh = document.getElementById('btn-refresh-history');
    const symbolFilter = document.getElementById('history-symbol-filter');
    const modelFilter = document.getElementById('history-model-filter');
    const limitSelect = document.getElementById('history-limit-select');
    const btnPrev = document.getElementById('btn-history-prev');
    const btnNext = document.getElementById('btn-history-next');

    if (btnRefresh) {
      btnRefresh.addEventListener('click', () => loadHistory());
    }

    if (symbolFilter) {
      let debounceTimer;
      symbolFilter.addEventListener('input', () => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
          AppState.history.symbolFilter = symbolFilter.value.trim().toUpperCase();
          AppState.history.offset = 0;
          loadHistory();
        }, 300);
      });
    }

    if (modelFilter) {
      modelFilter.addEventListener('change', () => {
        AppState.history.modelFilter = modelFilter.value;
        AppState.history.offset = 0;
        loadHistory();
      });
    }

    if (limitSelect) {
      limitSelect.addEventListener('change', () => {
        AppState.history.limit = parseInt(limitSelect.value, 10);
        AppState.history.offset = 0;
        loadHistory();
      });
    }

    if (btnPrev) {
      btnPrev.addEventListener('click', () => {
        if (AppState.history.offset >= AppState.history.limit) {
          AppState.history.offset -= AppState.history.limit;
          loadHistory();
        }
      });
    }

    if (btnNext) {
      btnNext.addEventListener('click', () => {
        if (AppState.history.offset + AppState.history.limit < AppState.history.total) {
          AppState.history.offset += AppState.history.limit;
          loadHistory();
        }
      });
    }
  }

  async function loadHistory() {
    const tbody = document.getElementById('history-table-body');
    const infoEl = document.getElementById('history-pagination-info');
    const btnPrev = document.getElementById('btn-history-prev');
    const btnNext = document.getElementById('btn-history-next');

    if (tbody) {
      tbody.innerHTML = '<tr><td colspan="7" class="text-center py-8 text-muted">Fetching audit records...</td></tr>';
    }

    AppState.history.isLoading = true;

    try {
      const data = await ApiService.fetchHistory({
        symbol: AppState.history.symbolFilter,
        model_name: AppState.history.modelFilter,
        limit: AppState.history.limit,
        offset: AppState.history.offset,
      });

      AppState.history.items = data.items || [];
      AppState.history.total = data.total || 0;

      renderHistoryTable(data.items || []);

      // Update Pagination Info
      const start = data.total === 0 ? 0 : data.offset + 1;
      const end = Math.min(data.offset + data.limit, data.total);
      if (infoEl) infoEl.textContent = `Showing ${start}-${end} of ${data.total} records`;

      if (btnPrev) btnPrev.disabled = data.offset <= 0;
      if (btnNext) btnNext.disabled = data.offset + data.limit >= data.total;

      // Concurrently load comparative model metrics (Phase 15)
      loadComparison();

    } catch (err) {
      if (tbody) {
        tbody.innerHTML = `<tr><td colspan="7" class="text-center py-8 text-rose">Error loading history: ${escapeHtml(err.message)}</td></tr>`;
      }
    } finally {
      AppState.history.isLoading = false;
    }
  }

  async function loadComparison() {
    const tbody = document.getElementById('comparison-table-body');
    const badgeEl = document.getElementById('comparison-lift-badge');
    const pairwiseEl = document.getElementById('comparison-pairwise-text');
    if (!tbody) return;

    try {
      const data = await ApiService.fetchComparison({
        symbol: AppState.history.symbolFilter,
      });

      if (!data || !data.models || data.models.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-muted">No verified comparison sessions available yet.</td></tr>';
        if (badgeEl) {
          badgeEl.textContent = 'Awaiting Verified Sessions';
          badgeEl.className = 'badge badge-info';
        }
        if (pairwiseEl) pairwiseEl.textContent = '';
        return;
      }

      tbody.innerHTML = data.models.map((m) => {
        const accStr = m.directional_accuracy !== null && m.directional_accuracy !== undefined
          ? `${(m.directional_accuracy * 100).toFixed(1)}%`
          : '--';
        const f1Up = m.f1_up !== null && m.f1_up !== undefined ? m.f1_up.toFixed(2) : '--';
        const f1Dn = m.f1_down !== null && m.f1_down !== undefined ? m.f1_down.toFixed(2) : '--';
        const brierStr = m.brier_score !== null && m.brier_score !== undefined ? m.brier_score.toFixed(4) : '--';

        const modelLabel = m.model_name === 'ensemble'
          ? '<strong>Ensemble (ML+LLM)</strong>'
          : escapeHtml(m.model_name.toUpperCase());

        return `
          <tr>
            <td>${modelLabel}</td>
            <td class="font-mono">${m.total_predictions}</td>
            <td class="font-mono">${m.verified_sessions}</td>
            <td class="font-mono text-bold">${accStr}</td>
            <td class="font-mono">${f1Up} / ${f1Dn}</td>
            <td class="font-mono">${brierStr}</td>
          </tr>
        `;
      }).join('');

      if (badgeEl) {
        if (data.ensemble_lift_over_ml !== null && data.ensemble_lift_over_ml !== undefined) {
          const liftPct = (data.ensemble_lift_over_ml * 100).toFixed(1);
          const sign = data.ensemble_lift_over_ml >= 0 ? '+' : '';
          badgeEl.textContent = `Ensemble Lift vs ML: ${sign}${liftPct}%`;
          badgeEl.className = data.ensemble_lift_over_ml >= 0 ? 'badge badge-success' : 'badge badge-warning';
        } else {
          badgeEl.textContent = `${data.models.length} Models Tracked`;
          badgeEl.className = 'badge badge-info';
        }
      }

      if (pairwiseEl && data.pairwise_comparisons && data.pairwise_comparisons.length > 0) {
        pairwiseEl.innerHTML = data.pairwise_comparisons.map((pw) => {
          const agrStr = pw.agreement_rate !== null && pw.agreement_rate !== undefined
            ? `${(pw.agreement_rate * 100).toFixed(1)}%`
            : 'N/A';
          const deltaStr = pw.accuracy_delta !== null && pw.accuracy_delta !== undefined
            ? `${pw.accuracy_delta >= 0 ? '+' : ''}${(pw.accuracy_delta * 100).toFixed(1)}%`
            : 'N/A';
          return `<strong>${escapeHtml(pw.model_a.toUpperCase())} vs ${escapeHtml(pw.model_b.toUpperCase())}:</strong> ` +
            `Matched: ${pw.matched_sessions} | Agreement: ${agrStr} | Wins: ${escapeHtml(pw.model_a.toUpperCase())}=${pw.model_a_superior_count}, ${escapeHtml(pw.model_b.toUpperCase())}=${pw.model_b_superior_count} | Delta: ${deltaStr}`;
        }).join('<br>');
      } else if (pairwiseEl) {
        pairwiseEl.textContent = '';
      }
    } catch (e) {
      if (tbody) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-center py-4 text-rose">Comparison data error: ${escapeHtml(e.message)}</td></tr>`;
      }
    }
  }

  function renderHistoryTable(items) {
    const tbody = document.getElementById('history-table-body');
    if (!tbody) return;

    if (items.length === 0) {
      const sym = AppState.history.symbolFilter ? ` for symbol '${escapeHtml(AppState.history.symbolFilter)}'` : '';
      tbody.innerHTML = `<tr><td colspan="8" class="text-center py-8 text-muted">No prediction audit records found${sym}. Persisted predictions appear here after execution with audit logging enabled.</td></tr>`;
      return;
    }

    tbody.innerHTML = items.map((it, idx) => {
      // Direction Pill
      let dirPill = '<span class="badge badge-warning">N/A</span>';
      if (it.predicted_direction === 'UP') {
        dirPill = '<span class="badge badge-success">UP ↗</span>';
      } else if (it.predicted_direction === 'DOWN') {
        dirPill = '<span class="badge badge-danger">DOWN ↘</span>';
      }

      // Probability
      const probText = it.probability_up !== null && it.probability_up !== undefined ? `${(it.probability_up * 100).toFixed(1)}%` : '--';

      // Verified Actual Outcome Column
      let outcomeHtml = '<span class="badge badge-timestamp">Pending Outcome</span>';
      if (it.actual) {
        const act = it.actual;
        const actDir = act.actual_direction === 'UP' ? 'text-emerald' : 'text-rose';
        const isMatch = it.predicted_direction === act.actual_direction;
        const matchBadge = isMatch ? '<span class="badge badge-success">✓ Correct</span>' : '<span class="badge badge-danger">✗ Miss</span>';

        outcomeHtml = `
          <div style="display: flex; flex-direction: column; gap: 2px;">
            <div style="display: flex; gap: 6px; align-items: center;">
              <span class="font-mono text-bold ${actDir}">${act.actual_direction}</span>
              ${matchBadge}
            </div>
            <div style="font-size: 0.75rem; color: var(--text-dim);" class="font-mono">
              Close: ${formatPriceINR(act.actual_close)} (${formatPercent(act.actual_return)})
            </div>
          </div>
        `;
      }

      // Structured why_prediction evidence
      const why = it.why_prediction || {};
      const horizonText = escapeHtml(why.horizon || '1 Session');
      const techText = escapeHtml(why.technical_evidence || 'Technical indicators evaluated.');
      const llmText = escapeHtml(why.qualitative_reasoning || 'No qualitative summary recorded.');
      const sourcesText = escapeHtml((why.cited_sources && why.cited_sources.length > 0) ? why.cited_sources.join(', ') : 'None');
      const provText = escapeHtml(why.provenance || it.model_name);

      return `
        <tr class="history-main-row">
          <td><code class="font-mono text-muted" title="${escapeHtml(it.prediction_id)}">${escapeHtml(it.prediction_id.substring(0, 8))}...</code></td>
          <td><strong>${escapeHtml(it.symbol)}</strong></td>
          <td><span class="badge badge-info">${escapeHtml(it.model_name)}</span></td>
          <td class="font-mono text-muted" style="font-size: 0.78rem;">${formatDateTimeIST(it.prediction_timestamp)}</td>
          <td>${dirPill}</td>
          <td class="font-mono">${probText}</td>
          <td>${outcomeHtml}</td>
          <td>
            <button type="button" class="btn-evidence-toggle" data-target="evidence-row-${idx}" aria-label="Toggle prediction evidence details">
              Evidence 🔍
            </button>
          </td>
        </tr>
        <tr id="evidence-row-${idx}" class="history-evidence-row" style="display: none;">
          <td colspan="8">
            <div class="history-evidence-box">
              <div class="history-evidence-grid">
                <div class="hist-evidence-col">
                  <span class="hist-evidence-label">Horizon & Provenance</span>
                  <div><strong>Horizon:</strong> ${horizonText}</div>
                  <div><strong>Provenance:</strong> ${provText}</div>
                </div>
                <div class="hist-evidence-col">
                  <span class="hist-evidence-label">Technical Evidence</span>
                  <div>${techText}</div>
                </div>
                <div class="hist-evidence-col">
                  <span class="hist-evidence-label">Qualitative Reasoning</span>
                  <div>${llmText}</div>
                </div>
                <div class="hist-evidence-col">
                  <span class="hist-evidence-label">Sources Cited</span>
                  <div>${sourcesText}</div>
                </div>
              </div>
            </div>
          </td>
        </tr>
      `;
    }).join('');

    tbody.querySelectorAll('.btn-evidence-toggle').forEach((btn) => {
      btn.addEventListener('click', () => {
        const targetId = btn.getAttribute('data-target');
        const row = document.getElementById(targetId);
        if (row) {
          const isHidden = row.style.display === 'none';
          row.style.display = isHidden ? 'table-row' : 'none';
          btn.textContent = isHidden ? 'Evidence ▲' : 'Evidence 🔍';
        }
      });
    });
  }

  // -------------------------------------------------------------------------
  // Macro & Regulatory Events Controller
  // -------------------------------------------------------------------------
  function initEventsModule() {
    const btnRefresh = document.getElementById('btn-refresh-events');
    if (btnRefresh) {
      btnRefresh.addEventListener('click', () => loadEvents());
    }

    const filterChips = document.querySelectorAll('#events-category-filters .filter-chip');
    filterChips.forEach((chip) => {
      chip.addEventListener('click', () => {
        filterChips.forEach((c) => c.classList.remove('active'));
        chip.classList.add('active');
        AppState.events.categoryFilter = chip.getAttribute('data-category') || '';
        loadEvents();
      });
    });

    const searchInput = document.getElementById('events-search-input');
    if (searchInput) {
      searchInput.addEventListener('input', () => {
        const query = searchInput.value.trim().toLowerCase();
        if (!query) {
          renderEventsGrid(AppState.events.items || []);
          return;
        }
        const filtered = (AppState.events.items || []).filter((ev) => {
          const t = (ev.title || '').toLowerCase();
          const s = (ev.source_org || '').toLowerCase();
          const p = (ev.provider || '').toLowerCase();
          const c = (ev.category || '').toLowerCase();
          return t.includes(query) || s.includes(query) || p.includes(query) || c.includes(query);
        });
        renderEventsGrid(filtered);
      });
    }
  }

  async function loadEvents() {
    const grid = document.getElementById('events-cards-grid');
    if (grid) {
      grid.innerHTML = '<div class="loading-placeholder">Ingesting and deduplicating latest regulatory circulars...</div>';
    }

    AppState.events.isLoading = true;

    try {
      const data = await ApiService.fetchEvents({
        category: AppState.events.categoryFilter,
      });

      AppState.events.items = data.events || [];
      renderEventsGrid(data.events || []);
    } catch (err) {
      if (grid) {
        grid.innerHTML = `<div class="loading-placeholder text-rose">Error loading events: ${escapeHtml(err.message)}</div>`;
      }
    } finally {
      AppState.events.isLoading = false;
    }
  }

  function renderEventsGrid(events) {
    const grid = document.getElementById('events-cards-grid');
    if (!grid) return;

    if (events.length === 0) {
      grid.innerHTML = '<div class="loading-placeholder text-muted">No macroeconomic announcements found for the selected category.</div>';
      return;
    }

    // Safely construct cards via DOM APIs avoiding innerHTML string interpolation of untrusted values
    grid.replaceChildren();

    events.forEach((ev) => {
      const card = document.createElement('article');
      card.className = 'event-card';

      const header = document.createElement('div');
      header.className = 'event-header';

      const catBadge = document.createElement('span');
      catBadge.className = `badge ${ev.category === 'monetary_policy' ? 'badge-purple' : 'badge-info'}`;
      catBadge.textContent = String(ev.category || '').replace('_', ' ').toUpperCase();

      const timeBadge = document.createElement('span');
      timeBadge.className = 'badge badge-timestamp';
      timeBadge.textContent = formatDateTimeIST(ev.published_at || ev.ingested_at);

      header.appendChild(catBadge);
      header.appendChild(timeBadge);
      card.appendChild(header);

      const titleEl = document.createElement('h4');
      titleEl.className = 'event-title';
      titleEl.textContent = ev.title || '';
      card.appendChild(titleEl);

      const metaRow = document.createElement('div');
      metaRow.className = 'event-meta-row';

      const srcSpan = document.createElement('span');
      srcSpan.textContent = '🏛️ Source: ';
      const srcStrong = document.createElement('strong');
      srcStrong.textContent = ev.source_org || '';
      srcSpan.appendChild(srcStrong);

      const bulletSpan = document.createElement('span');
      bulletSpan.textContent = ' • ';

      const provSpan = document.createElement('span');
      provSpan.textContent = `Provider: ${ev.provider || ''}`;

      metaRow.appendChild(srcSpan);
      metaRow.appendChild(bulletSpan);
      metaRow.appendChild(provSpan);
      card.appendChild(metaRow);

      if (ev.affected_sectors && ev.affected_sectors.length > 0) {
        const sectorsDiv = document.createElement('div');
        sectorsDiv.className = 'event-sectors';
        ev.affected_sectors.forEach((sec) => {
          const chip = document.createElement('span');
          chip.className = 'chip';
          chip.textContent = String(sec);
          sectorsDiv.appendChild(chip);
        });
        card.appendChild(sectorsDiv);
      }

      if (isSafeHttpUrl(ev.url)) {
        try {
          const parsed = new URL(ev.url);
          if (parsed.protocol === 'http:' || parsed.protocol === 'https:') {
            const link = document.createElement('a');
            link.href = parsed.href;
            link.target = '_blank';
            link.rel = 'noopener noreferrer';
            link.className = 'btn btn-outline btn-sm';
            link.style.marginTop = 'auto';
            link.style.alignSelf = 'flex-start';
            link.textContent = 'Official Circular ↗';
            card.appendChild(link);
          }
        } catch (_) {}
      }

      grid.appendChild(card);
    });
  }

  // -------------------------------------------------------------------------
  // System Health Controller
  // -------------------------------------------------------------------------
  function initHealthModule() {
    const btnRefresh = document.getElementById('btn-refresh-health');
    if (btnRefresh) {
      btnRefresh.addEventListener('click', () => loadHealth());
    }
  }

  async function loadHealth() {
    const pill = document.getElementById('health-pill');
    const pillLabel = document.getElementById('health-pill-label');
    const indicatorDot = document.getElementById('health-indicator-dot');
    const heroTitle = document.getElementById('health-hero-title');
    const heroDesc = document.getElementById('health-hero-desc');
    const heroIcon = document.getElementById('health-hero-icon');
    const lastEval = document.getElementById('health-last-evaluated');
    const depGrid = document.getElementById('dependencies-grid');

    AppState.health.isLoading = true;

    try {
      const data = await ApiService.fetchHealth();
      AppState.health.status = data.status;
      AppState.health.dependencies = data.dependencies || {};
      AppState.health.lastEvaluated = data.timestamp;

      // Update Pill
      if (indicatorDot && pillLabel) {
        indicatorDot.className = 'status-indicator ' + (data.status === 'healthy' ? 'status-healthy' : 'status-degraded');
        pillLabel.textContent = data.status === 'healthy' ? 'System Operational' : 'Degraded State';
      }

      // Update Hero Banner
      if (heroTitle && heroDesc && heroIcon) {
        if (data.status === 'healthy') {
          heroTitle.textContent = 'System Status: All Systems Operational';
          heroDesc.textContent = `Active in ${data.environment} mode. All database connections and model registries are responsive.`;
          heroIcon.textContent = '✅';
        } else {
          heroTitle.textContent = 'System Status: Attention Required (Degraded)';
          heroDesc.textContent = 'One or more subsystem dependencies are unreachable or impaired.';
          heroIcon.textContent = '⚠️';
        }
      }

      if (lastEval) {
        lastEval.textContent = `Last Evaluated: ${formatDateTimeIST(data.timestamp)}`;
      }

      // Render Dependencies Grid
      if (depGrid) {
        const deps = data.dependencies || {};
        depGrid.innerHTML = Object.keys(deps).map((name) => {
          const item = deps[name];
          const isOk = item.status === 'ok' || item.status === 'configured';
          const badgeClass = isOk ? 'badge-success' : 'badge-danger';

          return `
            <div class="dep-card">
              <div class="dep-header">
                <span class="dep-name">${escapeHtml(name)}</span>
                <span class="badge ${badgeClass}">${escapeHtml(item.status.toUpperCase())}</span>
              </div>
              <p class="dep-details">${escapeHtml(item.details || 'Operational')}</p>
            </div>
          `;
        }).join('');
      }

    } catch (err) {
      if (indicatorDot && pillLabel) {
        indicatorDot.className = 'status-indicator status-unreachable';
        pillLabel.textContent = 'Backend Offline';
      }
      if (heroTitle && heroDesc) {
        heroTitle.textContent = 'System Status: Offline / Unreachable';
        heroDesc.textContent = err.message || 'Could not connect to FastAPI server.';
      }
    } finally {
      AppState.health.isLoading = false;
    }
  }

  async function loadInstrumentCatalog() {
    try {
      const data = await ApiService.fetchInstruments();
      if (!data || !data.instruments) return;
      AppState.catalog = data.instruments;
      renderDashboardCatalog();
      const chipsGroup = document.getElementById('quick-ticker-chips');
      if (!chipsGroup) return;

      chipsGroup.innerHTML = '';
      data.instruments.forEach((inst) => {
        const btn = document.createElement('button');
        btn.type = 'button';
        const isSupp = inst.status === 'SUPPORTED';
        btn.className = `chip ${isSupp ? 'chip-supported' : 'chip-blocked'}`;
        btn.setAttribute('data-symbol', inst.symbol);
        btn.setAttribute('title', `${inst.name} (${inst.status}): ${inst.reason}`);

        const dot = document.createElement('span');
        dot.className = `chip-status-dot ${isSupp ? 'supported' : 'blocked'}`;
        btn.appendChild(dot);

        const symSpan = document.createElement('span');
        symSpan.className = 'chip-symbol';
        symSpan.textContent = inst.symbol === 'NIFTY_TELECOMMUNICATIONS' ? 'NIFTY_TELECOM' : inst.symbol;
        btn.appendChild(symSpan);

        const badge = document.createElement('span');
        badge.className = `chip-badge ${isSupp ? 'badge-supported' : 'badge-blocked'}`;
        badge.textContent = isSupp ? 'Supported' : (inst.instrument_type === 'INDEX' ? 'Index Blocked' : 'Blocked');
        btn.appendChild(badge);

        btn.addEventListener('click', () => {
          if (AppState.isPredicting) return;
          clearStalePredictionIfSymbolChanged(inst.symbol);
          const input = document.getElementById('symbol-input');
          if (input) {
            input.value = inst.symbol;
            input.focus();
            const err = document.getElementById('symbol-error');
            if (err) err.textContent = '';
          }
        });

        chipsGroup.appendChild(btn);
      });
    } catch (err) {
      console.warn('Could not load dynamic instrument catalog from backend:', err);
      const chipsGroup = document.getElementById('quick-ticker-chips');
      if (chipsGroup) {
        chipsGroup.innerHTML = '<span class="catalog-error-notice" role="status">Dynamic instrument catalog currently unavailable. Please verify backend connection.</span>';
      }
    }
  }

  // -------------------------------------------------------------------------
  // Initialization
  // -------------------------------------------------------------------------
  document.addEventListener('DOMContentLoaded', () => {
    startMarketClock();
    initNavigationTabs();
    initDashboard();
    initPredictionEngine();
    initHistoryModule();
    initEventsModule();
    initHealthModule();
    initChatModule();

    // Initial background health check, instrument catalog load, and dashboard snapshot
    loadHealth();
    loadInstrumentCatalog();
    loadDashboard();
  });

})();
