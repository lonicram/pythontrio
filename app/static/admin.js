// Client-side transition rules (server is authoritative; this drives button state only)
const ALLOWED = {
  new:       { btnVerify: true,  btnSuspend: false, btnReinstate: false, btnDelete: true  },
  verified:  { btnVerify: false, btnSuspend: true,  btnReinstate: false, btnDelete: true  },
  suspended: { btnVerify: false, btnSuspend: false, btnReinstate: true,  btnDelete: true  },
  deleted:   { btnVerify: false, btnSuspend: false, btnReinstate: false, btnDelete: false },
};

let currentProfileId = null;

// -----------------------------------------------
// View routing
// -----------------------------------------------

function showView(viewId) {
  document.getElementById('usersView').classList.toggle('hidden', viewId !== 'usersView');
  document.getElementById('detailView').classList.toggle('hidden', viewId !== 'detailView');
}

function showUsers() {
  loadUsers();
  showView('usersView');
}

// -----------------------------------------------
// Users list
// -----------------------------------------------

async function loadUsers() {
  try {
    const res = await fetch('/user-profiles/');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const profiles = (await res.json()).sort((a, b) => a.id - b.id);

    const countEl = document.getElementById('userCount');
    countEl.textContent = profiles.length;

    const tbody = document.getElementById('usersTableBody');
    tbody.innerHTML = '';

    profiles.forEach((p) => {
      const tr = document.createElement('tr');

      // ID cell — mono, right-aligned, muted
      const tdId = document.createElement('td');
      tdId.className = 'mono muted';
      tdId.style.textAlign = 'right';
      tdId.textContent = p.id;
      tr.appendChild(tdId);

      // Email cell — mono
      const tdEmail = document.createElement('td');
      tdEmail.className = 'mono';
      tdEmail.textContent = p.email;
      tr.appendChild(tdEmail);

      // Username cell — mono, muted em-dash if null
      const tdUsername = document.createElement('td');
      tdUsername.className = 'mono';
      if (p.username) {
        tdUsername.textContent = p.username;
      } else {
        tdUsername.textContent = '—';
        tdUsername.classList.add('muted');
      }
      tr.appendChild(tdUsername);

      // Status badge cell
      const tdStatus = document.createElement('td');
      tdStatus.appendChild(makeBadge(p.status));
      tr.appendChild(tdStatus);

      // Manage link cell — using addEventListener to avoid any escaping issues
      const tdAction = document.createElement('td');
      tdAction.style.textAlign = 'right';
      const manageLink = document.createElement('a');
      manageLink.href = '#';
      manageLink.className = 'manage-link';
      manageLink.textContent = 'Manage';
      manageLink.addEventListener('click', (e) => {
        e.preventDefault();
        openDetail(p.id);
      });
      tdAction.appendChild(manageLink);
      tr.appendChild(tdAction);

      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error('Failed to load users:', err);
  }
}

function makeBadge(status) {
  const span = document.createElement('span');
  span.className = `badge badge-${status}`;
  span.textContent = status;
  return span;
}

// -----------------------------------------------
// Detail view
// -----------------------------------------------

async function openDetail(id) {
  try {
    const res = await fetch(`/user-profiles/${id}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const profile = await res.json();
    renderProfile(profile);
    showView('detailView');
  } catch (err) {
    console.error('Failed to load profile:', err);
  }
}

function renderProfile(p) {
  currentProfileId = p.id;

  // Large state indicator: "● status"
  const indicator = document.getElementById('stateIndicator');
  indicator.textContent = `●  ${p.status}`;
  indicator.className = `state-${p.status}`;

  // Profile meta fields
  document.getElementById('dEmail').textContent = p.email;
  document.getElementById('dUsername').textContent = p.username || '—';

  // Apply allowed transitions to buttons
  const allowed = ALLOWED[p.status] || {};
  document.getElementById('btnVerify').disabled    = !allowed.btnVerify;
  document.getElementById('btnSuspend').disabled   = !allowed.btnSuspend;
  document.getElementById('btnReinstate').disabled = !allowed.btnReinstate;
  document.getElementById('btnDelete').disabled    = !allowed.btnDelete;

  clearError();
}

// -----------------------------------------------
// Transitions
// -----------------------------------------------

async function doTransition(target) {
  if (currentProfileId === null) return;
  clearError();

  try {
    const res = await fetch(`/user-profiles/${currentProfileId}/transition`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target }),
    });

    const body = await res.json();

    if (res.ok) {
      renderProfile(body);
    } else {
      showError(body.detail || 'Transition failed.');
    }
  } catch (err) {
    showError('Network error — please try again.');
    console.error('Transition error:', err);
  }
}

// -----------------------------------------------
// Error banner
// -----------------------------------------------

function showError(msg) {
  const banner = document.getElementById('errorBanner');
  banner.textContent = msg;
  banner.classList.remove('hidden');
}

function clearError() {
  const banner = document.getElementById('errorBanner');
  banner.textContent = '';
  banner.classList.add('hidden');
}

// -----------------------------------------------
// Init
// -----------------------------------------------

showUsers();
