/* TalentLens core UI behaviours */
(function () {
  "use strict";

  function escapeHtml(str) {
    var div = document.createElement("div");
    div.textContent = String(str == null ? "" : str);
    return div.innerHTML;
  }

  /* ---------- Upload dropzone ---------- */
  function initDropzones() {
    document.querySelectorAll(".dropzone").forEach(function (dz) {
      var input = dz.querySelector('input[type="file"]');
      if (!input) return;
      dz.addEventListener("click", function () { input.click(); });
      dz.addEventListener("dragover", function (e) {
        e.preventDefault();
        dz.classList.add("dragover");
      });
      dz.addEventListener("dragleave", function () { dz.classList.remove("dragover"); });
      dz.addEventListener("drop", function (e) {
        e.preventDefault();
        dz.classList.remove("dragover");
        if (e.dataTransfer.files.length) input.files = e.dataTransfer.files;
        updateFileChip(input);
      });
      input.addEventListener("change", function () { updateFileChip(input); });
    });
  }

  function updateFileChip(input) {
    var chip = input.closest(".dropzone").querySelector(".file-chip");
    if (!chip) return;
    if (input.files && input.files.length) {
      chip.innerHTML = "Document attached: <strong>" + escapeHtml(input.files[0].name) + "</strong>";
      chip.classList.add("show");
    } else {
      chip.classList.remove("show");
    }
  }

  /* ---------- Pipeline loading overlay ---------- */
  function showLoading(steps) {
    var overlay = document.getElementById("loadingOverlay");
    if (!overlay) return;
    var list = overlay.querySelector(".pipeline-steps");
    list.innerHTML = steps.map(function (s, i) {
      return '<li data-step="' + i + '"><span class="step-dot">' + (i + 1) + '</span><span>' +
        escapeHtml(s) + "</span></li>";
    }).join("");
    overlay.classList.add("active");
    overlay.style.opacity = "1";

    var items = list.querySelectorAll("li");
    items.forEach(function (li, i) {
      setTimeout(function () {
        items.forEach(function (other) { other.classList.remove("active"); });
        li.classList.add("active");
        if (i === items.length - 1) {
          setTimeout(function () { li.classList.add("done"); }, 400);
        }
      }, i * 700);
    });
  }

  function hideLoading() {
    var overlay = document.getElementById("loadingOverlay");
    if (!overlay) return;
    overlay.style.opacity = "0";
    setTimeout(function () { overlay.classList.remove("active"); }, 300);
  }

/* ---------- Analyze form ---------- */

  function showFormError(box, message) {
    if (!box) return;
    box.textContent = message;
    box.classList.remove("hidden");
    box.scrollIntoView({ block: "center", behavior: "smooth" });
  }

  /* ---------- Results animations ---------- */
  function animateScoreRing() {
    var ring = document.querySelector(".ring-fill");
    if (!ring) return;
    var target = parseInt(ring.getAttribute("data-value") || "0", 10);
    var number = document.getElementById("scoreValue");
    var circumference = 628;
    var offset = circumference - (target / 100) * circumference;

    requestAnimationFrame(function () { ring.style.strokeDashoffset = offset; });

    if (number) {
      var start = 0;
      var duration = 1600;
      var startTime = null;
      function tick(ts) {
        if (!startTime) startTime = ts;
        var progress = Math.min((ts - startTime) / duration, 1);
        var eased = 1 - Math.pow(1 - progress, 3);
        number.textContent = Math.round(start + (target - start) * eased);
        if (progress < 1) requestAnimationFrame(tick);
      }
      requestAnimationFrame(tick);
    }
  }

  function animateProgressBars() {
    document.querySelectorAll(".progress-fill").forEach(function (fill) {
      var value = parseInt(fill.getAttribute("data-value") || "0", 10);
      setTimeout(function () { fill.style.width = value + "%"; }, 250);
    });
  }

  /* ---------- Resource modal ---------- */
  function initResourceModal() {
    var overlay = document.getElementById("resourceModal");
    if (!overlay) return;

    var closeBtn = overlay.querySelector(".modal-close");
    function close() {
      overlay.classList.remove("active");
      document.body.style.overflow = "";
    }
    closeBtn.addEventListener("click", close);
    overlay.addEventListener("click", function (e) {
      if (e.target === overlay) close();
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") close();
    });

    document.addEventListener("click", function (e) {
      var btn = e.target.closest("[data-open-resource]");
      if (!btn) return;
      openResourceModal(btn.getAttribute("data-open-resource"));
    });
  }

  function openResourceModal(skill) {
    var overlay = document.getElementById("resourceModal");
    if (!overlay) return;
    var body = overlay.querySelector(".modal-body");
    var title = overlay.querySelector(".modal-head h3");
    body.innerHTML =
      '<div class="text-center"><div class="spinner"></div><p class="muted">Loading resources for <strong>' +
      escapeHtml(skill) + "</strong>…</p></div>";
    title.textContent = skill;
    overlay.classList.add("active");
    document.body.style.overflow = "hidden";

    fetch("/api/resources/" + encodeURIComponent(skill))
      .then(function (res) { return res.json(); })
      .then(function (data) {
        var groups = {};
        data.resources.forEach(function (r) {
          var type = r.resource_type || "Resource";
          (groups[type] = groups[type] || []).push(r);
        });
        var typeOrder = ["Documentation", "Course", "Article", "Video", "Playlist"];
        var html = "";
        typeOrder.forEach(function (type) {
          if (!groups[type]) return;
          html += '<div class="resource-group"><h4>' + escapeHtml(type) + "</h4>";
          groups[type].forEach(function (r) {
            html +=
              '<div class="resource-item">' +
              "<div class=\"meta\"><strong>" + escapeHtml(r.title) + "</strong>" +
              escapeHtml(r.provider) + " · " + escapeHtml(r.difficulty) + "</div>" +
              '<a class="btn btn-sm btn-outline" href="' + escapeHtml(r.url) + '" target="_blank" rel="noopener noreferrer">' +
              (type === "Documentation" ? "Open Documentation" : type === "Video" ? "Watch Tutorial" : type === "Article" ? "Read Article" : "Open Resource") +
              "</a></div>";
          });
          html += "</div>";
        });
        body.innerHTML = html || '<p class="muted">No resources found for this skill.</p>';
      })
      .catch(function () {
        body.innerHTML = '<div class="alert alert-error">Could not load resources. Please try again.</div>';
      });
  }

document.addEventListener("DOMContentLoaded", function () {
  initDropzones();
  initAnalyzeForm();
  initResourceModal();
  animateScoreRing();
  animateProgressBars();
  initHistory();
  initTabs();
  
  // Page transition
  setTimeout(() => {
    const content = document.getElementById('page-content');
    if (content) content.classList.add('visible');
  }, 50);
  
  // Prevent instant navigation for better UX
  document.querySelectorAll('a[href]:not([target="_blank"])').forEach(link => {
    link.addEventListener('click', function(e) {
      const href = this.getAttribute('href');
      if (href && !href.startsWith('#') && !href.startsWith('javascript:')) {
        e.preventDefault();
        const content = document.getElementById('page-content');
        if (content) {
          // Add transitioning class to html for smoother experience
          document.documentElement.classList.add('transitioning');
          content.classList.remove('visible');
          setTimeout(() => {
            window.location.href = href;
            // Remove transitioning class after new page loads
            setTimeout(() => {
              document.documentElement.classList.remove('transitioning');
            }, 50);
          }, 400);
        }
      }
    });
  });
});

// Tab functionality
function initTabs() {
  document.querySelectorAll('.tabs').forEach(tabContainer => {
    const tabButtons = tabContainer.querySelectorAll('.tab-btn');
    const tabContents = tabContainer.parentElement.querySelectorAll('.tab-content');
    
    tabButtons.forEach((button, index) => {
      button.addEventListener('click', () => {
        // Remove active state from all buttons and contents
        tabButtons.forEach(btn => btn.classList.remove('active'));
        tabContents.forEach(content => content.classList.remove('active'));
        
        // Add active state to clicked button and corresponding content
        button.classList.add('active');
        if (tabContents[index]) {
          tabContents[index].classList.add('active');
        }
      });
    });
    
    // Set first tab as active by default if none are active
    if (tabButtons.length > 0 && !tabContainer.querySelector('.tab-btn.active')) {
      tabButtons[0].classList.add('active');
      if (tabContents[0]) {
        tabContents[0].classList.add('active');
      }
    }
  });
}

// History management
function initHistory() {
  // Load history from localStorage
  const history = JSON.parse(localStorage.getItem('talentlens-history') || '[]');
  
  // Update history link in nav if on any page
  updateHistoryLink();
}

function updateHistoryLink() {
  const historyLink = document.querySelector('a[href="/history"]');
  if (!historyLink) return;
  
  const history = JSON.parse(localStorage.getItem('talentlens-history') || '[]');
  const count = history.length;
  
  if (count > 0) {
    // Update or create badge
    let badge = historyLink.querySelector('.history-count');
    if (!badge) {
      badge = document.createElement('span');
      badge.className = 'history-count badge bg-danger ms-1';
      historyLink.appendChild(badge);
    }
    badge.textContent = count;
  } else {
    // Remove badge if exists
    const badge = historyLink.querySelector('.history-count');
    if (badge) {
      badge.remove();
    }
  }
}

// Let's modify the initAnalyzeForm function to add history tracking
function initAnalyzeForm() {
  var form = document.getElementById("analyzeForm");
  if (!form) return;

  var errorBox = document.getElementById("formError");
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    if (errorBox) errorBox.classList.add("hidden");

    var file = form.querySelector('input[name="resume"]');
    var resumeText = form.querySelector('textarea[name="resume_text"]');
    var jobText = form.querySelector('textarea[name="job_description"]');
    var hasFile = file && file.files && file.files.length;
    var hasResumeText = resumeText && resumeText.value.trim().length > 0;
    var hasJob = jobText && jobText.value.trim().length > 0;

    if (!hasFile && !hasResumeText) {
      showFormError(errorBox, "Please upload a resume or paste resume text.");
      return;
    }
    if (!hasJob) {
      showFormError(errorBox, "Please enter a job description.");
      return;
    }

    var btn = form.querySelector('button[type="submit"]');
    btn.disabled = true;

    var steps = [
      "Extracting Resume Text",
      "Extracting Skills",
      "Comparing Job Requirements",
      "Detecting Skill Gaps",
      "Generating Recommendations"
    ];
    showLoading(steps);

    var data = new FormData();
    if (hasFile) data.append("resume", file.files[0]);
    if (hasResumeText) data.append("resume_text", resumeText.value);
    data.append("job_description", jobText.value);

    fetch("/api/analyze", { method: "POST", body: data })
      .then(function (res) { return res.json().then(function (j) { return { ok: res.ok, body: j }; }); })
      .then(function (result) {
        if (!result.ok) throw new Error(result.body.error || "Analysis failed.");
        
        // Store resume, job text, and PDF info in localStorage temporarily for history
        var fileName = hasFile && file.files[0] ? file.files[0].name : '';
        var storeData = {
          resume_text: hasFile ? '' : resumeText.value,
          job_description: jobText.value,
          timestamp: new Date().toISOString(),
          pdf_file_id: result.body.pdf_file_id || null,
          pdf_filename: fileName || null
        };
        
        localStorage.setItem('talentlens-temp-analysis-data', JSON.stringify(storeData));
        
        window.location.href = "/results?token=" + encodeURIComponent(result.body.token);
      })
      .catch(function (err) {
        hideLoading();
        btn.disabled = false;
        showFormError(errorBox, err.message || "An unexpected error occurred.");
      });
  });
}

// On results page, read temp data and add to history (only if not already added)
document.addEventListener('DOMContentLoaded', function () {
  if (window.location.pathname === '/results') {
    const tempData = localStorage.getItem('talentlens-temp-analysis-data');
    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get('token');
    
    if (tempData && token) {
      const data = JSON.parse(tempData);
      
      // Check if this token is already in history to prevent duplicates
      const history = JSON.parse(localStorage.getItem('talentlens-history') || '[]');
      const alreadyExists = history.some(function(entry) { return entry.token === token; });
      
      if (!alreadyExists) {
        fetch('/api/analysis?token=' + encodeURIComponent(token))
          .then(function(res) { return res.json(); })
          .then(function(analysis) {
            var historyEntry = {
              id: Date.now(),
              timestamp: data.timestamp,
              resume_excerpt: data.resume_text ? data.resume_text.substring(0, 200) : analysis.resume_text_excerpt || '',
              job_excerpt: data.job_description ? data.job_description.substring(0, 200) : '',
              token: token,
              overall_score: analysis.overall_score,
              skill_match: analysis.skill_match,
              pdf_file_id: data.pdf_file_id || null,
              pdf_filename: data.pdf_filename || null
            };
            
            history.unshift(historyEntry);
            if (history.length > 50) history.pop();
            localStorage.setItem('talentlens-history', JSON.stringify(history));
            updateHistoryLink();
          })
          .catch(function(err) {
            console.error('Failed to save history:', err);
          });
      }
      
      // Clean up temp data regardless
      localStorage.removeItem('talentlens-temp-analysis-data');
    }
  }
});
})();