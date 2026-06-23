/**
 * CropScan AI — script.js
 * Shared across all pages.
 * Handles: language switching, nav scroll, scan logic, results rendering.
 */

/* ══════════════════════════════════════════════════════════
   TRANSLATIONS
══════════════════════════════════════════════════════════ */
const translations = {
  en: {
    // Nav
    nav_home:  "Home",
    nav_scan:  "Scan",
    nav_guide: "Guide",
    nav_cta:   "Start Scanning",

    // Home — hero
    hero_badge:    "AI-Powered Plant Diagnostics",
    hero_title_1:  "Detect crop disease",
    hero_title_em: "in seconds.",
    hero_sub:      "Upload a leaf photo and our AI model analyses it instantly — identifying disease, confidence level, and tailored treatment recommendations.",
    hero_cta:      "Scan a Leaf →",
    hero_ghost:    "View Disease Guide",
    stat_acc:      "Accuracy",
    stat_species:  "Species",
    stat_diseases: "Diseases",

    // Home — how it works
    how_tag:   "HOW IT WORKS",
    how_title: "Three steps to a",
    how_em:    "diagnosis.",
    how_sub:   "No expertise needed. Just upload a photo and let the model do the rest.",
    step1_num:   "Step 01",
    step1_title: "Upload a Leaf Photo",
    step1_desc:  "Take a clear, well-lit photo of the affected leaf and upload it via drag & drop or file picker.",
    step2_num:   "Step 02",
    step2_title: "AI Analysis",
    step2_desc:  "Our deep learning model (ResNet-50, PlantVillage) inspects colour patterns, spots, and lesions.",
    step3_num:   "Step 03",
    step3_title: "Get Results",
    step3_desc:  "Receive the disease name, confidence score, pathogen identity, and a step-by-step treatment plan.",

    // Scan page
    scan_tag:       "CROP DISEASE SCANNER",
    scan_title:     "Upload a",
    scan_title_em:  "leaf image.",
    scan_sub:       "Supports JPG, PNG, and WEBP — max 10 MB. Use a clear, well-lit photo for best results.",
    upload_label:   "LEAF PHOTOGRAPH",
    upload_title:   "Drop your image here or",
    upload_strong:  "click to browse",
    upload_hint:    "JPG · PNG · WEBP · max 10 MB",
    analyse_btn:    "Analyse Leaf",
    loading_label:  "RUNNING INFERENCE…",
    lstep1: "Preprocessing",
    lstep2: "Feature Extract",
    lstep3: "Classification",
    lstep4: "Generating Report",
    empty_label:    "AWAITING INPUT",
    empty_text:     "Upload a leaf image to begin diagnosis.",
    divider_label:  "⟶",
    result_disease_label:    "DETECTED CONDITION",
    result_confidence_label: "CONFIDENCE SCORE",
    result_treatment_label:  "TREATMENT PROTOCOL",
    reset_btn: "↩ Scan Another Leaf",
    grade_high: "● HIGH CONFIDENCE",
    grade_med:  "◐ MODERATE",
    grade_low:  "○ LOW — VERIFY MANUALLY",

    // Guide page
    guide_tag:   "PLANT DISEASE GUIDE",
    guide_title: "Know your",
    guide_em:    "enemy.",
    guide_sub:   "Understanding common plant diseases helps you act before they spread.",

    // Footer
    footer_tagline: "AI-powered agriculture diagnostics for modern farming.",
    footer_product: "Product",
    footer_features: "Features",
    footer_accuracy: "Accuracy Report",
    footer_api:      "API Docs",
    footer_support:  "Support",
    footer_docs:     "Documentation",
    footer_contact:  "Contact",
    footer_privacy:  "Privacy Policy",
    footer_copy:     "© 2025 CropScan AI · Built for farmers, by scientists.",
  },

  hi: {
    nav_home:  "होम",
    nav_scan:  "स्कैन",
    nav_guide: "गाइड",
    nav_cta:   "स्कैन शुरू करें",

    hero_badge:    "AI-संचालित पौध निदान",
    hero_title_1:  "फसल रोग का",
    hero_title_em: "पता लगाएं।",
    hero_sub:      "पत्ती की फोटो अपलोड करें और हमारा AI मॉडल तुरंत विश्लेषण करेगा — रोग, आत्मविश्वास स्तर और उपचार की जानकारी देगा।",
    hero_cta:      "पत्ती स्कैन करें →",
    hero_ghost:    "रोग गाइड देखें",
    stat_acc:      "सटीकता",
    stat_species:  "प्रजातियाँ",
    stat_diseases: "रोग",

    how_tag:   "यह कैसे काम करता है",
    how_title: "निदान के",
    how_em:    "तीन चरण।",
    how_sub:   "कोई विशेषज्ञता की जरूरत नहीं। बस फोटो अपलोड करें।",
    step1_num:   "चरण 01",
    step1_title: "पत्ती की फोटो अपलोड करें",
    step1_desc:  "प्रभावित पत्ती की स्पष्ट, अच्छी रोशनी वाली फोटो लें और ड्रैग & ड्रॉप या फाइल पिकर से अपलोड करें।",
    step2_num:   "चरण 02",
    step2_title: "AI विश्लेषण",
    step2_desc:  "हमारा डीप लर्निंग मॉडल रंग पैटर्न, धब्बे और घावों की जाँच करता है।",
    step3_num:   "चरण 03",
    step3_title: "परिणाम प्राप्त करें",
    step3_desc:  "रोग का नाम, विश्वास स्कोर, रोगज़नक़ पहचान और उपचार योजना प्राप्त करें।",

    scan_tag:       "फसल रोग स्कैनर",
    scan_title:     "पत्ती की",
    scan_title_em:  "छवि अपलोड करें।",
    scan_sub:       "JPG, PNG, और WEBP समर्थित — अधिकतम 10 MB। सर्वोत्तम परिणाम के लिए स्पष्ट फोटो का उपयोग करें।",
    upload_label:   "पत्ती की तस्वीर",
    upload_title:   "छवि यहाँ खींचें या",
    upload_strong:  "ब्राउज़ करें",
    upload_hint:    "JPG · PNG · WEBP · अधिकतम 10 MB",
    analyse_btn:    "पत्ती का विश्लेषण करें",
    loading_label:  "विश्लेषण चल रहा है…",
    lstep1: "प्री-प्रोसेसिंग",
    lstep2: "फीचर निष्कर्षण",
    lstep3: "वर्गीकरण",
    lstep4: "रिपोर्ट तैयार",
    empty_label:    "इनपुट की प्रतीक्षा",
    empty_text:     "निदान शुरू करने के लिए पत्ती की छवि अपलोड करें।",
    divider_label:  "⟶",
    result_disease_label:    "पता लगाया गया रोग",
    result_confidence_label: "विश्वास स्कोर",
    result_treatment_label:  "उपचार प्रोटोकॉल",
    reset_btn: "↩ दूसरी पत्ती स्कैन करें",
    grade_high: "● उच्च विश्वास",
    grade_med:  "◐ मध्यम",
    grade_low:  "○ कम — मैन्युअल जाँच करें",

    guide_tag:   "पौध रोग गाइड",
    guide_title: "अपने",
    guide_em:    "दुश्मन को जानें।",
    guide_sub:   "सामान्य पौध रोगों को समझने से आप फैलने से पहले कार्रवाई कर सकते हैं।",

    footer_tagline: "आधुनिक खेती के लिए AI-संचालित कृषि निदान।",
    footer_product: "उत्पाद",
    footer_features: "विशेषताएँ",
    footer_accuracy: "सटीकता रिपोर्ट",
    footer_api:      "API डॉक्स",
    footer_support:  "सहायता",
    footer_docs:     "दस्तावेज़ीकरण",
    footer_contact:  "संपर्क",
    footer_privacy:  "गोपनीयता नीति",
    footer_copy:     "© 2025 CropScan AI · किसानों के लिए, वैज्ञानिकों द्वारा।",
  },

  mr: {
    nav_home:  "मुख्यपृष्ठ",
    nav_scan:  "स्कॅन",
    nav_guide: "मार्गदर्शिका",
    nav_cta:   "स्कॅन सुरू करा",

    hero_badge:    "AI-आधारित वनस्पती निदान",
    hero_title_1:  "पिकांच्या रोगाचे",
    hero_title_em: "क्षणात निदान.",
    hero_sub:      "पानाचा फोटो अपलोड करा आणि आमचे AI मॉडेल तात्काळ विश्लेषण करेल — रोग, आत्मविश्वास पातळी आणि उपचाराची माहिती देईल।",
    hero_cta:      "पान स्कॅन करा →",
    hero_ghost:    "रोग मार्गदर्शिका पहा",
    stat_acc:      "अचूकता",
    stat_species:  "प्रजाती",
    stat_diseases: "रोग",

    how_tag:   "हे कसे कार्य करते",
    how_title: "निदानाचे",
    how_em:    "तीन टप्पे.",
    how_sub:   "कोणत्याही तज्ञाची आवश्यकता नाही. फक्त फोटो अपलोड करा.",
    step1_num:   "टप्पा 01",
    step1_title: "पानाचा फोटो अपलोड करा",
    step1_desc:  "प्रभावित पानाचा स्पष्ट, चांगल्या प्रकाशातील फोटो घ्या आणि ड्रॅग & ड्रॉप किंवा फाइल पिकरने अपलोड करा.",
    step2_num:   "टप्पा 02",
    step2_title: "AI विश्लेषण",
    step2_desc:  "आमचे डीप लर्निंग मॉडेल रंग पॅटर्न, डाग आणि जखमांची तपासणी करते.",
    step3_num:   "टप्पा 03",
    step3_title: "निकाल मिळवा",
    step3_desc:  "रोगाचे नाव, विश्वास स्कोअर, रोगजंतू ओळख आणि उपचार योजना मिळवा.",

    scan_tag:       "पीक रोग स्कॅनर",
    scan_title:     "पानाची",
    scan_title_em:  "प्रतिमा अपलोड करा.",
    scan_sub:       "JPG, PNG, आणि WEBP समर्थित — कमाल 10 MB. सर्वोत्तम परिणामासाठी स्पष्ट फोटो वापरा.",
    upload_label:   "पानाचा फोटो",
    upload_title:   "येथे प्रतिमा टाका किंवा",
    upload_strong:  "ब्राउझ करा",
    upload_hint:    "JPG · PNG · WEBP · कमाल 10 MB",
    analyse_btn:    "पान विश्लेषण करा",
    loading_label:  "विश्लेषण सुरू आहे…",
    lstep1: "प्री-प्रोसेसिंग",
    lstep2: "फीचर एक्सट्रॅक्शन",
    lstep3: "वर्गीकरण",
    lstep4: "अहवाल तयार",
    empty_label:    "इनपुटची प्रतीक्षा",
    empty_text:     "निदान सुरू करण्यासाठी पानाची प्रतिमा अपलोड करा.",
    divider_label:  "⟶",
    result_disease_label:    "आढळलेला रोग",
    result_confidence_label: "विश्वास स्कोअर",
    result_treatment_label:  "उपचार प्रोटोकॉल",
    reset_btn: "↩ दुसरे पान स्कॅन करा",
    grade_high: "● उच्च विश्वास",
    grade_med:  "◐ मध्यम",
    grade_low:  "○ कमी — हाताने तपासा",

    guide_tag:   "वनस्पती रोग मार्गदर्शिका",
    guide_title: "आपल्या",
    guide_em:    "शत्रूला ओळखा.",
    guide_sub:   "सामान्य वनस्पती रोग समजून घेणे पसरण्याआधी कृती करण्यास मदत करते.",

    footer_tagline: "आधुनिक शेतीसाठी AI-आधारित कृषी निदान.",
    footer_product: "उत्पादन",
    footer_features: "वैशिष्ट्ये",
    footer_accuracy: "अचूकता अहवाल",
    footer_api:      "API डॉक्स",
    footer_support:  "सहाय्य",
    footer_docs:     "दस्तऐवजीकरण",
    footer_contact:  "संपर्क",
    footer_privacy:  "गोपनीयता धोरण",
    footer_copy:     "© 2025 CropScan AI · शेतकऱ्यांसाठी, शास्त्रज्ञांनी बनवले.",
  }
};

/* ══════════════════════════════════════════════════════════
   LANGUAGE ENGINE
══════════════════════════════════════════════════════════ */
let currentLang = localStorage.getItem('cropscan_lang') || 'en';

function t(key) {
  return (translations[currentLang] && translations[currentLang][key])
    || translations['en'][key]
    || key;
}

function applyTranslations() {
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    el.textContent = t(key);
  });
  document.querySelectorAll('[data-i18n-ph]').forEach(el => {
    el.placeholder = t(el.getAttribute('data-i18n-ph'));
  });
  // Update html lang attribute
  document.documentElement.lang = currentLang;
}

function initLangSelector() {
  const sel = document.getElementById('langSelect');
  if (!sel) return;
  sel.value = currentLang;
  sel.addEventListener('change', () => {
    currentLang = sel.value;
    localStorage.setItem('cropscan_lang', currentLang);
    applyTranslations();
  });
}

/* ══════════════════════════════════════════════════════════
   NAV SCROLL SHADOW
══════════════════════════════════════════════════════════ */
function initNavScroll() {
  const nav = document.querySelector('.nav');
  if (!nav) return;
  window.addEventListener('scroll', () => {
    nav.style.borderBottomColor = window.scrollY > 20
      ? 'rgba(82,183,136,0.28)'
      : 'rgba(82,183,136,0.15)';
  }, { passive: true });
}

/* Smooth scroll for anchor links */
function initSmoothScroll() {
  document.querySelectorAll('a[href^="#"]').forEach(link => {
    link.addEventListener('click', e => {
      const id = link.getAttribute('href').slice(1);
      const el = document.getElementById(id);
      if (!el) return;
      e.preventDefault();
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });
}

/* Step cards scroll animation */
function initStepCards() {
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.style.animationPlayState = 'running';
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.15 });

  document.querySelectorAll('.step-card').forEach((el, i) => {
    el.style.opacity = '0';
    el.style.animation = `fadeInUp 0.6s ${i * 0.15}s ease both paused`;
    observer.observe(el);
  });
}

/* Guide card entrance animation */
function initGuideCards() {
  const observer = new IntersectionObserver(entries => {
    entries.forEach((entry, i) => {
      if (entry.isIntersecting) {
        entry.target.style.animationPlayState = 'running';
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1 });

  document.querySelectorAll('.guide-card').forEach((el, i) => {
    el.style.opacity = '0';
    el.style.animation = `fadeInUp 0.6s ${i * 0.1}s ease both paused`;
    observer.observe(el);
  });
}

/* ══════════════════════════════════════════════════════════
   SCAN PAGE — UPLOAD & PREDICT
══════════════════════════════════════════════════════════ */
function initScanPage() {
  const uploadZone     = document.getElementById('uploadZone');
  if (!uploadZone) return; // not on scan page

  const fileInput      = document.getElementById('fileInput');
  const uploadDefault  = document.getElementById('uploadDefault');
  const uploadPreview  = document.getElementById('uploadPreview');
  const previewImg     = document.getElementById('previewImg');
  const removeBtn      = document.getElementById('removeBtn');
  const analyseBtn     = document.getElementById('analyseBtn');
  const uploadError    = document.getElementById('uploadError');
  const errorText      = document.getElementById('errorText');
  const resultsEmpty   = document.getElementById('resultsEmpty');
  const resultsLoading = document.getElementById('resultsLoading');
  const resultsData    = document.getElementById('resultsData');
  const loadingSteps   = document.getElementById('loadingSteps');
  const diseaseName    = document.getElementById('diseaseName');
  const pathogenName   = document.getElementById('pathogenName');
  const confidenceNum  = document.getElementById('confidenceNum');
  const confidenceGrade= document.getElementById('confidenceGrade');
  const confidenceBar  = document.getElementById('confidenceBar');
  const treatmentText  = document.getElementById('treatmentText');
  const resetBtn       = document.getElementById('resetBtn');

  let selectedFile = null;
  const ACCEPTED = ['image/jpeg', 'image/png', 'image/webp'];

  /* ── Drag & Drop ── */
  uploadZone.addEventListener('dragover', e => {
    e.preventDefault(); uploadZone.classList.add('dragover');
  });
  ['dragleave', 'dragend'].forEach(ev =>
    uploadZone.addEventListener(ev, () => uploadZone.classList.remove('dragover'))
  );
  uploadZone.addEventListener('drop', e => {
    e.preventDefault(); uploadZone.classList.remove('dragover');
    const f = e.dataTransfer.files[0]; if (f) handleFile(f);
  });
  uploadZone.addEventListener('click', e => {
    if (e.target === removeBtn || removeBtn.contains(e.target)) return;
    if (!selectedFile) fileInput.click();
  });
  fileInput.addEventListener('change', () => {
    if (fileInput.files[0]) handleFile(fileInput.files[0]);
  });

  /* ── File Handling ── */
  function handleFile(file) {
    if (!ACCEPTED.includes(file.type)) {
      showError('Invalid file type. Please upload a JPG, PNG, or WEBP image.'); return;
    }
    if (file.size > 10 * 1024 * 1024) {
      showError('File too large. Maximum allowed size is 10 MB.'); return;
    }
    hideError();
    selectedFile = file;
    const reader = new FileReader();
    reader.onload = e => {
      previewImg.src = e.target.result;
      uploadDefault.style.display = 'none';
      uploadPreview.style.display = 'flex';
      analyseBtn.disabled = false;
      showPanel('empty');
    };
    reader.readAsDataURL(file);
  }

  removeBtn.addEventListener('click', e => { e.stopPropagation(); resetUpload(); });

  /* ── Analyse → Real API ── */
  analyseBtn.addEventListener('click', async () => {
    if (!selectedFile) return;
    analyseBtn.disabled = true;
    showPanel('loading');
    animateLoadingSteps();

    const formData = new FormData();
    formData.append('image', selectedFile);

    try {
      const response = await fetch('/predict', { method: 'POST', body: formData });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || `Server error ${response.status}`);
      }
      if (data.error) {
        throw new Error(data.error);
      }

      await delay(600);
      displayResults(data);

    } catch (err) {
      await delay(400);
      showPanel('empty');
      showError(err.message || 'Something went wrong. Please try again.');
      analyseBtn.disabled = false;
    }
  });

  /* ── Display Results ── */
  function displayResults(data) {
    const { disease, confidence, suggestion } = data;

    const match = disease.match(/^(.*?)\s*\(([^)]+)\)\s*$/);
    if (match) {
      diseaseName.textContent  = match[1].trim();
      pathogenName.textContent = match[2].trim();
    } else {
      diseaseName.textContent  = disease || '—';
      pathogenName.textContent = '';
    }

    const confValue = parseFloat(String(confidence).replace('%', '')) || 0;
    confidenceNum.textContent = confValue.toFixed(1) + '%';

    if (confValue >= 90) confidenceGrade.textContent = t('grade_high');
    else if (confValue >= 70) confidenceGrade.textContent = t('grade_med');
    else confidenceGrade.textContent = t('grade_low');

    showPanel('results');
    requestAnimationFrame(() => requestAnimationFrame(() => {
      confidenceBar.style.width = Math.min(confValue, 100) + '%';
    }));
    treatmentText.textContent = suggestion || '—';
  }

  /* ── Loading steps animation ── */
  function animateLoadingSteps() {
    const steps = loadingSteps.querySelectorAll('.lstep');
    steps.forEach(s => s.classList.remove('active'));
    steps[0].classList.add('active');
    let i = 1;
    const iv = setInterval(() => {
      if (i >= steps.length) { clearInterval(iv); return; }
      steps.forEach(s => s.classList.remove('active'));
      steps[i].classList.add('active');
      i++;
    }, 900);
  }

  /* ── Panel switcher ── */
  function showPanel(state) {
    resultsEmpty.style.display   = state === 'empty'   ? 'flex' : 'none';
    resultsLoading.style.display = state === 'loading' ? 'flex' : 'none';
    resultsData.style.display    = state === 'results' ? 'flex' : 'none';
  }

  /* ── Reset ── */
  resetBtn.addEventListener('click', resetAll);
  function resetAll() { resetUpload(); showPanel('empty'); confidenceBar.style.width = '0%'; }
  function resetUpload() {
    selectedFile = null; fileInput.value = ''; previewImg.src = '';
    uploadPreview.style.display = 'none'; uploadDefault.style.display = 'flex';
    analyseBtn.disabled = true; hideError();
  }

  /* ── Error helpers ── */
  function showError(msg) { errorText.textContent = msg; uploadError.style.display = 'flex'; }
  function hideError() { uploadError.style.display = 'none'; }
}

/* ══════════════════════════════════════════════════════════
   UTILITY
══════════════════════════════════════════════════════════ */
function delay(ms) { return new Promise(r => setTimeout(r, ms)); }

/* ══════════════════════════════════════════════════════════
   INIT
══════════════════════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {
  initLangSelector();
  applyTranslations();
  initNavScroll();
  initSmoothScroll();
  initStepCards();
  initGuideCards();
  initScanPage();
});
