/**
 * ResumeAI — app.js
 * Handles upload, analysis, conversion, and results rendering.
 * No emojis — all visual indicators are CSS/SVG-based.
 */

// ── State ─────────────────────────────────────────────────────────────────────
let activeTab   = 'file';
let activeMode  = 'analyze';
let selectedFile  = null;
let convertedBlob = null;
let convertedName = 'Converted_Resume.docx';

// ── DOM refs ──────────────────────────────────────────────────────────────────
const tabFile        = document.getElementById('tab-file');
const tabText        = document.getElementById('tab-text');
const filePanel      = document.getElementById('file-panel');
const textPanel      = document.getElementById('text-panel');
const dropZone       = document.getElementById('drop-zone');
const fileInput      = document.getElementById('file-input');
const fileBadge      = document.getElementById('file-badge');
const fileNameSpan   = document.getElementById('file-name');
const resumeTextArea = document.getElementById('resume-text');
const jdTextArea     = document.getElementById('job-desc');
const analyzeBtn     = document.getElementById('analyze-btn');
const btnText        = document.getElementById('btn-text');
const btnIconAnalyze = document.getElementById('btn-icon-analyze');
const btnIconConvert = document.getElementById('btn-icon-convert');
const loadingOverlay = document.getElementById('loading-overlay');
const loadingTitle   = document.getElementById('loading-title');
const loadingStep    = document.getElementById('loading-step');
const errorBanner    = document.getElementById('error-banner');
const errorMsg       = document.getElementById('error-msg');
const results        = document.getElementById('results');
const convertResults = document.getElementById('convert-results');
const convertPreview = document.getElementById('convert-preview');
const downloadBtn    = document.getElementById('download-btn');
const uploadCard     = document.getElementById('upload-card');

// Analyze results
const resCandName   = document.getElementById('res-cand-name');
const resCandAvatar = document.getElementById('res-cand-avatar');
const resCandTitle  = document.getElementById('res-cand-title');
const resSummary    = document.getElementById('res-summary');
const resExpNum     = document.getElementById('res-exp-num');
const resExpBadge   = document.getElementById('experience-badge');
const resSkills     = document.getElementById('res-skills');
const resHighlights = document.getElementById('res-highlights');
const resATSNum     = document.getElementById('res-ats-num');
const resATSGrade   = document.getElementById('res-ats-grade');
const resATSSummary = document.getElementById('res-ats-summary');
const resSubscores  = document.getElementById('res-subscores');
const resTips       = document.getElementById('res-tips');
const gaugeCircle   = document.getElementById('gauge-circle');

// ── Mode switching ────────────────────────────────────────────────────────────
function switchMode(mode) {
  activeMode = mode;
  const isConvert = mode === 'convert';

  document.getElementById('mode-analyze').classList.toggle('active', !isConvert);
  document.getElementById('mode-convert').classList.toggle('active', isConvert);

  btnText.textContent = isConvert ? 'Convert Resume' : 'Analyze Resume';
  btnIconAnalyze.style.display = isConvert ? 'none' : '';
  btnIconConvert.style.display = isConvert ? '' : 'none';

  results.classList.remove('show');
  convertResults.classList.remove('show');
  uploadCard.style.display = '';
  hideError();
}

// ── Tab switching ─────────────────────────────────────────────────────────────
tabFile.addEventListener('click', () => switchTab('file'));
tabText.addEventListener('click', () => switchTab('text'));

function switchTab(tab) {
  activeTab = tab;
  tabFile.classList.toggle('active', tab === 'file');
  tabText.classList.toggle('active', tab === 'text');
  filePanel.classList.toggle('hidden', tab !== 'file');
  textPanel.classList.toggle('active', tab === 'text');
}

// ── File handling ─────────────────────────────────────────────────────────────
fileInput.addEventListener('change', (e) => handleFile(e.target.files[0]));

dropZone.addEventListener('dragover', (e) => {
  e.preventDefault();
  dropZone.classList.add('drag-over');
});
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
dropZone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropZone.classList.remove('drag-over');
  handleFile(e.dataTransfer.files[0]);
});

function handleFile(file) {
  if (!file) return;
  const ext = file.name.split('.').pop().toLowerCase();
  if (!['pdf', 'docx', 'doc', 'txt'].includes(ext)) {
    showError('Unsupported file type. Please upload a PDF, DOCX, or TXT file.');
    return;
  }
  selectedFile = file;
  fileNameSpan.textContent = file.name;
  fileBadge.classList.add('show');
  hideError();
}

// ── Main action ───────────────────────────────────────────────────────────────
analyzeBtn.addEventListener('click', () => {
  if (activeMode === 'analyze') runAnalysis();
  else runConversion();
});

// ── Analyze ───────────────────────────────────────────────────────────────────
async function runAnalysis() {
  if (!validateInput()) return;

  const formData = buildFormData();
  const steps = [
    'Extracting text from your resume…',
    'Groq AI is analyzing your skills…',
    'Calculating ATS compatibility score…',
    'Generating improvement recommendations…',
    'Finalizing results…',
  ];

  setLoading(true, 'Analyzing your resume with Groq AI');
  results.classList.remove('show');
  const stepInterval = cycleSteps(steps);

  try {
    const res = await fetch('/api/analyze', { method: 'POST', body: formData });
    clearInterval(stepInterval);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Unknown error.' }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    const data = await res.json();
    setLoading(false);
    renderResults(data);
  } catch (err) {
    clearInterval(stepInterval);
    setLoading(false);
    showError(err.message || 'Something went wrong. Please try again.');
  }
}

// ── Convert ───────────────────────────────────────────────────────────────────
async function runConversion() {
  if (!validateInput()) return;

  const formData = buildFormData();
  const steps = [
    'Extracting resume content…',
    'Groq AI is restructuring sections…',
    'Mapping to template format…',
    'Generating DOCX document…',
    'Finalizing converted resume…',
  ];

  setLoading(true, 'Converting your resume with Groq AI');
  convertResults.classList.remove('show');
  const stepInterval = cycleSteps(steps);

  try {
    const res = await fetch('/api/convert', { method: 'POST', body: formData });
    clearInterval(stepInterval);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Conversion failed.' }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    const blob = await res.blob();
    const disposition = res.headers.get('Content-Disposition') || '';
    const nameMatch = disposition.match(/filename="?([^"]+)"?/);
    convertedName = nameMatch ? nameMatch[1] : 'Converted_Resume.docx';
    convertedBlob = blob;
    setLoading(false);
    renderConvertResult(blob, convertedName);
  } catch (err) {
    clearInterval(stepInterval);
    setLoading(false);
    showError(err.message || 'Conversion failed. Please try again.');
  }
}

// ── Convert result render ─────────────────────────────────────────────────────
function renderConvertResult(blob, filename) {
  const displayName = filename.replace(/_/g, ' ').replace('.docx', '');
  const sizeKB = (blob.size / 1024).toFixed(1);

  convertPreview.innerHTML = `
    <div class="convert-preview-section">
      <div class="convert-preview-heading">Ready to Download</div>
      <div class="convert-preview-name">${escHtml(displayName)}</div>
      <div class="convert-preview-contact">Format: Microsoft Word (.docx) &nbsp;&middot;&nbsp; ${sizeKB} KB</div>
    </div>
    <div class="convert-preview-section">
      <div class="convert-preview-heading">Sections Included</div>
      ${['Professional Summary', 'Technical Skills', 'Professional Experience',
         'Other Relevant Experience', 'Education History', 'Certifications']
        .map(s => `<div class="convert-preview-bullet">${escHtml(s)}</div>`).join('')}
    </div>
  `;

  convertResults.classList.add('show');
  convertResults.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ── Download handler ──────────────────────────────────────────────────────────
downloadBtn.addEventListener('click', () => {
  if (!convertedBlob) return;
  const url = URL.createObjectURL(convertedBlob);
  const a   = Object.assign(document.createElement('a'), { href: url, download: convertedName });
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 5000);
});

// ── Analyze results render ────────────────────────────────────────────────────
function renderResults(data) {
  const name = data.candidate_name || 'Unknown Candidate';
  resCandName.textContent  = name;
  resCandAvatar.textContent = getInitials(name);
  resCandTitle.textContent  = data.candidate_title || 'Professional';
  resSummary.textContent    = data.summary || '';

  if (data.total_experience_years != null) {
    resExpNum.textContent = data.total_experience_years;
    resExpBadge.style.display = '';
  } else {
    resExpBadge.style.display = 'none';
  }

  renderSkills(data.skills);
  renderHighlights(data.highlights || []);
  renderATS(data.ats_score);
  renderTips(data.improvement_tips || []);

  results.classList.add('show');
  results.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ── Skills ────────────────────────────────────────────────────────────────────
const SKILL_GROUPS = [
  { key: 'technical',        label: 'Technical Skills',  cls: 'tag-technical', color: '#93c5fd' },
  { key: 'tools',            label: 'Tools & Software',  cls: 'tag-tools',     color: '#c4b5fd' },
  { key: 'soft_skills',      label: 'Soft Skills',       cls: 'tag-soft',      color: '#6ee7b7' },
  { key: 'domain_expertise', label: 'Domain Expertise',  cls: 'tag-domain',    color: '#7dd3fc' },
];

function renderSkills(skills) {
  resSkills.innerHTML = '';
  for (const group of SKILL_GROUPS) {
    const items = skills[group.key] || [];
    if (!items.length) continue;
    const groupDiv = document.createElement('div');
    groupDiv.className = 'skill-group';
    groupDiv.innerHTML = `<div class="skill-group-label" style="color:${group.color}">${group.label}</div>`;
    const tagsDiv = document.createElement('div');
    tagsDiv.className = 'skill-tags';
    items.forEach(skill => {
      const tag = document.createElement('span');
      tag.className = `skill-tag ${group.cls}`;
      tag.textContent = skill;
      tagsDiv.appendChild(tag);
    });
    groupDiv.appendChild(tagsDiv);
    resSkills.appendChild(groupDiv);
  }
}

// ── Highlights ────────────────────────────────────────────────────────────────
const CAT_STYLES = {
  'Work Experience': { bg: 'rgba(26,86,240,0.12)',   color: '#93c5fd', letter: 'W' },
  'Education':       { bg: 'rgba(139,92,246,0.12)',  color: '#c4b5fd', letter: 'E' },
  'Project':         { bg: 'rgba(14,165,233,0.12)',  color: '#7dd3fc', letter: 'P' },
  'Certification':   { bg: 'rgba(245,158,11,0.12)',  color: '#fcd34d', letter: 'C' },
  'Achievement':     { bg: 'rgba(16,185,129,0.12)',  color: '#6ee7b7', letter: 'A' },
};
const DEFAULT_CAT = { bg: 'rgba(255,255,255,0.06)', color: '#8892a4', letter: '—' };

function renderHighlights(highlights) {
  resHighlights.innerHTML = '';
  highlights.forEach(h => {
    const cat = CAT_STYLES[h.category] || DEFAULT_CAT;
    const div = document.createElement('div');
    div.className = 'highlight-item';
    div.innerHTML = `
      <div class="highlight-icon" style="background:${cat.bg};">
        <span style="font-size:13px;font-weight:700;color:${cat.color}">${cat.letter}</span>
      </div>
      <div class="highlight-body">
        <div class="highlight-category" style="color:${cat.color}">${escHtml(h.category)}</div>
        <div class="highlight-title">${escHtml(h.title)}</div>
        <div class="highlight-desc">${escHtml(h.description)}</div>
        ${h.impact ? `<span class="highlight-impact">${escHtml(h.impact)}</span>` : ''}
      </div>
    `;
    resHighlights.appendChild(div);
  });
}

// ── ATS Score ─────────────────────────────────────────────────────────────────
function renderATS(ats) {
  const score = ats.overall;
  const cls   = scoreColorClass(score);

  resATSNum.textContent     = score;
  resATSNum.className       = `score-number ${cls}`;
  resATSGrade.textContent   = ats.grade;
  resATSGrade.className     = `score-grade ${cls}`;
  resATSSummary.textContent = ats.summary;

  const CIRC = 2 * Math.PI * 54;
  gaugeCircle.style.strokeDasharray  = CIRC;
  gaugeCircle.style.strokeDashoffset = CIRC;
  requestAnimationFrame(() => requestAnimationFrame(() => {
    gaugeCircle.style.strokeDashoffset = CIRC - (score / 100) * CIRC;
  }));

  resSubscores.innerHTML = '';
  (ats.subscores || []).forEach(s => {
    const pct    = Math.round((s.score / s.max_score) * 100);
    const barCls = barColorClass(pct);
    const sCls   = scoreColorClass(pct);
    const div    = document.createElement('div');
    div.className = 'subscore-item';
    div.innerHTML = `
      <div class="subscore-header">
        <span>${escHtml(s.label)}</span>
        <span class="${sCls}">${s.score} / ${s.max_score}</span>
      </div>
      <div class="subscore-bar-track">
        <div class="subscore-bar-fill ${barCls}" data-pct="${pct}" style="width:0%"></div>
      </div>
      <div style="font-size:11px;color:var(--text-muted);margin-top:4px;">${escHtml(s.feedback)}</div>
    `;
    resSubscores.appendChild(div);
  });
  setTimeout(() => {
    document.querySelectorAll('.subscore-bar-fill').forEach(bar => {
      bar.style.width = bar.dataset.pct + '%';
    });
  }, 100);
}

// ── Tips ──────────────────────────────────────────────────────────────────────
function renderTips(tips) {
  resTips.innerHTML = '';
  tips.forEach(t => {
    const cls = ({ High: 'priority-high', Medium: 'priority-medium', Low: 'priority-low' })[t.priority] || 'priority-low';
    const div = document.createElement('div');
    div.className = 'tip-item';
    div.innerHTML = `
      <span class="tip-priority ${cls}">${t.priority}</span>
      <div class="tip-content">
        <div class="tip-area">${escHtml(t.area)}</div>
        <div class="tip-suggestion">${escHtml(t.suggestion)}</div>
      </div>
    `;
    resTips.appendChild(div);
  });
}

// ── Reset ─────────────────────────────────────────────────────────────────────
document.getElementById('new-analysis-btn').addEventListener('click', resetUI);
document.getElementById('new-convert-btn').addEventListener('click', resetUI);

function resetUI() {
  results.classList.remove('show');
  convertResults.classList.remove('show');
  selectedFile  = null;
  convertedBlob = null;
  fileInput.value = '';
  fileBadge.classList.remove('show');
  resumeTextArea.value = '';
  jdTextArea.value = '';
  hideError();
  uploadCard.style.display = '';
  uploadCard.scrollIntoView({ behavior: 'smooth' });
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function validateInput() {
  hideError();
  if (activeTab === 'file' && !selectedFile) {
    showError('Please upload a resume file first.');
    return false;
  }
  if (activeTab === 'text' && !resumeTextArea.value.trim()) {
    showError('Please paste your resume text first.');
    return false;
  }
  return true;
}

function buildFormData() {
  const fd = new FormData();
  if (activeTab === 'file') fd.append('file', selectedFile);
  else fd.append('text', resumeTextArea.value.trim());

  const jdVal = jdTextArea.value.trim();
  if (jdVal) {
    fd.append('job_description', jdVal);
  }
  return fd;
}

function setLoading(on, title) {
  analyzeBtn.disabled = on;
  if (on) {
    btnText.textContent = activeMode === 'convert' ? 'Converting…' : 'Analyzing…';
    loadingTitle.textContent = title || 'Processing…';
  } else {
    btnText.textContent = activeMode === 'convert' ? 'Convert Resume' : 'Analyze Resume';
  }
  loadingOverlay.classList.toggle('show', on);
  uploadCard.style.display = on ? 'none' : '';
}

function cycleSteps(steps) {
  let i = 0;
  loadingStep.textContent = steps[0];
  return setInterval(() => {
    i = (i + 1) % steps.length;
    loadingStep.textContent = steps[i];
  }, 1800);
}

function showError(msg) {
  errorMsg.textContent = msg;
  errorBanner.classList.add('show');
}
function hideError() {
  errorBanner.classList.remove('show');
}

function getInitials(name) {
  return name.split(' ').filter(Boolean).slice(0, 2).map(n => n[0].toUpperCase()).join('');
}

function escHtml(str) {
  if (!str) return '';
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function scoreColorClass(score) {
  if (score >= 80) return 'score-excellent';
  if (score >= 60) return 'score-good';
  if (score >= 40) return 'score-fair';
  return 'score-poor';
}
function barColorClass(pct) {
  if (pct >= 80) return 'bar-excellent';
  if (pct >= 60) return 'bar-good';
  if (pct >= 40) return 'bar-fair';
  return 'bar-poor';
}
