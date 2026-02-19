// Liquid Glass Navbar JS

document.addEventListener('DOMContentLoaded', function() {
  const navIcons = document.querySelectorAll('.liquid-glass-navbar .nav-icon');
  navIcons.forEach(icon => {
    const dropdownId = icon.getAttribute('data-dropdown');
    if (dropdownId) {
      const dropdown = document.getElementById(dropdownId);
      // Desktop: open on hover
      icon.addEventListener('mouseenter', () => {
        if (window.innerWidth > 900) {
          closeAllDropdowns();
          dropdown.classList.add('open');
        }
      });
      icon.addEventListener('mouseleave', () => {
        if (window.innerWidth > 900) {
          setTimeout(() => dropdown.classList.remove('open'), 120);
        }
      });
      dropdown.addEventListener('mouseenter', () => {
        if (window.innerWidth > 900) dropdown.classList.add('open');
      });
      dropdown.addEventListener('mouseleave', () => {
        if (window.innerWidth > 900) dropdown.classList.remove('open');
      });
      // Mobile: open on tap
      icon.addEventListener('click', (e) => {
        if (window.innerWidth <= 900) {
          e.preventDefault();
          if (dropdown.classList.contains('open')) {
            dropdown.classList.remove('open');
          } else {
            closeAllDropdowns();
            dropdown.classList.add('open');
          }
        }
      });
    }
  });
  // Close all dropdowns on click outside
  document.addEventListener('click', function(e) {
    if (!e.target.closest('.liquid-glass-navbar') && !e.target.closest('.liquid-glass-dropdown')) {
      closeAllDropdowns();
    }
  });
  function closeAllDropdowns() {
    document.querySelectorAll('.liquid-glass-dropdown.open').forEach(d => d.classList.remove('open'));
  }
});
