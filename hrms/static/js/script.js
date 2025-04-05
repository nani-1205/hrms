// Add your custom JavaScript here
console.log("HRMS main script loaded.");

/**
 * Initialize Bootstrap Tooltips
 */
function initializeTooltips() {
  const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
  tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl);
  });
  console.log("Tooltips initialized.");
}

/**
 * Initialize Bootstrap client-side validation feedback
 */
function initializeBsValidation() {
  const forms = document.querySelectorAll('.needs-validation');
  Array.prototype.slice.call(forms)
    .forEach(function (form) {
      form.addEventListener('submit', function (event) {
        if (!form.checkValidity()) {
          event.preventDefault();
          event.stopPropagation();
        }
        form.classList.add('was-validated');
      }, false);
    });
   console.log("Bootstrap validation initialized.");
}

// --- Run initializations on DOMContentLoaded ---
document.addEventListener('DOMContentLoaded', function () {
  initializeTooltips();
  initializeBsValidation();

  // Add any other initial setup functions here
});

// --- Example of a reusable function ---
// function showLoadingSpinner(elementId) {
//   const target = document.getElementById(elementId);
//   if (target) {
//      target.innerHTML = '<div class="spinner-border spinner-border-sm" role="status"><span class="visually-hidden">Loading...</span></div>';
//   }
// }