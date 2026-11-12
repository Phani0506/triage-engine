/**
 * Mobile-First Antigravity Triage Engine Doctor Review Client
 */

(function () {
  'use strict';

  // --- STATE ---
  let authToken = '';
  let batchId = 'batch1';
  let doctorName = '';
  let batchCases = [];
  let completedCaseIds = new Set();
  let currentCaseIndex = 0;
  let currentCaseData = null;
  let selectedLevel = null;
  let selectedColour = null;
  let currentReviewId = null;

  // --- DOM ELEMENTS ---
  const elDoctorName = document.getElementById('doctor-display-name');
  const btnChangeName = document.getElementById('btn-change-name');
  const elBatchDisplay = document.getElementById('batch-display');
  const elProgressText = document.getElementById('progress-text');
  const elProgressPct = document.getElementById('progress-pct');
  const elProgressBarFill = document.getElementById('progress-bar-fill');

  const elLoadingState = document.getElementById('loading-state');
  const elCompletionState = document.getElementById('completion-state');
  const elCaseContent = document.getElementById('case-content');

  const serverStatusBanner = document.getElementById('server-status-banner');
  const doctorModal = document.getElementById('doctor-modal');
  const doctorSelectDropdown = document.getElementById('doctor-select-dropdown');
  const btnConfirmDoctor = document.getElementById('btn-confirm-doctor');

  const elCaseIdBadge = document.getElementById('case-id-badge');
  const elCaseTopicBadge = document.getElementById('case-topic-badge');
  const elSummaryList = document.getElementById('summary-lines-list');
  const elRawInputsContent = document.getElementById('raw-inputs-content');

  const elAssessmentStep = document.getElementById('assessment-step');
  const urgencyButtons = document.querySelectorAll('.btn-urgency');
  const elDoctorNotes = document.getElementById('doctor-notes');
  const btnSubmitAssessment = document.getElementById('btn-submit-assessment');

  const elRevealStep = document.getElementById('reveal-step');
  const elAgreementBanner = document.getElementById('agreement-banner');
  const elEngineBadge = document.getElementById('engine-urgency-badge');
  const elEngineReasons = document.getElementById('engine-reasons-list');
  const elEngineAdvice = document.getElementById('engine-advice-text');
  const elEngineTestsBox = document.getElementById('engine-tests-box');
  const elEngineTestsList = document.getElementById('engine-tests-list');

  const agreementSection = document.getElementById('agreement-section');
  const agreementDoctorNotes = document.getElementById('agreement-doctor-notes');
  const elDisagreementForm = document.getElementById('disagreement-form');
  const elDisagreementPromptLabel = document.getElementById('disagreement-prompt-label');
  const chipLevelTooLow = document.getElementById('chip-level-too-low');
  const elFeedbackText = document.getElementById('feedback-text');
  const btnNextCase = document.getElementById('btn-next-case');
  const btnRestartBatch = document.getElementById('btn-restart-batch');

  // --- INITIALIZATION ---
  function init() {
    parseUrlFragment();
    setupEventListeners();
    initDoctorIdentity();
  }

  function parseUrlFragment() {
    // 1. Check URL hash: e.g. #t=TOKEN&batch=batch1
    if (window.location.hash) {
      const hash = window.location.hash.substring(1);
      const params = new URLSearchParams(hash);
      if (params.has('t')) {
        let t = params.get('t') || '';
        t = t.split(/[^a-zA-Z0-9_-]/)[0] || '';
        authToken = t;
        sessionStorage.setItem('triage_token', authToken);
      }
      if (params.has('batch')) {
        let b = params.get('batch') || 'batch1';
        b = b.split(/[^a-zA-Z0-9_-]/)[0] || 'batch1';
        batchId = b;
        sessionStorage.setItem('triage_batch', batchId);
      }
      history.replaceState(null, '', window.location.pathname);
    }

    const stored = sessionStorage.getItem('triage_token');
    if (!authToken || authToken.length < 40) {
      authToken = (stored && stored.length >= 40) ? stored : 'sM5WfU1GLNbpJovXBBCxSC0K-MjQWfZ5YcZOWI5SCYg';
      sessionStorage.setItem('triage_token', authToken);
    }

    batchId = (sessionStorage.getItem('triage_batch') || 'batch1').split(/[^a-zA-Z0-9_-]/)[0] || 'batch1';
    sessionStorage.setItem('triage_batch', batchId);
    elBatchDisplay.textContent = 'All Topics (38 Cases)';
  }

  function initDoctorIdentity() {
    doctorName = (localStorage.getItem('triage_doctor_name') || '').trim();
    if (doctorName) {
      elDoctorName.textContent = doctorName;
      if (doctorModal) doctorModal.classList.add('hidden');
      loadBatch();
    } else {
      if (doctorModal) {
        doctorModal.classList.remove('hidden');
        if (doctorSelectDropdown) doctorSelectDropdown.value = '';
        if (btnConfirmDoctor) btnConfirmDoctor.disabled = true;
      }
    }
  }

  function setupEventListeners() {
    if (doctorSelectDropdown && btnConfirmDoctor) {
      doctorSelectDropdown.addEventListener('change', () => {
        btnConfirmDoctor.disabled = !doctorSelectDropdown.value;
      });

      btnConfirmDoctor.addEventListener('click', () => {
        const selected = doctorSelectDropdown.value;
        if (selected) {
          doctorName = selected;
          localStorage.setItem('triage_doctor_name', doctorName);
          elDoctorName.textContent = doctorName;
          doctorModal.classList.add('hidden');
          loadBatch();
        }
      });
    }

    btnChangeName.addEventListener('click', () => {
      if (doctorModal) {
        doctorModal.classList.remove('hidden');
        if (doctorSelectDropdown && doctorName) {
          doctorSelectDropdown.value = doctorName;
          if (btnConfirmDoctor) btnConfirmDoctor.disabled = false;
        }
      }
    });

    urgencyButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        urgencyButtons.forEach(b => b.classList.remove('selected'));
        btn.classList.add('selected');
        selectedLevel = btn.getAttribute('data-level');
        selectedColour = btn.getAttribute('data-colour');
        btnSubmitAssessment.disabled = false;
      });
    });

    btnSubmitAssessment.addEventListener('click', submitAssessment);
    btnNextCase.addEventListener('click', proceedToNextCase);
    btnRestartBatch.addEventListener('click', () => {
      completedCaseIds.clear();
      currentCaseIndex = 0;
      elCompletionState.classList.add('hidden');
      loadCase(batchCases[0].case_id);
    });
  }

  // Active requests counter for cold-start server banner
  let activeRequests = 0;
  let coldStartTimer = null;

  async function apiFetch(url, options = {}) {
    options.headers = options.headers || {};
    options.headers['Authorization'] = `Bearer ${authToken}`;
    options.headers['Content-Type'] = 'application/json';

    activeRequests++;
    if (!coldStartTimer) {
      coldStartTimer = setTimeout(() => {
        if (activeRequests > 0 && serverStatusBanner) {
          serverStatusBanner.classList.remove('hidden');
        }
      }, 600);
    }

    try {
      const resp = await fetch(url, options);
      if (resp.status === 401) {
        alert('Authentication error. Refreshing session...');
        sessionStorage.removeItem('triage_token');
        window.location.reload();
        throw new Error('Unauthorized');
      }
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ error: 'Request failed' }));
        throw new Error(err.error || 'Server error');
      }
      return await resp.json();
    } finally {
      activeRequests--;
      if (activeRequests <= 0) {
        activeRequests = 0;
        if (coldStartTimer) {
          clearTimeout(coldStartTimer);
          coldStartTimer = null;
        }
        if (serverStatusBanner) {
          serverStatusBanner.classList.add('hidden');
        }
      }
    }
  }

  // --- BATCH LOADING ---
  async function loadBatch() {
    try {
      elLoadingState.classList.remove('hidden');
      elCaseContent.classList.add('hidden');
      elCompletionState.classList.add('hidden');

      const data = await apiFetch(`/api/batches/${batchId}/cases?doctor=${encodeURIComponent(doctorName)}`);
      batchCases = data.cases || [];
      completedCaseIds = new Set(data.completed_case_ids || []);

      if (batchCases.length === 0) {
        alert(`No cases found for batch: ${batchId}`);
        return;
      }

      // Resume at first uncompleted case
      let resumeIndex = 0;
      for (let i = 0; i < batchCases.length; i++) {
        if (!completedCaseIds.has(batchCases[i].case_id)) {
          resumeIndex = i;
          break;
        }
      }

      if (completedCaseIds.size >= batchCases.length) {
        showCompletionScreen();
        return;
      }

      currentCaseIndex = resumeIndex;
      await loadCase(batchCases[currentCaseIndex].case_id);
    } catch (e) {
      alert(`Error loading batch: ${e.message}`);
    }
  }

  // --- CASE LOADING ---
  async function loadCase(caseId) {
    try {
      elLoadingState.classList.remove('hidden');
      elCaseContent.classList.add('hidden');
      elRevealStep.classList.add('hidden');
      elAssessmentStep.classList.remove('hidden');

      // Reset selection state
      selectedLevel = null;
      selectedColour = null;
      currentReviewId = null;
      urgencyButtons.forEach(b => b.classList.remove('selected'));
      btnSubmitAssessment.disabled = true;
      elDoctorNotes.value = '';
      elFeedbackText.value = '';

      updateProgress();

      const c = await apiFetch(`/api/cases/${caseId}`);
      currentCaseData = c;

      elCaseIdBadge.textContent = c.case_id;
      elCaseTopicBadge.textContent = (c.topic || '').replace('_', ' ');

      // Summary lines
      elSummaryList.innerHTML = '';
      (c.patient_summary_lines || []).forEach(line => {
        const li = document.createElement('li');
        li.textContent = line;
        elSummaryList.appendChild(li);
      });

      // Raw inputs
      elRawInputsContent.innerHTML = '';
      const entries = Object.entries(c.patient_inputs || {}).sort();
      for (const [k, v] of entries) {
        const item = document.createElement('div');
        item.innerHTML = `<strong>${k}:</strong> ${v}`;
        elRawInputsContent.appendChild(item);
      }

      elLoadingState.classList.add('hidden');
      elCaseContent.classList.remove('hidden');
    } catch (e) {
      alert(`Error loading case: ${e.message}`);
    }
  }

  function updateProgress() {
    const total = batchCases.length;
    const currentNum = currentCaseIndex + 1;
    const pct = Math.round((completedCaseIds.size / total) * 100);

    elProgressText.textContent = `Case ${currentNum} of ${total}`;
    elProgressPct.textContent = `${pct}%`;
    elProgressBarFill.style.width = `${pct}%`;
  }

  function showCompletionScreen() {
    elLoadingState.classList.add('hidden');
    elCaseContent.classList.add('hidden');
    elCompletionState.classList.remove('hidden');
    elProgressText.textContent = `All ${batchCases.length} Cases Completed`;
    elProgressPct.textContent = `100%`;
    elProgressBarFill.style.width = `100%`;
  }

  // --- STEP 1: SUBMIT ASSESSMENT ---
  async function submitAssessment() {
    if (!selectedLevel || !selectedColour) return;

    btnSubmitAssessment.disabled = true;
    btnSubmitAssessment.innerHTML = '<span class="spinner-inline"></span> Comparing with Engine...';

    try {
      const payload = {
        case_id: currentCaseData.case_id,
        doctor_name: doctorName,
        doctor_level: selectedLevel,
        doctor_colour: selectedColour,
        doctor_initial_notes: elDoctorNotes.value.trim(),
      };

      const result = await apiFetch('/api/reviews/submit-assessment', {
        method: 'POST',
        body: JSON.stringify(payload),
      });

      currentReviewId = result.review_id;
      completedCaseIds.add(currentCaseData.case_id);
      updateProgress();

      revealEngineResult(result);
    } catch (e) {
      alert(`Error submitting assessment: ${e.message}`);
      btnSubmitAssessment.disabled = false;
      btnSubmitAssessment.textContent = 'Submit Evaluation & Compare with Engine';
    }
  }

  // --- STEP 2: REVEAL ENGINE OUTPUT ---
  function revealEngineResult(result) {
    elAssessmentStep.classList.add('hidden');
    elRevealStep.classList.remove('hidden');

    const engLevel = result.engine_level;
    const engColour = result.engine_colour;
    const isAgreed = result.agreement_status === 'same';

    // Badge
    elEngineBadge.textContent = `${formatColour(engColour)} (${formatLevel(engLevel)})`;
    elEngineBadge.className = `urgency-badge badge-${engColour}`;

    // Reasons (Clean doctor-friendly presentation without raw rule codes)
    elEngineReasons.innerHTML = '';
    (result.reasons || []).forEach(r => {
      const li = document.createElement('li');
      li.textContent = r.text || r.rule || 'Clinical guideline criterion satisfied.';
      elEngineReasons.appendChild(li);
    });

    // Advice
    elEngineAdvice.textContent = result.advice || 'None provided.';

    // Tests
    elEngineTestsList.innerHTML = '';
    const tests = result.doctor_may_suggest || [];
    if (tests.length > 0) {
      elEngineTestsBox.classList.remove('hidden');
      tests.forEach(t => {
        const li = document.createElement('li');
        li.textContent = t;
        elEngineTestsList.appendChild(li);
      });
    } else {
      elEngineTestsBox.classList.add('hidden');
    }

    // Agreement Banner & Additional Suggestion Box
    if (isAgreed) {
      elAgreementBanner.className = 'agreement-banner agreed';
      elAgreementBanner.innerHTML = `✅ <strong>Agreement!</strong> Clinical engine matched your assessment (<em>${formatLevel(selectedLevel)}</em>).`;
      if (agreementSection) {
        agreementSection.classList.remove('hidden');
        if (agreementDoctorNotes) agreementDoctorNotes.value = '';
      }
      elDisagreementForm.classList.add('hidden');
      btnNextCase.textContent = 'Save & Next Case →';
    } else {
      elAgreementBanner.className = 'agreement-banner disagreed';
      const dirText = result.agreement_status === 'engine_lower' ? 'Lower than' : 'Higher than';
      elAgreementBanner.innerHTML = `⚠️ <strong>Variance:</strong> Engine assigned <em>${formatLevel(engLevel)}</em> (${dirText} your <em>${formatLevel(selectedLevel)}</em>).`;
      if (agreementSection) agreementSection.classList.add('hidden');
      elDisagreementForm.classList.remove('hidden');

      // Pre-check "Recommendation too conservative" if engine under-triaged
      if (chipLevelTooLow) {
        chipLevelTooLow.checked = (result.agreement_status === 'engine_lower');
      }

      elDisagreementPromptLabel.innerHTML = `Why did you choose <strong>${formatColour(selectedColour)} (${formatLevel(selectedLevel)})</strong> instead of <strong>${formatColour(engColour)} (${formatLevel(engLevel)})</strong>?`;
      btnNextCase.textContent = 'Submit Feedback & Next Case →';
    }
  }

  // --- STEP 3: PROCEED / FEEDBACK ---
  async function proceedToNextCase() {
    btnNextCase.disabled = true;
    btnNextCase.innerHTML = '<span class="spinner-inline"></span> Saving...';

    // 1. If agreement section has doctor suggestions, submit them
    if (agreementSection && !agreementSection.classList.contains('hidden') && currentReviewId) {
      const extraNotes = agreementDoctorNotes ? agreementDoctorNotes.value.trim() : '';
      if (extraNotes) {
        try {
          await apiFetch('/api/reviews/submit-feedback', {
            method: 'POST',
            body: JSON.stringify({
              review_id: currentReviewId,
              doctor_name: doctorName,
              verdict: 'both_fine',
              problem_chips: [],
              feedback_text: extraNotes,
            }),
          });
        } catch (e) {
          console.error('Agreement feedback submission error:', e);
        }
      }
    }

    // 2. If disagreement form is visible, submit feedback
    if (!elDisagreementForm.classList.contains('hidden') && currentReviewId) {
      try {
        const checkedChips = [];
        document.querySelectorAll('#problem-chips-container input:checked').forEach(cb => {
          checkedChips.push(cb.value);
        });

        const selectedVerdict = document.querySelector('input[name="verdict"]:checked')?.value || 'doctor_is_right';

        await apiFetch('/api/reviews/submit-feedback', {
          method: 'POST',
          body: JSON.stringify({
            review_id: currentReviewId,
            doctor_name: doctorName,
            verdict: selectedVerdict,
            problem_chips: checkedChips,
            feedback_text: elFeedbackText.value.trim(),
          }),
        });
      } catch (e) {
        console.error('Feedback submission error:', e);
      }
    }

    // Advance to next case
    currentCaseIndex++;
    if (currentCaseIndex >= batchCases.length) {
      showCompletionScreen();
    } else {
      await loadCase(batchCases[currentCaseIndex].case_id);
    }
    btnNextCase.disabled = false;
    btnNextCase.textContent = 'Save & Next Case →';
  }

  function formatLevel(lvl) {
    if (!lvl) return '';
    return lvl.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase());
  }

  function formatColour(col) {
    if (!col) return '';
    return col.charAt(0).toUpperCase() + col.slice(1);
  }

  // Run on load
  document.addEventListener('DOMContentLoaded', init);
})();

