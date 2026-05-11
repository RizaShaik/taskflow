/**
 * static/js/app.js
 * -----------------
 * FlowDesk — complete frontend application logic.
 *
 * Responsibilities:
 *   1. WebSocket connection + real-time event handling
 *   2. REST API calls via fetch()
 *   3. Rendering task cards into the DOM
 *   4. Stats cards — computed from local state
 *   5. Modal open/close/save for task create & edit
 *   6. Filter buttons (all / pending / in_progress / completed)
 *   7. Analytics section — fetches and renders data
 *   8. Toast notifications
 *   9. Logout
 */

"use strict";

// ── App State ──────────────────────────────────────────────────────────────────
// We keep a local copy of all tasks so we can filter/count without
// re-fetching from the server every time.
let allTasks      = [];
let currentFilter = "all";
let editingTaskId = null;   // null = create mode; number = edit mode

// ══════════════════════════════════════════════════════════════════════════════
// WEBSOCKET SETUP
// ══════════════════════════════════════════════════════════════════════════════

// io() connects to the same host/port that served this page.
// Socket.IO tries WebSocket first, falls back to HTTP polling.
const socket = io({ transports: ["websocket", "polling"] });

socket.on("connect", () => {
  setWsIndicator(true);
  console.log("WebSocket connected:", socket.id);
});

socket.on("disconnect", (reason) => {
  setWsIndicator(false);
  console.log("WebSocket disconnected:", reason);
});

// ── Real-time task broadcast listeners ────────────────────────────────────────

socket.on("task_created", (task) => {
  // Guard: ignore if we already have this task
  // (happens when the current user created it — REST also adds it)
  if (!allTasks.find(t => t.id === task.id)) {
    allTasks.unshift(task);    // Newest first
    renderTaskList();
    updateStatCards();
    showToast(`New task added: "${task.title}"`, "info");
  }
});

socket.on("task_updated", (task) => {
  const idx = allTasks.findIndex(t => t.id === task.id);
  if (idx !== -1) {
    allTasks[idx] = task;
    renderTaskList();
    updateStatCards();
  }
});

socket.on("task_deleted", ({ id }) => {
  allTasks = allTasks.filter(t => t.id !== id);
  renderTaskList();
  updateStatCards();
});

// ── WebSocket status indicator ─────────────────────────────────────────────────
function setWsIndicator(connected) {
  const dot   = document.getElementById("ws-dot");
  const label = document.getElementById("ws-label");
  dot.className = "ws-dot" + (connected ? " connected" : "");
  label.textContent = connected ? "Live" : "Offline";
}

// ══════════════════════════════════════════════════════════════════════════════
// INITIALISATION
// ══════════════════════════════════════════════════════════════════════════════

document.addEventListener("DOMContentLoaded", () => {
  // Set the avatar letter from the username Jinja2 injected into the HTML
  const username = document.getElementById("sidebar-username") ||
                   { textContent: "?" };
  const usernameText = document.querySelector(".sidebar-username");
  const avatar       = document.getElementById("user-avatar");
  if (usernameText && usernameText.textContent.trim()) {
    avatar.textContent = usernameText.textContent.trim()[0].toUpperCase();
  }

  // Load all tasks on page open
  fetchTasks();
});

// ══════════════════════════════════════════════════════════════════════════════
// API HELPER
// ══════════════════════════════════════════════════════════════════════════════

/**
 * Wrapper around fetch() that:
 *   - Always sends JSON Content-Type header
 *   - Always includes session credentials (cookies)
 *   - Returns { ok: bool, data: parsed JSON }
 */
async function apiFetch(url, options = {}) {
  const response = await fetch(url, {
    headers:     { "Content-Type": "application/json" },
    credentials: "same-origin",
    ...options,
  });
  const data = await response.json();
  return { ok: response.ok, status: response.status, data };
}

// ══════════════════════════════════════════════════════════════════════════════
// TASK FETCHING & RENDERING
// ══════════════════════════════════════════════════════════════════════════════

async function fetchTasks() {
  const list = document.getElementById("task-list");
  list.innerHTML = `
    <div class="loading-state">
      <div class="spinner"></div> Loading tasks…
    </div>`;

  try {
    const { ok, data } = await apiFetch("/api/tasks");
    if (!ok) throw new Error(data.message || "Failed to load tasks");

    allTasks = data.data || [];
    renderTaskList();
    updateStatCards();

  } catch (err) {
    list.innerHTML = `
      <div class="empty-state">
        <p>⚠️ ${escHtml(err.message)}</p>
      </div>`;
  }
}

// ── Render the filtered task list into the DOM ─────────────────────────────────
function renderTaskList() {
  const list  = document.getElementById("task-list");
  const label = document.getElementById("task-count-label");

  // Apply current filter
  const filtered = currentFilter === "all"
    ? allTasks
    : allTasks.filter(t => t.status === currentFilter);

  const count = filtered.length;
  label.textContent = `${count} task${count !== 1 ? "s" : ""}`;

  // Empty state
  if (count === 0) {
    const msg = currentFilter === "all"
      ? "No tasks yet. Create your first one!"
      : `No ${currentFilter.replace("_", " ")} tasks.`;
    list.innerHTML = `
      <div class="empty-state">
        <svg width="48" height="48" fill="none" stroke="currentColor"
             stroke-width="1.5" viewBox="0 0 24 24">
          <rect x="3" y="3" width="18" height="18" rx="3"/>
          <path d="M9 12l2 2 4-4"/>
        </svg>
        <h3>${msg}</h3>
        <p>Use the "+ New Task" button to get started.</p>
      </div>`;
    return;
  }

  list.innerHTML = filtered.map(buildTaskCard).join("");
}

// ── Build a single task card HTML string ───────────────────────────────────────
function buildTaskCard(task) {
  const date = new Date(task.created_at).toLocaleDateString("en-IN", {
    day: "numeric", month: "short"
  });

  // Status label: "in_progress" → "In Progress"
  const statusLabel = task.status
    .split("_")
    .map(w => w[0].toUpperCase() + w.slice(1))
    .join(" ");

  const descHtml = task.description
    ? `<div class="task-desc">${escHtml(task.description)}</div>`
    : "";

  return `
    <div class="task-card"
         data-id="${task.id}"
         data-priority="${task.priority}"
         data-status="${task.status}">

      <div class="task-body">
        <div class="task-title">${escHtml(task.title)}</div>
        ${descHtml}
        <div class="task-meta">
          <span class="badge badge-${task.priority}">${task.priority}</span>
          <span class="badge badge-${task.status}">${statusLabel}</span>
          <span class="task-date">${date}</span>
        </div>
      </div>

      <div class="task-actions">
        <button class="btn btn-ghost btn-sm"
                onclick="openEditModal(${task.id})"
                title="Edit task">
          <!-- Pencil icon -->
          <svg width="13" height="13" fill="none" stroke="currentColor"
               stroke-width="2" viewBox="0 0 24 24">
            <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/>
            <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/>
          </svg>
        </button>
        <button class="btn btn-danger btn-sm"
                onclick="deleteTask(${task.id})"
                title="Delete task">
          <!-- Trash icon -->
          <svg width="13" height="13" fill="none" stroke="currentColor"
               stroke-width="2" viewBox="0 0 24 24">
            <polyline points="3 6 5 6 21 6"/>
            <path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6"/>
            <path d="M10 11v6M14 11v6"/>
          </svg>
        </button>
      </div>

    </div>`;
}

// ══════════════════════════════════════════════════════════════════════════════
// STAT CARDS
// ══════════════════════════════════════════════════════════════════════════════

// Recompute stats from local allTasks — no API call needed
function updateStatCards() {
  const total      = allTasks.length;
  const completed  = allTasks.filter(t => t.status === "completed").length;
  const inProgress = allTasks.filter(t => t.status === "in_progress").length;
  const pending    = allTasks.filter(t => t.status === "pending").length;
  const pct        = total ? Math.round((completed / total) * 100) : 0;

  document.getElementById("stat-total").textContent      = total;
  document.getElementById("stat-completed").textContent  = completed;
  document.getElementById("stat-inprogress").textContent = inProgress;
  document.getElementById("stat-pending").textContent    = pending;

  // Animate the progress bar to the new width
  document.getElementById("stat-progress").style.width = pct + "%";
}

// ══════════════════════════════════════════════════════════════════════════════
// FILTER BUTTONS
// ══════════════════════════════════════════════════════════════════════════════

function applyFilter(filter, btn) {
  currentFilter = filter;

  // Update button active state
  document.querySelectorAll(".filter-btn").forEach(b => {
    b.classList.remove("active");
  });
  btn.classList.add("active");

  renderTaskList();
}

// ══════════════════════════════════════════════════════════════════════════════
// MODAL — OPEN / CLOSE / SAVE
// ══════════════════════════════════════════════════════════════════════════════

function openModal() {
  editingTaskId = null;
  document.getElementById("modal-title").textContent = "New Task";
  document.getElementById("save-btn").textContent    = "Save Task";
  // Clear form fields
  document.getElementById("t-title").value    = "";
  document.getElementById("t-desc").value     = "";
  document.getElementById("t-priority").value = "medium";
  document.getElementById("t-status").value   = "pending";
  clearModalAlert();
  showModal();
  document.getElementById("t-title").focus();
}

function openEditModal(taskId) {
  const task = allTasks.find(t => t.id === taskId);
  if (!task) return;

  editingTaskId = taskId;
  document.getElementById("modal-title").textContent = "Edit Task";
  document.getElementById("save-btn").textContent    = "Update Task";
  // Pre-fill with existing values
  document.getElementById("t-title").value    = task.title;
  document.getElementById("t-desc").value     = task.description || "";
  document.getElementById("t-priority").value = task.priority;
  document.getElementById("t-status").value   = task.status;
  clearModalAlert();
  showModal();
  document.getElementById("t-title").focus();
}

function showModal()  {
  document.getElementById("modal-overlay").classList.add("open");
}

function closeModal() {
  document.getElementById("modal-overlay").classList.remove("open");
}

// Close when clicking the dark overlay (not the modal box itself)
function closeModalOnOutside(event) {
  if (event.target === document.getElementById("modal-overlay")) {
    closeModal();
  }
}

// Close on Escape key
document.addEventListener("keydown", e => {
  if (e.key === "Escape") closeModal();
});

// ── Save (create or update) ────────────────────────────────────────────────────
async function saveTask() {
  const title    = document.getElementById("t-title").value.trim();
  const desc     = document.getElementById("t-desc").value.trim();
  const priority = document.getElementById("t-priority").value;
  const status   = document.getElementById("t-status").value;

  // Client-side validation (server also validates)
  if (!title) {
    showModalAlert("Task title is required.", "error");
    document.getElementById("t-title").focus();
    return;
  }

  const btn = document.getElementById("save-btn");
  btn.disabled  = true;
  btn.innerHTML = '<span class="spinner"></span>';

  const payload  = { title, description: desc, priority, status };
  const isEdit   = editingTaskId !== null;
  const url      = isEdit ? `/api/tasks/${editingTaskId}` : "/api/tasks";
  const method   = isEdit ? "PUT" : "POST";

  try {
    const { ok, data } = await apiFetch(url, {
      method,
      body: JSON.stringify(payload),
    });

    if (!ok) {
      showModalAlert(data.message || "Save failed.", "error");
      return;
    }

    const savedTask = data.data;

    if (isEdit) {
      // Update local state
      const idx = allTasks.findIndex(t => t.id === savedTask.id);
      if (idx !== -1) allTasks[idx] = savedTask;
      showToast("Task updated!", "success");
    } else {
      // Prepend to local state
      allTasks.unshift(savedTask);
      showToast("Task created!", "success");
    }

    renderTaskList();
    updateStatCards();
    closeModal();

  } catch (err) {
    showModalAlert("Network error. Please try again.", "error");
  } finally {
    btn.disabled  = false;
    btn.textContent = isEdit ? "Update Task" : "Save Task";
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// DELETE TASK
// ══════════════════════════════════════════════════════════════════════════════

async function deleteTask(taskId) {
  if (!confirm("Delete this task? This cannot be undone.")) return;

  // Animate the card out first
  const card = document.querySelector(`.task-card[data-id="${taskId}"]`);
  if (card) card.classList.add("removing");

  try {
    const { ok, data } = await apiFetch(`/api/tasks/${taskId}`, {
      method: "DELETE",
    });

    if (!ok) throw new Error(data.message || "Delete failed");

    // Remove from local state
    allTasks = allTasks.filter(t => t.id !== taskId);

    // Wait for animation then re-render
    setTimeout(() => {
      renderTaskList();
      updateStatCards();
    }, 220);

    showToast("Task deleted.", "success");

  } catch (err) {
    // Undo the animation if delete failed
    if (card) card.classList.remove("removing");
    showToast(err.message, "error");
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// ANALYTICS
// ══════════════════════════════════════════════════════════════════════════════

async function loadAnalytics() {
  // Show loading spinner in trend table
  document.getElementById("trend-table").innerHTML = `
    <div class="loading-state"><div class="spinner"></div> Computing…</div>`;

  try {
    const { ok, data } = await apiFetch("/api/analytics");
    if (!ok) throw new Error(data.message || "Failed");

    const { summary, priority_distribution, daily_trend } = data.data;

    // ── Summary cards ──────────────────────────────────────────────────────────
    document.getElementById("ana-total").textContent = summary.total;
    document.getElementById("ana-score").textContent = summary.productivity_score + "%";
    document.getElementById("ana-pct").textContent   = summary.completion_percentage + "%";

    // Animate progress bar
    setTimeout(() => {
      document.getElementById("ana-progress").style.width =
        summary.completion_percentage + "%";
    }, 100);

    // ── Priority pills ─────────────────────────────────────────────────────────
    document.getElementById("ana-high").textContent   = priority_distribution.high;
    document.getElementById("ana-medium").textContent = priority_distribution.medium;
    document.getElementById("ana-low").textContent    = priority_distribution.low;

    // ── Daily trend table ──────────────────────────────────────────────────────
    renderTrendTable(daily_trend);

  } catch (err) {
    document.getElementById("trend-table").innerHTML = `
      <div class="empty-state" style="padding:2rem;">
        <p>Could not load analytics: ${escHtml(err.message)}</p>
      </div>`;
  }
}

function renderTrendTable(trend) {
  const container = document.getElementById("trend-table");

  if (!trend || trend.length === 0) {
    container.innerHTML = `
      <div class="empty-state" style="padding:2rem;">
        <p>No trend data yet. Create some tasks!</p>
      </div>`;
    return;
  }

  // Find max count for relative bar widths
  const max = Math.max(...trend.map(r => r.count), 1);

  container.innerHTML = trend.map(row => {
    const barWidth = Math.round((row.count / max) * 100);
    return `
      <div class="trend-row">
        <span class="trend-date">${row.date}</span>
        <div class="trend-bar-wrap">
          <div class="trend-bar-fill" style="width:${barWidth}%"></div>
        </div>
        <span class="trend-count">${row.count}</span>
      </div>`;
  }).join("");
}

// ══════════════════════════════════════════════════════════════════════════════
// SECTION SWITCHING (Dashboard ↔ Analytics)
// ══════════════════════════════════════════════════════════════════════════════

function showSection(name, linkEl) {
  // Toggle section visibility
  document.getElementById("section-dashboard").style.display =
    name === "dashboard" ? "block" : "none";
  document.getElementById("section-analytics").style.display =
    name === "analytics" ? "block" : "none";

  // Update page title
  document.getElementById("page-title").textContent =
    name === "dashboard" ? "Dashboard" : "Analytics";

  // Update active nav link
  document.querySelectorAll(".sidebar-nav a").forEach(a => {
    a.classList.remove("active");
  });
  if (linkEl) linkEl.classList.add("active");

  // Load analytics data when switching to that tab
  if (name === "analytics") loadAnalytics();

  // Close sidebar on mobile after navigation
  if (window.innerWidth <= 768) {
    document.getElementById("sidebar").classList.remove("open");
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// SIDEBAR MOBILE TOGGLE
// ══════════════════════════════════════════════════════════════════════════════

function toggleSidebar() {
  document.getElementById("sidebar").classList.toggle("open");
}

// Close sidebar when clicking outside on mobile
document.addEventListener("click", (e) => {
  const sidebar = document.getElementById("sidebar");
  const toggle  = document.querySelector(".menu-toggle");
  if (
    window.innerWidth <= 768 &&
    sidebar.classList.contains("open") &&
    !sidebar.contains(e.target) &&
    !toggle.contains(e.target)
  ) {
    sidebar.classList.remove("open");
  }
});

// ══════════════════════════════════════════════════════════════════════════════
// LOGOUT
// ══════════════════════════════════════════════════════════════════════════════

async function logout() {
  try {
    await apiFetch("/auth/api/logout", { method: "POST" });
  } catch (_) {
    // If the request fails, redirect anyway — session will expire naturally
  }
  window.location.href = "/auth/login";
}

// ══════════════════════════════════════════════════════════════════════════════
// TOAST NOTIFICATIONS
// ══════════════════════════════════════════════════════════════════════════════

function showToast(message, type = "info") {
  const icons = {
    success: `<svg class="toast-icon" width="16" height="16" fill="none"
               stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
               <circle cx="12" cy="12" r="10"/>
               <path d="M9 12l2 2 4-4"/></svg>`,
    error:   `<svg class="toast-icon" width="16" height="16" fill="none"
               stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
               <circle cx="12" cy="12" r="10"/>
               <line x1="15" y1="9" x2="9" y2="15"/>
               <line x1="9"  y1="9" x2="15" y2="15"/></svg>`,
    info:    `<svg class="toast-icon" width="16" height="16" fill="none"
               stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
               <circle cx="12" cy="12" r="10"/>
               <line x1="12" y1="8"  x2="12" y2="12"/>
               <line x1="12" y1="16" x2="12.01" y2="16"/></svg>`,
  };

  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    ${icons[type] || ""}
    <span>${escHtml(message)}</span>`;

  document.getElementById("toast-container").appendChild(toast);

  // Auto-remove after 3.5 seconds
  setTimeout(() => toast.remove(), 3500);
}

// ══════════════════════════════════════════════════════════════════════════════
// MODAL ALERT HELPERS
// ══════════════════════════════════════════════════════════════════════════════

function showModalAlert(message, type) {
  const el = document.getElementById("modal-alert");
  el.textContent = message;
  el.className   = `alert alert-${type} show`;
}

function clearModalAlert() {
  const el = document.getElementById("modal-alert");
  el.textContent = "";
  el.className   = "alert";
}

// ══════════════════════════════════════════════════════════════════════════════
// UTILITY
// ══════════════════════════════════════════════════════════════════════════════

/**
 * Escape HTML special characters to prevent XSS.
 * Always run user-provided strings through this before inserting into innerHTML.
 */
function escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}