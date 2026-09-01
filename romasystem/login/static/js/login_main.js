/**
 * ROMA AUTOMOTORES - Login Interactions & Security Handling
 */

document.addEventListener('DOMContentLoaded', () => {
  // Elements
  const loginForm = document.getElementById('login-form');
  const emailInput = document.getElementById('email') || document.getElementById('username');
  const passwordInput = document.getElementById('password');
  const usernameError = document.getElementById('username-error');
  const passwordError = document.getElementById('password-error');
  const groupUsername = document.getElementById('group-username');
  const groupPassword = document.getElementById('group-password');
  const submitBtn = document.getElementById('btn-submit');
  const togglePasswordBtn = document.getElementById('toggle-password');
  const eyeShow = togglePasswordBtn.querySelector('.eye-show');
  const eyeHide = togglePasswordBtn.querySelector('.eye-hide');

  // Modals
  const modalForgot = document.getElementById('modal-forgot');
  const modalSecure = document.getElementById('modal-secure');
  const openForgotBtn = document.getElementById('open-forgot-modal');
  const closeForgotBtn = document.getElementById('close-forgot-modal');
  const cancelForgotBtn = document.getElementById('cancel-forgot-modal');
  const forgotForm = document.getElementById('forgot-form');
  const recoveryInput = document.getElementById('recovery-input');

  const openSecureBtn = document.getElementById('btn-secure-access');
  const closeSecureBtn = document.getElementById('close-secure-modal');
  const understandSecureBtn = document.getElementById('understand-secure-modal');

  const toastContainer = document.getElementById('toast-container');

  /* --------------------------------------------------------------------------
     1. Password Visibility Toggle
     -------------------------------------------------------------------------- */
  togglePasswordBtn.addEventListener('click', () => {
    const isPassword = passwordInput.type === 'password';
    passwordInput.type = isPassword ? 'text' : 'password';

    if (isPassword) {
      eyeShow.classList.add('hidden');
      eyeHide.classList.remove('hidden');
      togglePasswordBtn.setAttribute('aria-label', 'Ocultar contraseña');
    } else {
      eyeShow.classList.remove('hidden');
      eyeHide.classList.add('hidden');
      togglePasswordBtn.setAttribute('aria-label', 'Mostrar contraseña');
    }
  });

  /* --------------------------------------------------------------------------
     2. Input Error Reset on Input
     -------------------------------------------------------------------------- */
  function clearError(input, errorEl, groupEl) {
    const container = groupEl.querySelector('.input-container');
    if (container) container.classList.remove('has-error');
    errorEl.textContent = '';
    errorEl.classList.remove('visible');
  }

  function setError(input, errorEl, groupEl, message) {
    const container = groupEl.querySelector('.input-container');
    if (container) container.classList.add('has-error');
    errorEl.textContent = message;
    errorEl.classList.add('visible');
  }

  if (emailInput) {
    emailInput.addEventListener('input', () => {
      clearError(emailInput, usernameError, groupUsername);
    });
  }

  passwordInput.addEventListener('input', () => {
    clearError(passwordInput, passwordError, groupPassword);
  });

  /* --------------------------------------------------------------------------
     3. Form Validation & Submission
     -------------------------------------------------------------------------- */
  loginForm.addEventListener('submit', (e) => {
    let isValid = true;
    const emailVal = emailInput ? emailInput.value.trim() : '';
    const passwordVal = passwordInput.value;

    if (!emailVal) {
      setError(emailInput, usernameError, groupUsername, 'Por favor, ingresá tu email o usuario.');
      isValid = false;
    }

    if (!passwordVal) {
      setError(passwordInput, passwordError, groupPassword, 'Por favor, ingresá tu contraseña.');
      isValid = false;
    }

    if (!isValid) {
      e.preventDefault();
      return;
    }

    // Feedback visual al enviar formulario a Flask
    submitBtn.classList.add('loading');
  });

  /* --------------------------------------------------------------------------
     4. Modals Controller
     -------------------------------------------------------------------------- */
  function openModal(modal) {
    modal.classList.add('active');
    modal.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
  }

  function closeModal(modal) {
    modal.classList.remove('active');
    modal.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
  }

  // Forgot password modal
  openForgotBtn.addEventListener('click', () => openModal(modalForgot));
  closeForgotBtn.addEventListener('click', () => closeModal(modalForgot));
  cancelForgotBtn.addEventListener('click', () => closeModal(modalForgot));

  forgotForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const val = recoveryInput.value.trim();
    if (!val) {
      showToast('Por favor, ingresá un correo o usuario válido.', 'error');
      return;
    }

    closeModal(modalForgot);
    showToast(`Se ha enviado un enlace de restablecimiento a: ${val}`, 'info');
    recoveryInput.value = '';
  });

  // Secure access modal
  openSecureBtn.addEventListener('click', () => openModal(modalSecure));
  closeSecureBtn.addEventListener('click', () => closeModal(modalSecure));
  understandSecureBtn.addEventListener('click', () => closeModal(modalSecure));

  // Close modals on overlay backdrop click or Escape key
  [modalForgot, modalSecure].forEach((modal) => {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        closeModal(modal);
      }
    });
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      if (modalForgot.classList.contains('active')) closeModal(modalForgot);
      if (modalSecure.classList.contains('active')) closeModal(modalSecure);
    }
  });

  /* --------------------------------------------------------------------------
     5. Toast Notification System
     -------------------------------------------------------------------------- */
  function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    let iconSvg = '';
    if (type === 'success') {
      iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#16a34a" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
    } else if (type === 'error') {
      iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>`;
    } else {
      iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>`;
    }

    toast.innerHTML = `
      ${iconSvg}
      <span>${message}</span>
    `;

    toastContainer.appendChild(toast);

    // Trigger entrance transition
    requestAnimationFrame(() => {
      toast.classList.add('show');
    });

    // Remove toast after delay
    setTimeout(() => {
      toast.classList.remove('show');
      setTimeout(() => {
        toast.remove();
      }, 350);
    }, 4000);
  }
});
