/* ===================================================
   SCRIPT.JS – CV website functionality
   - Language switcher (EN ↔ CZ)
   - Navbar scroll behaviour & active section highlighting
   - Skill bar animations (Intersection Observer)
   - Entrance fade-in animations
   - Floating hero particles
   - Mobile menu
   - Contact form
   =================================================== */

/* ============================================================
   LANGUAGE SWITCHER
   ============================================================ */
let currentLang = 'en';

function toggleLang() {
  currentLang = currentLang === 'en' ? 'cz' : 'en';
  applyLang();
}

function applyLang() {
  const label = document.getElementById('lang-label');

  // Update all data-en / data-cz elements
  document.querySelectorAll('[data-en]').forEach(el => {
    const text = el.getAttribute(`data-${currentLang}`);
    if (text) el.textContent = text;
  });

  // Toggle html lang attribute
  document.documentElement.lang = currentLang === 'en' ? 'en' : 'cs';

  // Update button label
  label.textContent = currentLang === 'en' ? 'EN → CZ' : 'CZ → EN';

  // Update page title
  document.title = currentLang === 'en'
    ? 'Michal Votýpka | IT Student & Athlete'
    : 'Michal Votýpka | IT Student & Atlet';
}

/* ============================================================
   NAVBAR – scroll & active link
   ============================================================ */
const navbar = document.getElementById('navbar');
const sections = document.querySelectorAll('section[id]');
const navLinks = document.querySelectorAll('.nav-link');

window.addEventListener('scroll', () => {
  // Sticky shadow
  if (window.scrollY > 20) {
    navbar.classList.add('scrolled');
  } else {
    navbar.classList.remove('scrolled');
  }

  // Active link highlighting
  let current = '';
  sections.forEach(sec => {
    const secTop = sec.offsetTop - 100;
    if (window.scrollY >= secTop) current = sec.id;
  });

  navLinks.forEach(link => {
    link.classList.remove('active');
    if (link.getAttribute('href') === `#${current}`) {
      link.classList.add('active');
    }
  });
}, { passive: true });

/* ============================================================
   MOBILE MENU
   ============================================================ */
function toggleMenu() {
  const hamburger = document.getElementById('hamburger');
  const navLinksList = document.getElementById('nav-links');
  hamburger.classList.toggle('open');
  navLinksList.classList.toggle('open');
}

// Close menu when a link is clicked
document.querySelectorAll('.nav-link').forEach(link => {
  link.addEventListener('click', () => {
    document.getElementById('hamburger').classList.remove('open');
    document.getElementById('nav-links').classList.remove('open');
  });
});

/* ============================================================
   SKILL BARS – animate on scroll into view
   ============================================================ */
const skillObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      const fill = entry.target;
      const width = fill.getAttribute('data-width');
      fill.style.width = width + '%';
      skillObserver.unobserve(fill);
    }
  });
}, { threshold: 0.3 });

document.querySelectorAll('.skill-bar-fill').forEach(el => {
  skillObserver.observe(el);
});

/* ============================================================
   ENTRANCE ANIMATIONS – fade-in on scroll
   ============================================================ */
const fadeObserver = new IntersectionObserver((entries) => {
  entries.forEach((entry, i) => {
    if (entry.isIntersecting) {
      setTimeout(() => {
        entry.target.classList.add('visible');
      }, i * 60);
      fadeObserver.unobserve(entry.target);
    }
  });
}, { threshold: 0.1 });

// Add fade-in-up class to key elements
const animatableSelectors = [
  '.info-card',
  '.timeline-card',
  '.skill-group',
  '.exp-card',
  '.gallery-item',
  '.other-int-card',
  '.contact-item',
  '.about-text p',
];

animatableSelectors.forEach(sel => {
  document.querySelectorAll(sel).forEach(el => {
    el.classList.add('fade-in-up');
    fadeObserver.observe(el);
  });
});

/* ============================================================
   HERO PARTICLES
   ============================================================ */
function createParticles() {
  const container = document.getElementById('particles');
  if (!container) return;

  const count = 40;

  for (let i = 0; i < count; i++) {
    const p = document.createElement('div');
    p.style.cssText = `
      position: absolute;
      border-radius: 50%;
      pointer-events: none;
      opacity: ${Math.random() * 0.5 + 0.05};
      background: ${Math.random() > 0.5 ? 'rgba(59,158,255,0.6)' : 'rgba(0,229,160,0.5)'};
      width: ${Math.random() * 4 + 1}px;
      height: ${Math.random() * 4 + 1}px;
      left: ${Math.random() * 100}%;
      top: ${Math.random() * 100}%;
      animation: particleDrift ${Math.random() * 10 + 8}s ease-in-out infinite;
      animation-delay: ${Math.random() * -12}s;
    `;
    container.appendChild(p);
  }

  // Inject particle keyframes
  if (!document.getElementById('particle-style')) {
    const style = document.createElement('style');
    style.id = 'particle-style';
    style.textContent = `
      @keyframes particleDrift {
        0%, 100% { transform: translate(0, 0); }
        33% { transform: translate(${Math.random() > 0.5 ? '' : '-'}${Math.floor(Math.random() * 30 + 10)}px, -${Math.floor(Math.random() * 40 + 10)}px); }
        66% { transform: translate(${Math.random() > 0.5 ? '' : '-'}${Math.floor(Math.random() * 20 + 5)}px, ${Math.floor(Math.random() * 20 + 5)}px); }
      }
    `;
    document.head.appendChild(style);
  }
}

createParticles();
applyLang();

/* ============================================================
   CONTACT FORM – demo handler
   ============================================================ */
function handleForm(e) {
  e.preventDefault();
  const btn = e.target.querySelector('button[type="submit"]');
  const successEl = document.getElementById('form-success');

  btn.textContent = currentLang === 'en' ? 'Sending…' : 'Odesílám…';
  btn.disabled = true;

  // Simulate async
  setTimeout(() => {
    btn.textContent = currentLang === 'en' ? 'Send Message' : 'Odeslat zprávu';
    btn.disabled = false;
    successEl.classList.remove('hidden');
    successEl.textContent = successEl.getAttribute(`data-${currentLang}`);
    e.target.reset();
    setTimeout(() => successEl.classList.add('hidden'), 5000);
  }, 800);
}

/* ============================================================
   SMOOTH NAV SCROLL (safety for older browsers)
   ============================================================ */
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
  anchor.addEventListener('click', function (e) {
    const target = document.querySelector(this.getAttribute('href'));
    if (target) {
      e.preventDefault();
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  });
});
