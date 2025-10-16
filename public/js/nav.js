/* ============================================
   Navigation Toggle Logic
   Created: 2025-10-15
   ============================================ */

   document.addEventListener('DOMContentLoaded', function() {
    const navToggle = document.getElementById('nav-toggle');
    const sideNav = document.getElementById('side-nav');
    const navOverlay = document.getElementById('nav-overlay');
    const navLinks = document.querySelectorAll('#side-nav a');
  
    // Toggle navigation open/close
    navToggle.addEventListener('click', function(e) {
      e.stopPropagation();
      toggleNav();
    });
  
    // Close nav when clicking overlay
    navOverlay.addEventListener('click', function() {
      closeNav();
    });
  
    // Close nav when clicking a link
    navLinks.forEach(link => {
      link.addEventListener('click', function() {
        closeNav();
      });
    });
  
    // Close nav when clicking outside
    document.addEventListener('click', function(e) {
      if (sideNav.classList.contains('nav-expanded')) {
        if (!sideNav.contains(e.target) && e.target !== navToggle) {
          closeNav();
        }
      }
    });
  
    // Toggle function
    function toggleNav() {
      sideNav.classList.toggle('nav-expanded');
      navOverlay.classList.toggle('visible');
      navToggle.innerHTML = sideNav.classList.contains('nav-expanded') ? '✕' : '☰';
    }
  
    // Close function
    function closeNav() {
      sideNav.classList.remove('nav-expanded');
      navOverlay.classList.remove('visible');
      navToggle.innerHTML = '☰';
    }
  
    // Set active page based on current URL
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';
    navLinks.forEach(link => {
      const linkPage = link.getAttribute('href').split('/').pop();
      if (linkPage === currentPage) {
        link.classList.add('active');
      }
    });
  });