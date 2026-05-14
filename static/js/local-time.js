(function () {
  function formatLocal(iso) {
    try {
      var d = new Date(iso);
      if (isNaN(d.getTime())) return null;
      return d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
    } catch (e) {
      return null;
    }
  }

  function applyKickoffTimes(root) {
    var scope = root || document;
    scope.querySelectorAll("time.kickoff-local").forEach(function (el) {
      var iso = el.getAttribute("datetime");
      if (!iso) return;
      var local = formatLocal(iso);
      if (local) {
        el.textContent = local;
        var tz = "";
        try {
          tz = Intl.DateTimeFormat().resolvedOptions().timeZone || "";
        } catch (e2) {}
        el.setAttribute("title", (tz ? tz + " · " : "") + iso);
      }
    });
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function renderTodayMatches(container, data) {
    if (!container) return;
    var tz = data.timezone || "";
    var date = data.date || "";
    var list = data.matches || [];
    if (!list.length) {
      container.innerHTML =
        '<p class="muted">No kickoffs scheduled in the database for <strong>' +
        escapeHtml(date) +
        "</strong> in your time zone" +
        (tz ? " (<code>" + escapeHtml(tz) + "</code>)" : "") +
        ".</p>";
      return;
    }
    var html =
      '<p class="muted small">Your local day: <strong>' +
      escapeHtml(date) +
      "</strong>" +
      (tz ? " · <code>" + escapeHtml(tz) + "</code>" : "") +
      "</p><ul class=\"list home-today-list\">";
    list.forEach(function (m) {
      var timeHtml = m.kickoff
        ? '<time class="kickoff-local muted small" datetime="' + escapeHtml(m.kickoff) + '"></time>'
        : '<span class="muted small">TBC</span>';
      var score =
        m.home_score != null && m.away_score != null
          ? m.home_score + "–" + m.away_score
          : "—";
      var pred =
        m.pred_scoreline != null
          ? '<span class="pred-inline">' + escapeHtml(String(m.pred_scoreline)) + "</span>"
          : "";
      html +=
        "<li><div><a href=\"" +
        escapeHtml(m.detail_url) +
        '">' +
        escapeHtml(m.home_code) +
        " vs " +
        escapeHtml(m.away_code) +
        "</a> <span class=\"muted small\">" +
        escapeHtml(m.round_name || "") +
        "</span></div><div class=\"home-today-meta\">" +
        timeHtml +
        " · " +
        escapeHtml(m.status) +
        " · <strong>" +
        score +
        "</strong> " +
        pred +
        "</div></li>";
    });
    html += "</ul>";
    container.innerHTML = html;
    applyKickoffTimes(container);
  }

  function loadTodayMatches(apiUrl) {
    var container = document.getElementById("home-today-matches");
    if (!container || !apiUrl) return;
    var tz;
    try {
      tz = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
    } catch (e) {
      tz = "UTC";
    }
    var url = apiUrl + (apiUrl.indexOf("?") >= 0 ? "&" : "?") + "tz=" + encodeURIComponent(tz);
    container.innerHTML = '<p class="muted small">Loading today’s fixtures…</p>';
    fetch(url, { credentials: "same-origin" })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        renderTodayMatches(container, data);
      })
      .catch(function () {
        container.innerHTML =
          '<p class="muted">Could not load today’s fixtures. Try refreshing the page.</p>';
      });
  }

  document.addEventListener("DOMContentLoaded", function () {
    applyKickoffTimes(document);
    var api = document.body && document.body.getAttribute("data-today-matches-api");
    if (api) loadTodayMatches(api);
  });

  window.GoalLineLocalTime = { applyKickoffTimes: applyKickoffTimes, loadTodayMatches: loadTodayMatches };
})();
