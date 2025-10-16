/* ============================================
   Navigation Toggle Logic
   Created: 2025-10-15
   ============================================ */

// Load navigation from external file
async function loadNav() {
    try {
        const response = await fetch('/nav.html');
        const navHtml = await response.text();
        document.body.insertAdjacentHTML('afterbegin', navHtml);
        initializeNav(); // Call AFTER nav HTML is loaded
    } catch (error) {
        console.error('Failed to load navigation:', error);
    }
}

function initializeNav() {
    // NOW set up the event listeners on the loaded nav elements
    const navToggle = document.getElementById('nav-toggle');
    const sideNav = document.getElementById('side-nav');
    const navOverlay = document.getElementById('nav-overlay');
    const navLinks = document.querySelectorAll('#side-nav a');

    if (!navToggle || !sideNav || !navOverlay) {
        console.error('Nav elements not found!');
        return;
    }

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

    // Toggle navigation open/close
    navToggle.addEventListener('click', function (e) {
        e.stopPropagation();
        toggleNav();
    });

    // Close nav when clicking overlay
    navOverlay.addEventListener('click', closeNav);

    // Close nav when clicking a link
    navLinks.forEach(link => {
        link.addEventListener('click', closeNav);
    });

    // Close nav when clicking outside
    document.addEventListener('click', function (e) {
        if (sideNav.classList.contains('nav-expanded')) {
            if (!sideNav.contains(e.target) && e.target !== navToggle) {
                closeNav();
            }
        }
    });

    // Set active page based on current URL
    const currentPage = window.location.pathname;
    navLinks.forEach(link => {
        const linkHref = link.getAttribute('href');
        if (linkHref === currentPage || 
            (currentPage === '/' && linkHref === '/') ||
            (currentPage.includes(linkHref) && linkHref !== '/')) {
            link.classList.add('active');
        }
    });
}

// Load nav when page loads
document.addEventListener('DOMContentLoaded', loadNav);

