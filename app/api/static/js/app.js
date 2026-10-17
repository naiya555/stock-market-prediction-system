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

    async runPrediction(payload) {
      const res = await fetch(`${API_BASE}/predict`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      const data = await res.json().catch(() => null);

      if (!res.ok) {
        let msg = 'Failed to execute prediction.';
        if (data && data.error && data.error.message) {
          msg = data.error.message;
        } else if (data && data.detail) {
          msg = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
        }
        const err = new Error(msg);
        err.status = res.status;
        err.data = data;
        throw err;
      }

      return data;
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
        if (targetId === 'tab-panel-history') {
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
          symbolInput.value = sym;
          symbolInput.focus();
          if (symbolError) symbolError.textContent = '';
        }
      });
    });

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

        // Set Loading State
        setPredictionLoading(true);

        try {
          const result = await ApiService.runPrediction(payload);
          AppState.prediction = result;
          renderPredictionResult(result);
        } catch (err) {
          showPredictionError(err.message || 'An unexpected error occurred during prediction inference.');
        } finally {
          setPredictionLoading(false);
        }
      });
    }
  }

  function setPredictionLoading(isLoading) {
    const btn = document.getElementById('btn-run-prediction');
    const skeleton = document.getElementById('prediction-loading-skeleton');
    const resultsContainer = document.getElementById('prediction-results-container');
    const emptyState = document.getElementById('predict-empty-state');

    if (btn) {
      btn.disabled = isLoading;
      if (isLoading) {
        btn.classList.add('loading');
        document.getElementById('btn-predict-text').textContent = 'Analyzing Market Data...';
      } else {
        btn.classList.remove('loading');
        document.getElementById('btn-predict-text').textContent = 'Generate Prediction';
      }
    }

    if (isLoading) {
      if (emptyState) emptyState.style.display = 'none';
      if (resultsContainer) resultsContainer.style.display = 'none';
      if (skeleton) skeleton.style.display = 'flex';
    } else {
      if (skeleton) skeleton.style.display = 'none';
    }
  }

  function showPredictionError(msg) {
    const alertBanner = document.getElementById('prediction-alert');
    const alertMsg = document.getElementById('alert-message');
    const resultsContainer = document.getElementById('prediction-results-container');
    const emptyState = document.getElementById('predict-empty-state');

    if (alertBanner && alertMsg) {
      alertMsg.textContent = msg;
      alertBanner.style.display = 'flex';
    }
    if (resultsContainer) resultsContainer.style.display = 'none';
    if (emptyState) emptyState.style.display = 'block';
  }

  function renderPredictionResult(res) {
    const container = document.getElementById('prediction-results-container');
    const emptyState = document.getElementById('predict-empty-state');
    if (!container) return;

    if (emptyState) emptyState.style.display = 'none';
    container.style.display = 'block';

    const heroCard = document.getElementById('result-hero-card');
    const symEl = document.getElementById('res-symbol');
    const modelBadge = document.getElementById('res-model-badge');
    const tsEl = document.getElementById('res-timestamp');
    const dirBadge = document.getElementById('res-direction-badge');
    const dirIcon = document.getElementById('res-direction-icon');
    const dirText = document.getElementById('res-direction-text');

    // Basic identifiers
    if (symEl) symEl.textContent = res.symbol;
    if (modelBadge) {
      modelBadge.textContent = `${res.model_name.toUpperCase()} (${res.model_version})`;
      modelBadge.className = 'badge ' + (res.model_name === 'ensemble' ? 'badge-purple' : 'badge-info');
    }
    if (tsEl) tsEl.textContent = formatDateTimeIST(res.prediction_timestamp);

    // Direction Decision & Styling
    const dir = res.predicted_direction;
    const isSuccess = res.status === 'SUCCESS';

    if (heroCard) {
      heroCard.classList.remove('direction-up', 'direction-down');
      if (dir === 'UP') heroCard.classList.add('direction-up');
      if (dir === 'DOWN') heroCard.classList.add('direction-down');
    }

    if (dirBadge && dirIcon && dirText) {
      dirBadge.className = 'direction-badge';
      if (!isSuccess) {
        dirBadge.classList.add('neutral');
        dirIcon.textContent = '⚠️';
        dirText.textContent = res.status || 'FAILED';
      } else if (dir === 'UP') {
        dirBadge.classList.add('up');
        dirIcon.textContent = '↗';
        dirText.textContent = 'PREDICTED UP';
      } else if (dir === 'DOWN') {
        dirBadge.classList.add('down');
        dirIcon.textContent = '↘';
        dirText.textContent = 'PREDICTED DOWN';
      } else {
        dirBadge.classList.add('neutral');
        dirIcon.textContent = '⏸';
        dirText.textContent = dir || 'NEUTRAL';
      }
    }

    // Probabilities Bar - Never substitute 50% for missing probability
    const hasProbUp = typeof res.probability_up === 'number' && res.probability_up !== null && !isNaN(res.probability_up);
    const hasProbDown = typeof res.probability_down === 'number' && res.probability_down !== null && !isNaN(res.probability_down);
    const fillEl = document.getElementById('res-probability-fill');
    const probUpEl = document.getElementById('res-prob-up');
    const probDownEl = document.getElementById('res-prob-down');

    if (hasProbUp) {
      const probUp = res.probability_up;
      const probDown = hasProbDown ? res.probability_down : (1.0 - probUp);
      if (fillEl) fillEl.style.width = `${Math.max(0, Math.min(100, probUp * 100)).toFixed(1)}%`;
      if (probUpEl) probUpEl.textContent = `P(UP): ${(probUp * 100).toFixed(1)}%`;
      if (probDownEl) probDownEl.textContent = `P(DOWN): ${(probDown * 100).toFixed(1)}%`;
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

    } catch (err) {
      if (tbody) {
        tbody.innerHTML = `<tr><td colspan="7" class="text-center py-8 text-rose">Error loading history: ${escapeHtml(err.message)}</td></tr>`;
      }
    } finally {
      AppState.history.isLoading = false;
    }
  }

  function renderHistoryTable(items) {
    const tbody = document.getElementById('history-table-body');
    if (!tbody) return;

    if (items.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" class="text-center py-8 text-muted">No prediction audit records found matching criteria.</td></tr>';
      return;
    }

    tbody.innerHTML = items.map((it) => {
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

      return `
        <tr>
          <td><code class="font-mono text-muted" title="${escapeHtml(it.prediction_id)}">${escapeHtml(it.prediction_id.substring(0, 8))}...</code></td>
          <td><strong>${escapeHtml(it.symbol)}</strong></td>
          <td><span class="badge badge-info">${escapeHtml(it.model_name)}</span></td>
          <td class="font-mono text-muted" style="font-size: 0.78rem;">${formatDateTimeIST(it.prediction_timestamp)}</td>
          <td>${dirPill}</td>
          <td class="font-mono">${probText}</td>
          <td>${outcomeHtml}</td>
        </tr>
      `;
    }).join('');
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

    grid.innerHTML = events.map((ev) => {
      const catClass = ev.category === 'monetary_policy' ? 'badge-purple' : 'badge-info';
      const sectorTags = (ev.affected_sectors || []).map((s) => `<span class="chip">${escapeHtml(s)}</span>`).join('');
      const safeUrl = isSafeHttpUrl(ev.url) ? escapeHtml(ev.url) : null;

      return `
        <article class="event-card">
          <div class="event-header">
            <span class="badge ${catClass}">${escapeHtml(ev.category.replace('_', ' ').toUpperCase())}</span>
            <span class="badge badge-timestamp">${formatDateTimeIST(ev.published_at || ev.ingested_at)}</span>
          </div>
          <h4 class="event-title">${escapeHtml(ev.title)}</h4>
          <div class="event-meta-row">
            <span>🏛️ Source: <strong>${escapeHtml(ev.source_org)}</strong></span>
            <span>&bull;</span>
            <span>Provider: ${escapeHtml(ev.provider)}</span>
          </div>
          ${sectorTags ? `<div class="event-sectors">${sectorTags}</div>` : ''}
          ${safeUrl ? `<a href="${safeUrl}" target="_blank" rel="noopener noreferrer" class="btn btn-outline btn-sm" style="margin-top: auto; align-self: flex-start;">Official Circular ↗</a>` : ''}
        </article>
      `;
    }).join('');
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

  // -------------------------------------------------------------------------
  // Initialization
  // -------------------------------------------------------------------------
  document.addEventListener('DOMContentLoaded', () => {
    startMarketClock();
    initNavigationTabs();
    initPredictionEngine();
    initHistoryModule();
    initEventsModule();
    initHealthModule();

    // Initial background health check
    loadHealth();
  });

})();
