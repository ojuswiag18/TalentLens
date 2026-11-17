/* TalentLens dashboard charts (Chart.js) */
(function () {
  "use strict";

  function chartColors() {
    var theme = document.documentElement.getAttribute("data-theme") || "light";
    return {
      primary: theme === "dark" ? "#60a5fa" : "#2563eb",
      secondary: theme === "dark" ? "#a78bfa" : "#7c3aed",
      success: theme === "dark" ? "#4ade80" : "#16a34a",
      warning: theme === "dark" ? "#fbbf24" : "#f59e0b",
      danger: theme === "dark" ? "#f87171" : "#dc2626",
      muted: theme === "dark" ? "#94a3b8" : "#64748b",
      grid: theme === "dark" ? "rgba(148,163,184,0.12)" : "rgba(100,116,139,0.15)",
      text: theme === "dark" ? "#f8fafc" : "#0f172a",
    };
  }

  function baseOptions(preserve) {
    var c = chartColors();
    return {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 1200, easing: "easeOutQuart" },
      plugins: {
        legend: {
          labels: { color: c.text, font: { family: "Inter", size: 12 } }
        }
      },
      scales: preserve ? undefined : {
        x: { ticks: { color: c.muted }, grid: { color: c.grid } },
        y: { ticks: { color: c.muted }, grid: { color: c.grid }, beginAtZero: true }
      }
    };
  }

  function renderCharts(data) {
    if (typeof Chart === "undefined") return;
    var c = chartColors();

    var el = function (id) { return document.getElementById(id); };

    var skillMatch = el("chartSkillMatch");
    if (skillMatch) {
      new Chart(skillMatch, {
        type: "doughnut",
        data: {
          labels: ["Matched Skills", "Missing Skills"],
          datasets: [{
            data: [data.skill_match_chart.matched, data.skill_match_chart.missing],
            backgroundColor: [c.success, c.danger],
            borderWidth: 0,
            hoverOffset: 6
          }]
        },
        options: baseOptions(true)
      });
    }

    var breakdown = el("chartBreakdown");
    if (breakdown) {
      new Chart(breakdown, {
        type: "bar",
        data: {
          labels: data.compatibility_breakdown.labels.map(function (l) { return l.charAt(0).toUpperCase() + l.slice(1); }),
          datasets: [{
            label: "Compatibility",
            data: data.compatibility_breakdown.values,
            backgroundColor: c.primary,
            borderRadius: 8,
            maxBarThickness: 46
          }]
        },
        options: baseOptions(false)
      });
    }

    var gap = el("chartGap");
    if (gap) {
      new Chart(gap, {
        type: "bar",
        data: {
          labels: ["Critical", "Important", "Optional"],
          datasets: [{
            label: "Missing skills by importance",
            data: [data.skill_gap_chart.critical, data.skill_gap_chart.important, data.skill_gap_chart.optional],
            backgroundColor: [c.danger, c.warning, c.primary],
            borderRadius: 8,
            maxBarThickness: 46
          }]
        },
        options: baseOptions(false)
      });
    }

    var distribution = el("chartDistribution");
    if (distribution && data.skill_distribution.labels.length) {
      new Chart(distribution, {
        type: "pie",
        data: {
          labels: data.skill_distribution.labels,
          datasets: [{
            data: data.skill_distribution.values,
            backgroundColor: ["#2563eb", "#7c3aed", "#0ea5e9", "#16a34a", "#f59e0b", "#dc2626", "#14b8a6", "#f43f5e"],
            borderWidth: 0,
            hoverOffset: 6
          }]
        },
        options: baseOptions(true)
      });
    }

    var kw = el("chartKeywords");
    if (kw) {
      new Chart(kw, {
        type: "doughnut",
        data: {
          labels: ["Matched Keywords", "Missing Keywords"],
          datasets: [{
            data: [data.keyword_chart.matched, data.keyword_chart.missing],
            backgroundColor: [c.secondary, c.muted],
            borderWidth: 0,
            hoverOffset: 6
          }]
        },
        options: baseOptions(true)
      });
    }
  }

  function init() {
    var el = document.getElementById("dashboardData");
    if (!el) return;
    var data;
    try {
      data = JSON.parse(el.textContent);
    } catch (e) {
      return;
    }
    renderCharts(data);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();