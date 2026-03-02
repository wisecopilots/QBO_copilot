/* ============================================
   WiseCopilots — Main JavaScript
   ============================================ */

(function () {
  'use strict';

  /* ------------------------------------------
     Smooth Scroll for Anchor Links
  ------------------------------------------ */
  document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
    anchor.addEventListener('click', function (e) {
      e.preventDefault();
      var targetId = this.getAttribute('href').substring(1);
      var target = document.getElementById(targetId);
      if (!target) return;

      var navHeight = document.querySelector('.navbar').offsetHeight;
      var targetPosition = target.getBoundingClientRect().top + window.pageYOffset - navHeight;

      window.scrollTo({
        top: targetPosition,
        behavior: 'smooth'
      });

      // Close mobile menu if open
      var mobileNav = document.querySelector('.nav-links');
      if (mobileNav.classList.contains('nav-open')) {
        mobileNav.classList.remove('nav-open');
        document.querySelector('.nav-toggle').classList.remove('active');
        document.body.classList.remove('nav-body-lock');
      }
    });
  });

  /* ------------------------------------------
     Mobile Navigation Toggle
  ------------------------------------------ */
  var navToggle = document.querySelector('.nav-toggle');
  var navLinks = document.querySelector('.nav-links');

  navToggle.addEventListener('click', function () {
    navLinks.classList.toggle('nav-open');
    navToggle.classList.toggle('active');
    document.body.classList.toggle('nav-body-lock');
  });

  /* ------------------------------------------
     Navbar Background on Scroll
  ------------------------------------------ */
  var navbar = document.querySelector('.navbar');

  function handleNavScroll() {
    if (window.scrollY > 40) {
      navbar.classList.add('navbar-scrolled');
    } else {
      navbar.classList.remove('navbar-scrolled');
    }
  }

  window.addEventListener('scroll', handleNavScroll, { passive: true });
  handleNavScroll();

  /* ------------------------------------------
     Active Nav Link Highlighting
  ------------------------------------------ */
  var sections = document.querySelectorAll('section[id]');
  var navItems = document.querySelectorAll('.nav-links a');

  function highlightNav() {
    var scrollPos = window.scrollY + navbar.offsetHeight + 100;

    sections.forEach(function (section) {
      var top = section.offsetTop;
      var bottom = top + section.offsetHeight;
      var id = section.getAttribute('id');

      navItems.forEach(function (link) {
        if (link.getAttribute('href') === '#' + id) {
          if (scrollPos >= top && scrollPos < bottom) {
            link.classList.add('active');
          } else {
            link.classList.remove('active');
          }
        }
      });
    });
  }

  window.addEventListener('scroll', highlightNav, { passive: true });
  highlightNav();

  /* ------------------------------------------
     Intersection Observer — Fade-in Animations
  ------------------------------------------ */
  var animatedEls = document.querySelectorAll('.fade-in');

  if ('IntersectionObserver' in window) {
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12 });

    animatedEls.forEach(function (el) {
      observer.observe(el);
    });
  } else {
    // Fallback: show everything immediately
    animatedEls.forEach(function (el) {
      el.classList.add('visible');
    });
  }

  /* ------------------------------------------
     Contact Form Handling
  ------------------------------------------ */
  var form = document.getElementById('contact-form');

  if (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();

      var submitBtn = form.querySelector('button[type="submit"]');
      var originalText = submitBtn.textContent;
      submitBtn.textContent = 'Sending...';
      submitBtn.disabled = true;

      var formData = new FormData(form);

      fetch(form.action, {
        method: 'POST',
        body: formData,
        headers: {
          'Accept': 'application/json'
        }
      }).then(function (response) {
        if (response.ok) {
          form.reset();
          submitBtn.textContent = 'Sent!';
          submitBtn.classList.add('btn-success');
          setTimeout(function () {
            submitBtn.textContent = originalText;
            submitBtn.disabled = false;
            submitBtn.classList.remove('btn-success');
          }, 3000);
        } else {
          throw new Error('Form submission failed');
        }
      }).catch(function () {
        submitBtn.textContent = 'Error — Try Again';
        submitBtn.disabled = false;
        setTimeout(function () {
          submitBtn.textContent = originalText;
        }, 3000);
      });
    });
  }

  /* ------------------------------------------
     Typing effect for the code demo box
  ------------------------------------------ */
  var demoBox = document.querySelector('.demo-box');
  if (demoBox) {
    var observed = false;
    var demoObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting && !observed) {
          observed = true;
          demoBox.classList.add('demo-visible');
          demoObserver.unobserve(entry.target);
        }
      });
    }, { threshold: 0.3 });
    demoObserver.observe(demoBox);
  }

})();
