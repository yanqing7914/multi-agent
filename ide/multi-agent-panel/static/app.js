(function () {
  "use strict";

  const GATE_ORDER = [
    "explorers_complete",
    "workers_complete",
    "review_complete",
    "verify_complete",
    "scope_audit",
    "final_delivery",
  ];

  let pollTimer = null;

  function badgeClass(status) {
    if (status === "passed") return "passed";
    if (status === "failed") return "failed";
    return "pending";
  }

  function renderGates(gates) {
    const el = document.getElementById("gates");
    el.innerHTML = "";
    GATE_ORDER.forEach(function (name) {
      const gate = gates[name] || { status: "pending" };
      const span = document.createElement("span");
      span.className = "badge " + badgeClass(gate.status);
      span.textContent = name.replace(/_/g, " ") + ": " + (gate.status || "pending");
      el.appendChild(span);
    });
  }

  function renderTasks(tasks) {
    const body = document.getElementById("tasks-body");
    body.innerHTML = "";
    if (!tasks || !tasks.length) {
      body.innerHTML = '<tr><td colspan="6" class="empty">No tasks</td></tr>';
      return;
    }
    tasks.forEach(function (t) {
      const tr = document.createElement("tr");
      const reports = [];
      if (t.result_report_json) {
        reports.push('<a href="file://' + t.result_report_json + '" title="JSON">JSON</a>');
      }
      if (t.result_report_markdown) {
        reports.push('<a href="file://' + t.result_report_markdown + '" title="MD">MD</a>');
      }
      const preflight = (t.preflight_issues || []).join("; ") || (t.preflight && t.preflight.reason) || "—";
      tr.innerHTML =
        "<td>" + (t.task_id || "") + "</td>" +
        "<td>" + (t.role || "") + "</td>" +
        "<td>" + (t.session_name || "") + "</td>" +
        '<td><span class="status-pill ' + (t.status || "pending") + '">' + (t.status || "pending") + "</span></td>" +
        "<td>" + (reports.join(" · ") || "—") + "</td>" +
        "<td>" + preflight + "</td>";
      body.appendChild(tr);
    });
  }

  function renderFindings(findings) {
    const list = document.getElementById("findings-list");
    list.innerHTML = "";
    if (!findings || !findings.length) {
      list.innerHTML = '<li class="empty">No findings</li>';
      return;
    }
    findings.forEach(function (f) {
      const li = document.createElement("li");
      const sev = f.severity || "P2";
      const loc = f.target_file || f.file || "";
      const line = f.line ? ":" + f.line : "";
      li.innerHTML =
        '<span class="sev ' + sev + '">[' + sev + "]</span> " +
        (f.title || f.raw || JSON.stringify(f)) +
        (loc ? ' <span class="muted">(' + loc + line + ")</span>" : "");
      list.appendChild(li);
    });
  }

  function renderAudit(audit) {
    const box = document.getElementById("audit-content");
    if (!audit || !Object.keys(audit).length) {
      box.innerHTML = '<p class="empty">No audit run yet</p>';
      return;
    }
    const gate = (audit.gate && audit.gate.status) || audit.gate_status || "pending";
    const stale = audit.stale ? "yes" : "no";
    box.innerHTML =
      "<dl>" +
      "<dt>Gate</dt><dd>" + gate + "</dd>" +
      "<dt>OK</dt><dd>" + String(audit.ok) + "</dd>" +
      "<dt>Stale</dt><dd>" + stale + (audit.stale_reason ? " — " + audit.stale_reason : "") + "</dd>" +
      "<dt>Audit path</dt><dd>" + (audit.audit_path || "—") + "</dd>" +
      "<dt>Changed files digest</dt><dd>" + (audit.changed_files_digest || "—") + "</dd>" +
      "<dt>Violations</dt><dd>" + ((audit.violations || []).length) + "</dd>" +
      "<dt>Warnings</dt><dd>" + ((audit.warnings || []).length) + "</dd>" +
      "</dl>";
  }

  function renderPreflight(issues) {
    const list = document.getElementById("preflight-list");
    list.innerHTML = "";
    if (!issues || !issues.length) {
      list.innerHTML = '<li class="empty">None recorded</li>';
      return;
    }
    issues.forEach(function (item) {
      const li = document.createElement("li");
      li.textContent =
        (item.task_id || "?") + " (" + (item.session_name || item.role || "") + "): " +
        (item.reason || JSON.stringify(item));
      list.appendChild(li);
    });
  }

  function renderState(data) {
    const run = data.run || {};
    document.getElementById("task-title").textContent = run.task_title || "Multi-agent run";
    document.getElementById("run-id").textContent = "Run " + (run.run_id || "—");
    document.getElementById("current-phase").textContent = run.current_phase || "—";
    document.getElementById("last-sync").textContent = data.last_sync || "—";
    document.getElementById("summary-preview").textContent = data.summary_preview || "(No summary yet — run --summarize)";
    renderGates(data.gates || {});
    renderTasks(data.tasks || []);
    renderFindings(data.findings || []);
    renderAudit(data.latest_audit || {});
    renderPreflight(data.preflight_issues || []);
  }

  function fetchState() {
    return fetch("/api/state")
      .then(function (r) { return r.json(); })
      .then(renderState)
      .catch(function (err) {
        document.getElementById("task-title").textContent = "Error loading state";
        console.error(err);
      });
  }

  function schedulePoll(seconds) {
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = setInterval(fetchState, Math.max(2, seconds) * 1000);
  }

  function init() {
    fetch("/api/config")
      .then(function (r) { return r.json(); })
      .then(function (cfg) {
        const input = document.getElementById("refresh-interval");
        input.value = cfg.refresh_seconds || 5;
        document.getElementById("write-status").textContent = cfg.write_enabled
          ? "Write endpoints enabled on this server."
          : "Write endpoints disabled (read-only).";
        schedulePoll(Number(input.value));
      })
      .catch(function () { schedulePoll(5); });

    document.getElementById("btn-refresh").addEventListener("click", fetchState);
    document.getElementById("refresh-interval").addEventListener("change", function (e) {
      schedulePoll(Number(e.target.value) || 5);
      fetchState();
    });

    fetchState();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
