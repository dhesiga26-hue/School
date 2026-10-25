"use strict";

const API = "/students";
const PAGE_SIZE = 8;

const state = {
  all: [],
  filtered: [],
  searchTerm: "",
  page: 1,
  sortKey: "name",
  sortDir: "asc",
  editingId: null,
  viewingId: null,
  deleteId: null,
  loading: false,
  view: "dashboard",
  error: null,
};

const els = {};

function grab() {
  if (!Object.keys(els).length) {
    const ids = [
      "apiStatus", "apiStatusText", "navCount", "pageTitle", "breadcrumb",
      "statGrid", "recentWrap", "courseWrap",
      "studentsBody", "rowCount", "pager", "loadError", "searchInput", "clearSearch",
      "addStudentBtn", "navAddBtn", "studentDialog", "studentForm", "modalTitle",
      "saveBtn", "formError",
      "detailDialog", "detailAvatar", "detailName", "detailMeta", "detailDob",
      "detailEmail", "detailPhone", "detailCourse", "detailCreated", "detailUpdated",
      "detailEditBtn", "detailCloseBtn",
      "confirmDialog", "confirmText", "confirmDelete", "confirmCancel",
      "toastStack", "sidebar", "sidebarScrim",
    ];
    for (const id of ids) els[id] = document.getElementById(id);
    els.views = {
      dashboard: document.getElementById("view-dashboard"),
      students: document.getElementById("view-students"),
    };
    els.menuToggle = document.getElementById("menuToggle");
    els.sidebarClose = document.getElementById("sidebarClose");
    els.fields = {
      id: document.getElementById("fieldId"),
      name: document.getElementById("fieldName"),
      dob: document.getElementById("fieldDob"),
      email: document.getElementById("fieldEmail"),
      phone: document.getElementById("fieldPhone"),
      course: document.getElementById("fieldCourse"),
    };
  }
  return els;
}

/* ---------- Helpers ---------- */

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function initials(name) {
  return String(name).trim().split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0].toUpperCase()).join("") || "?";
}

function fmtDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

function fmtDateTime(iso) {
  if (!iso) return "—";
  const d = new Date(String(iso).replace(" ", "T"));
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, { year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

function refreshIcons() {
  if (window.lucide && typeof window.lucide.createIcons === "function") {
    try { window.lucide.createIcons(); } catch { /* ignore */ }
  }
}

function toast(message, kind = "success") {
  const stack = grab().toastStack;
  const el = document.createElement("div");
  el.className = `toast ${kind}`;
  el.innerHTML = `<i data-lucide="${kind === "error" ? "circle-alert" : "circle-check"}"></i><span>${escapeHtml(message)}</span>`;
  stack.appendChild(el);
  refreshIcons();
  setTimeout(() => {
    el.style.transition = "opacity 0.25s, transform 0.25s";
    el.style.opacity = "0";
    el.style.transform = "translateX(12px)";
    setTimeout(() => el.remove(), 280);
  }, 3600);
}

async function api(path, options = {}) {
  const response = await fetch(path, { headers: { "Content-Type": "application/json" }, ...options });
  let body = null;
  const text = await response.text();
  if (text) {
    try { body = JSON.parse(text); } catch { body = text; }
  }
  if (!response.ok) {
    const detail = body && body.detail;
    let message = Array.isArray(detail)
      ? detail.map((e) => e.msg).join("; ")
      : String(detail || `Request failed (${response.status})`);
    const nested = message.match(/"msg"\s*:\s*"([^"]*)"/);
    if (nested) message = nested[1];
    if (/valid date/i.test(message)) message = "Invalid date of birth. Use the YYYY-MM-DD format.";
    throw new Error(message);
  }
  return body;
}

/* ---------- View switching ---------- */

const VIEW_META = {
  dashboard: { title: "Dashboard", crumb: "StudentHub · Overview" },
  students: { title: "All Students", crumb: "StudentHub · Student Records" },
};

function showView(view) {
  const e = grab();
  state.view = view;
  e.views.dashboard.classList.toggle("hidden", view !== "dashboard");
  e.views.students.classList.toggle("hidden", view !== "students");
  e.pageTitle.textContent = VIEW_META[view].title;
  e.breadcrumb.textContent = VIEW_META[view].crumb;
  document.querySelectorAll(".nav-item[data-view]").forEach((b) => b.classList.toggle("active", b.dataset.view === view));
  closeMobileNav();
  refreshIcons();
  if (view === "dashboard") renderDashboard();
  else renderStudents();
}

function closeMobileNav() {
  grab().sidebar.classList.remove("open");
  grab().sidebarScrim.classList.remove("show");
}

/* ---------- Data loading (real API only) ---------- */

async function loadStudents() {
  const e = grab();
  if (state.loading) return;
  state.loading = true;
  state.error = null;
  renderStudents();
  try {
    const params = state.searchTerm ? `?name=${encodeURIComponent(state.searchTerm)}` : "";
    const records = await api(API + params);
    state.all = records;
    applyFilterAndSort();
    e.navCount.textContent = records.length;
    if (state.view === "dashboard") renderDashboard();
    else renderStudents();
  } catch (err) {
    state.error = err.message;
    state.all = [];
    state.filtered = [];
    e.loadError.textContent = err.message;
    e.loadError.classList.remove("hidden");
    if (state.view === "dashboard") renderDashboard();
    else renderStudents();
  } finally {
    state.loading = false;
  }
}

function applyFilterAndSort() {
  const key = state.sortKey;
  const dir = state.sortDir === "asc" ? 1 : -1;
  state.filtered = state.all.slice().sort((a, b) => {
    const av = key === "date_of_birth" ? a[key] : String(a[key] || "").toLowerCase();
    const bv = key === "date_of_birth" ? b[key] : String(b[key] || "").toLowerCase();
    if (av < bv) return -1 * dir;
    if (av > bv) return 1 * dir;
    return 0;
  });
  const totalPages = Math.max(1, Math.ceil(state.filtered.length / PAGE_SIZE));
  if (state.page > totalPages) state.page = totalPages;
}

/* ---------- Dashboard (all metrics computed from real records) ---------- */

function renderDashboard() {
  const e = grab();
  const records = state.all;
  const hasError = state.error;

  const courseMap = {};
  for (const s of records) courseMap[s.course] = (courseMap[s.course] || 0) + 1;
  const courses = Object.entries(courseMap).sort((a, b) => b[1] - a[1]);
  const bornAfter = records.filter((s) => (s.date_of_birth || "") > "2005-12-31").length;

  const cards = [
    { featured: true, icon: "users", label: "Total students", value: records.length, sub: "From the live database" },
    { icon: "book-open", label: "Courses offered", value: courses.length },
    { icon: "sparkles", label: "Born after 2005", value: bornAfter },
    { icon: "graduation-cap", label: "Records tracked", value: records.length, sub: "Unique auto-generated IDs" },
  ];

  e.statGrid.innerHTML = records.length === 0 && hasError
    ? `<div class="state-box" style="grid-column:1/-1">
         <span class="state-icon"><i data-lucide="wifi-off"></i></span>
         <p>Could not load data</p>
         <span class="state-sub">${escapeHtml(hasError)}</span>
         <div class="state-actions"><button class="btn btn-primary" data-action="reload" type="button"><i data-lucide="refresh-cw"></i> Retry</button></div>
       </div>`
    : cards.map((c) => `
        <div class="stat-card ${c.featured ? "featured" : ""}">
          <span class="stat-icon"><i data-lucide="${c.icon}"></i></span>
          <div>
            <span class="stat-label">${c.label}</span>
            <span class="stat-value">${c.value}</span>
            ${c.sub ? `<span class="stat-sub">${c.sub}</span>` : ""}
          </div>
        </div>
      `).join("");

  const recent = records
    .slice()
    .sort((a, b) => (b.created_at || `${b.id}-0`).localeCompare(a.created_at || `${a.id}-0`) || b.id - a.id)
    .slice(0, 5);

  e.recentWrap.innerHTML = records.length === 0
    ? dashboardEmpty(hasError)
    : recent.map((s) => `
        <div class="recent-row">
          <span class="avatar" style="background:${avatarColor(s.name)}">${escapeHtml(initials(s.name))}</span>
          <div>
            <div class="r-name">${escapeHtml(s.name)}</div>
            <div class="r-course">${escapeHtml(s.course)}</div>
          </div>
          <span class="when">${fmtDate(s.created_at || s.date_of_birth)}</span>
        </div>
      `).join("");

  const maxCount = courses.length ? courses[0][1] : 1;
  e.courseWrap.innerHTML = courses.length === 0
    ? dashboardEmpty(hasError, "Enrolment by course", "Course distribution will appear here once students are added.", false)
    : courses.map(([name, count]) => `
        <div class="course-item">
          <div class="course-top">
            <strong>${escapeHtml(name)}</strong>
            <span class="course-count">${count} ${count === 1 ? "student" : "students"}</span>
          </div>
          <div class="course-bar"><span style="width:${(count / maxCount) * 100}%"></span></div>
        </div>
      `).join("");

  refreshIcons();
}

function dashboardEmpty(hasError, title, sub, withAdd) {
  const isError = Boolean(hasError);
  if (isError) {
    return `
      <div class="state-box">
        <span class="state-icon"><i data-lucide="wifi-off"></i></span>
        <p>Could not load data</p>
        <span class="state-sub">${escapeHtml(hasError)}</span>
        <div class="state-actions"><button class="btn btn-primary btn-sm" data-action="reload" type="button"><i data-lucide="refresh-cw"></i> Retry</button></div>
      </div>`;
  }
  return `
    <div class="state-box">
      <span class="state-icon"><i data-lucide="${withAdd === false ? "book-open" : "inbox"}"></i></span>
      <p>${escapeHtml(title || "No students yet")}</p>
      <span class="state-sub">${escapeHtml(sub || "Your student records will appear here once added.")}</span>
      ${withAdd !== false ? `<div class="state-actions"><button class="btn btn-primary btn-sm" data-action="add" type="button"><i data-lucide="user-plus"></i> Add Student</button></div>` : ""}
    </div>`;
}

function avatarColor(name) {
  const palette = ["#344767", "#3E5A8A", "#4A6B9C", "#5C7399", "#34507A", "#2E4E74"];
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = (hash * 31 + name.charCodeAt(i)) % 997;
  return palette[hash % palette.length];
}

/* ---------- Students table ---------- */

function emptyState(icon, title, sub, withAdd) {
  return `
    <div class="state-box">
      <span class="state-icon"><i data-lucide="${icon}"></i></span>
      <p>${escapeHtml(title)}</p>
      <span class="state-sub">${escapeHtml(sub)}</span>
      ${withAdd ? `<div class="state-actions"><button class="btn btn-primary btn-sm" data-action="add" type="button"><i data-lucide="user-plus"></i> Add Student</button></div>` : ""}
    </div>`;
}

function renderStudents() {
  const e = grab();
  e.loadError.classList.add("hidden");

  if (state.loading && state.all.length === 0) {
    e.studentsBody.innerHTML = '<tr class="skeleton-row"><td colspan="6">Loading…</td></tr><tr class="skeleton-row"><td colspan="6">Loading…</td></tr><tr class="skeleton-row"><td colspan="6">Loading…</td></tr>';
    e.rowCount.textContent = "loading…";
    renderPager();
    return;
  }

  if (state.error) {
    e.studentsBody.innerHTML = `<tr class="row-empty"><td colspan="6">${emptyState("wifi-off", "Could not load students", state.error, false)}</td></tr>`;
    e.rowCount.textContent = "0 records";
    renderPager();
    return;
  }

  const start = (state.page - 1) * PAGE_SIZE;
  const pageRows = state.filtered.slice(start, start + PAGE_SIZE);

  let html;
  if (state.filtered.length === 0) {
    html = state.searchTerm
      ? `<tr class="row-empty"><td colspan="6">${emptyState("search-x", "No matching students", `No results found for “${state.searchTerm}”.`, false)}</td></tr>`
      : `<tr class="row-empty"><td colspan="6">${emptyState("inbox", "No students found", "Your student records will appear here once added.", true)}</td></tr>`;
  } else {
    html = pageRows.map((s) => `
      <tr>
        <td>
          <div class="cell-student">
            <span class="avatar" style="background:${avatarColor(s.name)}">${escapeHtml(initials(s.name))}</span>
            <div class="details">
              <span class="cell-name">${escapeHtml(s.name)}</span>
              <span class="id-tag">ID ${s.id}</span>
            </div>
          </div>
        </td>
        <td>${fmtDate(s.date_of_birth)}</td>
        <td class="cell-email">${escapeHtml(s.email)}</td>
        <td>${escapeHtml(s.phone)}</td>
        <td>${escapeHtml(s.course)}</td>
        <td class="col-actions">
          <button class="link-btn" data-action="view" data-id="${s.id}">View</button>
          <button class="link-btn" data-action="edit" data-id="${s.id}">Edit</button>
          <button class="link-btn danger" data-action="delete" data-id="${s.id}">Delete</button>
        </td>
      </tr>
    `).join("");
  }

  e.studentsBody.innerHTML = html;
  e.rowCount.textContent = state.filtered.length === 0
    ? "0 records"
    : `${start + 1}–${Math.min(start + PAGE_SIZE, state.filtered.length)} of ${state.filtered.length} records`;
  renderPager();
  refreshIcons();
}

function renderPager() {
  const e = grab();
  const totalPages = Math.max(1, Math.ceil(state.filtered.length / PAGE_SIZE));

  const pages = [];
  const windowStart = Math.max(1, Math.min(state.page - 2, totalPages - 4));
  for (let p = windowStart; p <= Math.min(totalPages, windowStart + 4); p++) pages.push(p);

  let html = `
    <div class="pager-nav">
      <button class="page-btn" data-page="prev" type="button" ${state.page <= 1 ? "disabled" : ""} aria-label="Previous page"><i data-lucide="chevron-left"></i></button>
    </div>`;
  if (pages[0] > 1) html += `<button class="page-btn" data-page="1" type="button">1</button><span class="page-spacer">…</span>`;
  for (const p of pages) html += `<button class="page-btn ${p === state.page ? "active" : ""}" data-page="${p}" type="button">${p}</button>`;
  if (pages[pages.length - 1] < totalPages) html += `<span class="page-spacer">…</span><button class="page-btn" data-page="${totalPages}" type="button">${totalPages}</button>`;
  html += `
    <div class="pager-nav">
      <button class="page-btn" data-page="next" type="button" ${state.page >= totalPages ? "disabled" : ""} aria-label="Next page"><i data-lucide="chevron-right"></i></button>
    </div>`;

  e.pager.innerHTML = html;
  refreshIcons();
}

function goToPage(page) {
  const totalPages = Math.max(1, Math.ceil(state.filtered.length / PAGE_SIZE));
  if (page === "prev") page = Math.max(1, state.page - 1);
  else if (page === "next") page = Math.min(totalPages, state.page + 1);
  else page = Number(page);
  page = Math.max(1, Math.min(totalPages, page));
  if (page !== state.page) {
    state.page = page;
    renderStudents();
  }
}

/* ---------- Create / Edit ---------- */

function openCreate() {
  const e = grab();
  state.editingId = null;
  setupSaveButton("Add Student", false);
  resetForm();
  e.studentDialog.showModal();
  setTimeout(() => e.fields.name.focus(), 50);
}

function openEdit(student) {
  const e = grab();
  state.editingId = student.id;
  setupSaveButton("Save Changes", true);
  e.fields.id.value = student.id;
  e.fields.name.value = student.name;
  e.fields.dob.value = student.date_of_birth;
  e.fields.email.value = student.email;
  e.fields.phone.value = student.phone;
  e.fields.course.value = student.course;
  clearFieldErrors();
  e.formError.classList.add("hidden");
  e.studentDialog.showModal();
  setTimeout(() => e.fields.name.focus(), 50);
}

function setupSaveButton(label, isEdit) {
  const e = grab();
  e.modalTitle.textContent = isEdit ? "Edit Student" : "Add Student";
  e.saveBtn.innerHTML = `<i data-lucide="check"></i> ${label}`;
  refreshIcons();
}

function resetForm() {
  const e = grab();
  e.studentForm.reset();
  clearFieldErrors();
  e.formError.classList.add("hidden");
}

function clearFieldErrors() {
  document.querySelectorAll(".field").forEach((f) => f.classList.remove("invalid"));
  document.querySelectorAll(".error").forEach((el) => (el.textContent = ""));
}

function markError(fieldName, message) {
  const input = document.querySelector(`.field input[name="${fieldName}"]`);
  const error = document.querySelector(`.error[data-for="${fieldName}"]`);
  if (input) input.closest(".field").classList.add("invalid");
  if (error) error.textContent = message;
}

function validateClient(payload) {
  clearFieldErrors();
  let valid = true;
  if (!payload.name) { markError("name", "Name is required."); valid = false; }
  if (!payload.date_of_birth) { markError("date_of_birth", "Date of birth is required."); valid = false; }
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(payload.email)) { markError("email", "Enter a valid email address."); valid = false; }
  if ((payload.phone || "").replace(/\D/g, "").length < 7) { markError("phone", "Enter a valid phone number."); valid = false; }
  if (!payload.course) { markError("course", "Course is required."); valid = false; }
  return valid;
}

async function submitStudent(event) {
  event.preventDefault();
  const e = grab();

  const payload = {
    name: e.fields.name.value.trim(),
    date_of_birth: e.fields.dob.value,
    email: e.fields.email.value.trim(),
    phone: e.fields.phone.value.trim(),
    course: e.fields.course.value.trim(),
  };

  if (!validateClient(payload)) return;

  e.saveBtn.disabled = true;
  e.saveBtn.lastChild.textContent = " Saving…";
  try {
    if (state.editingId === null) {
      await api(API, { method: "POST", body: JSON.stringify(payload) });
      toast("Student created successfully.");
    } else {
      await api(`${API}/${state.editingId}`, { method: "PUT", body: JSON.stringify(payload) });
      toast("Student updated successfully.");
    }
    e.studentDialog.close();
    await loadStudents();
  } catch (err) {
    const msg = String(err.message);
    if (/already/i.test(msg)) markError("email", "This email is already registered.");
    e.formError.textContent = msg;
    e.formError.classList.remove("hidden");
    toast(msg, "error");
  } finally {
    e.saveBtn.disabled = false;
  }
}

/* ---------- View / Delete ---------- */

function showDetail(student) {
  const e = grab();
  state.viewingId = student.id;
  e.detailAvatar.textContent = initials(student.name);
  e.detailAvatar.style.background = avatarColor(student.name);
  e.detailName.textContent = student.name;
  e.detailMeta.textContent = `Student ${student.id} · ${student.course}`;
  e.detailDob.textContent = fmtDate(student.date_of_birth);
  e.detailEmail.textContent = student.email;
  e.detailPhone.textContent = student.phone;
  e.detailCourse.textContent = student.course;
  e.detailCreated.textContent = fmtDateTime(student.created_at);
  e.detailUpdated.textContent = fmtDateTime(student.updated_at);
  e.detailDialog.showModal();
}

function openDelete(student) {
  const e = grab();
  state.deleteId = student.id;
  e.confirmText.textContent = `Delete ${student.name} (student ${student.id})?`;
  e.confirmDialog.showModal();
}

async function confirmDelete() {
  const e = grab();
  if (state.deleteId === null) return;
  const id = state.deleteId;
  e.confirmDelete.disabled = true;
  try {
    await api(`${API}/${id}`, { method: "DELETE" });
    toast("Student deleted successfully.");
    e.confirmDialog.close();
    await loadStudents();
  } catch (err) {
    toast(err.message, "error");
  } finally {
    e.confirmDelete.disabled = false;
    state.deleteId = null;
  }
}

/* ---------- Events ---------- */

function bindEvents() {
  const e = grab();
  let searchTimer = null;

  e.searchInput.addEventListener("input", () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      state.searchTerm = e.searchInput.value.trim();
      state.page = 1;
      loadStudents();
    }, 250);
  });

  e.clearSearch.addEventListener("click", () => {
    e.searchInput.value = "";
    state.searchTerm = "";
    state.page = 1;
    loadStudents();
  });

  e.addStudentBtn.addEventListener("click", openCreate);
  e.navAddBtn.addEventListener("click", openCreate);
  e.studentForm.addEventListener("submit", submitStudent);

  e.confirmCancel.addEventListener("click", () => e.confirmDialog.close());
  e.confirmDelete.addEventListener("click", confirmDelete);
  e.detailCloseBtn.addEventListener("click", () => e.detailDialog.close());
  e.detailEditBtn.addEventListener("click", () => {
    const student = state.all.find((s) => s.id === state.viewingId);
    e.detailDialog.close();
    if (student) openEdit(student);
  });

  document.querySelectorAll(".nav-item[data-view]").forEach((btn) => {
    btn.addEventListener("click", () => showView(btn.dataset.view));
  });

  document.querySelectorAll("[data-goto]").forEach((btn) => {
    btn.addEventListener("click", () => showView(btn.dataset.goto));
  });

  document.querySelectorAll("[data-dialog-close]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const dialog = document.getElementById(btn.dataset.dialogClose);
      if (dialog) dialog.close();
    });
  });

  e.pager.addEventListener("click", (event) => {
    const btn = event.target.closest(".page-btn");
    if (btn && !btn.disabled) goToPage(btn.dataset.page);
  });

  document.querySelector(".sort-btn")?.addEventListener("click", () => {
    state.sortDir = state.sortDir === "asc" ? "desc" : "asc";
    state.page = 1;
    applyFilterAndSort();
    renderStudents();
  });

  e.studentsBody.addEventListener("click", (event) => {
    const btn = event.target.closest("button[data-action]");
    if (!btn) return;
    if (btn.dataset.action === "add") { openCreate(); return; }
    if (btn.dataset.action === "reload") { loadStudents(); return; }
    const id = Number(btn.dataset.id);
    const student = state.all.find((s) => s.id === id);
    if (!student) return;
    if (btn.dataset.action === "view") showDetail(student);
    if (btn.dataset.action === "edit") openEdit(student);
    if (btn.dataset.action === "delete") openDelete(student);
  });

  e.statGrid.addEventListener("click", (event) => {
    const btn = event.target.closest("button[data-action='reload']");
    if (btn) loadStudents();
  });

  for (const dialog of [e.studentDialog, e.detailDialog, e.confirmDialog]) {
    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) dialog.close();
    });
  }

  e.menuToggle.addEventListener("click", () => {
    e.sidebar.classList.add("open");
    e.sidebarScrim.classList.add("show");
  });
  e.sidebarClose.addEventListener("click", closeMobileNav);
  e.sidebarScrim.addEventListener("click", closeMobileNav);
}

/* ---------- API status ---------- */

async function checkApi() {
  const e = grab();
  e.apiStatus.className = "api-chip checking";
  e.apiStatusText.textContent = "Checking API…";
  try {
    const res = await fetch("/");
    if (!res.ok) throw new Error("bad status");
    e.apiStatus.className = "api-chip online";
    e.apiStatusText.textContent = "API online";
  } catch {
    e.apiStatus.className = "api-chip offline";
    e.apiStatusText.textContent = "API offline";
  }
}

/* ---------- Boot ---------- */

document.addEventListener("DOMContentLoaded", () => {
  bindEvents();
  refreshIcons();
  checkApi();
  loadStudents();
  showView("dashboard");
});