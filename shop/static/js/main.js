/**
 * Shop Manager — Main JavaScript Helper
 * Responsive mobile drawer, bottom dock, alerts, and touch ergonomics
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Mobile Drawer Navigation
    const navToggle = document.getElementById('navbarToggleBtn') || document.querySelector('.navbar-toggle-btn');
    const navMenu = document.getElementById('navbarMenu') || document.querySelector('.navbar-menu');
    const navBackdrop = document.getElementById('navBackdrop');
    const drawerCloseBtn = document.getElementById('mobileDrawerCloseBtn');
    const bottomNavMoreBtn = document.getElementById('bottomNavMoreBtn');

    function openMobileMenu() {
        if (!navMenu) return;
        navMenu.classList.add('open');
        if (navBackdrop) navBackdrop.classList.add('open');
        if (navToggle) {
            navToggle.classList.add('active');
            navToggle.setAttribute('aria-expanded', 'true');
        }
        document.body.classList.add('nav-open');
    }

    function closeMobileMenu() {
        if (!navMenu) return;
        navMenu.classList.remove('open');
        if (navBackdrop) navBackdrop.classList.remove('open');
        if (navToggle) {
            navToggle.classList.remove('active');
            navToggle.setAttribute('aria-expanded', 'false');
        }
        document.body.classList.remove('nav-open');
    }

    function toggleMobileMenu() {
        if (navMenu && navMenu.classList.contains('open')) {
            closeMobileMenu();
        } else {
            openMobileMenu();
        }
    }

    if (navToggle) {
        navToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleMobileMenu();
        });
    }

    if (bottomNavMoreBtn) {
        bottomNavMoreBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleMobileMenu();
        });
    }

    if (drawerCloseBtn) {
        drawerCloseBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            closeMobileMenu();
        });
    }

    if (navBackdrop) {
        navBackdrop.addEventListener('click', () => {
            closeMobileMenu();
        });
    }

    // Close menu when pressing ESC
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && navMenu && navMenu.classList.contains('open')) {
            closeMobileMenu();
        }
    });

    // Close menu when clicking outside or clicking any nav item
    document.addEventListener('click', (e) => {
        if (window.innerWidth <= 992 && navMenu && navMenu.classList.contains('open')) {
            if (!navMenu.contains(e.target) && (!navToggle || !navToggle.contains(e.target)) && (!bottomNavMoreBtn || !bottomNavMoreBtn.contains(e.target))) {
                closeMobileMenu();
            }
        }
    });

    if (navMenu) {
        navMenu.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', () => {
                if (window.innerWidth <= 992) {
                    closeMobileMenu();
                }
            });
        });
    }

    // Auto-close drawer if resized past mobile breakpoint
    window.addEventListener('resize', () => {
        if (window.innerWidth > 992 && navMenu && navMenu.classList.contains('open')) {
            closeMobileMenu();
        }
    });

    // 2. Desktop/Tablet Sidebar Toggle (if sidebar layout is used)
    const sidebar = document.querySelector('.sidebar');
    const toggleBtn = document.querySelector('.sidebar-toggle-btn');
    if (toggleBtn && sidebar) {
        toggleBtn.addEventListener('click', () => {
            sidebar.classList.toggle('open');
        });

        document.addEventListener('click', (e) => {
            if (window.innerWidth <= 900 &&
                sidebar.classList.contains('open') &&
                !sidebar.contains(e.target) &&
                !toggleBtn.contains(e.target)) {
                sidebar.classList.remove('open');
            }
        });
    }

    // 3. Alert Dismissal
    document.querySelectorAll('.alert-close').forEach(btn => {
        btn.addEventListener('click', () => {
            const alert = btn.closest('.alert');
            if (alert) {
                alert.style.opacity = '0';
                setTimeout(() => alert.remove(), 200);
            }
        });
    });

    // 4. Auto-hide alerts after 5 seconds
    setTimeout(() => {
        document.querySelectorAll('.alert-success').forEach(alert => {
            alert.style.transition = 'opacity 0.4s ease';
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 400);
        });
    }, 5000);
});
