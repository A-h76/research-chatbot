/* Public landing v2: theme, reveal, pipeline beam, router cascade, magic link. */
(function () {
  var root = document.documentElement;

  function systemPrefersDark() {
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  }

  function currentTheme() {
    var explicit = root.getAttribute("data-theme");
    if (explicit === "light" || explicit === "dark") return explicit;
    return systemPrefersDark() ? "dark" : "light";
  }

  function applyTheme(theme) {
    root.setAttribute("data-theme", theme);
    root.style.colorScheme = theme;
    try {
      localStorage.setItem("dhund-landing-theme", theme);
    } catch (e) {}
    var toggle = document.getElementById("theme-toggle");
    if (toggle) {
      var next = theme === "dark" ? "Switch to light theme" : "Switch to dark theme";
      toggle.setAttribute("aria-label", next);
      toggle.setAttribute("title", next);
    }
  }

  function initThemeToggle() {
    var toggle = document.getElementById("theme-toggle");
    if (!toggle) return;

    toggle.addEventListener("click", function (e) {
      e.preventDefault();
      applyTheme(currentTheme() === "dark" ? "light" : "dark");
    });

    var stored = null;
    try {
      stored = localStorage.getItem("dhund-landing-theme");
    } catch (e) {}
    if (stored === "light" || stored === "dark") {
      applyTheme(stored);
    } else {
      var resolved = currentTheme();
      root.style.colorScheme = resolved;
      var label = resolved === "dark" ? "Switch to light theme" : "Switch to dark theme";
      toggle.setAttribute("aria-label", label);
      toggle.setAttribute("title", label);
    }
  }

  function observeIn(nodes, className, options) {
    var reduce =
      window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) {
      nodes.forEach(function (el) {
        el.classList.add(className || "in");
      });
      return;
    }
    if (!("IntersectionObserver" in window) || !nodes.length) {
      nodes.forEach(function (el) {
        el.classList.add(className || "in");
      });
      return;
    }
    var io = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (e) {
          if (e.isIntersecting) {
            e.target.classList.add(className || "in");
            io.unobserve(e.target);
          }
        });
      },
      options || { threshold: 0.12, rootMargin: "0px 0px -32px 0px" }
    );
    nodes.forEach(function (el) {
      io.observe(el);
    });
  }

  function initReveal() {
    var reduce =
      window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) root.classList.add("reduce-motion");
    else document.body.classList.add("js-animate");

    observeIn(Array.prototype.slice.call(document.querySelectorAll(".reveal")));
    observeIn(Array.prototype.slice.call(document.querySelectorAll(".hero-fade")), "in", {
      threshold: 0.01,
      rootMargin: "0px",
    });
    observeIn(Array.prototype.slice.call(document.querySelectorAll(".product-frame.enter")), "in", {
      threshold: 0.15,
      rootMargin: "0px 0px -40px 0px",
    });
  }

  function initPipelineBeam() {
    var track = document.getElementById("pipeline-track");
    if (!track) return;
    var steps = Array.prototype.slice.call(track.querySelectorAll("[data-pipeline-step]"));
    var reduce =
      window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    if (reduce || !("IntersectionObserver" in window)) {
      track.classList.add("is-lit");
      track.style.setProperty("--beam", "100%");
      steps.forEach(function (s) {
        s.classList.add("in");
      });
      return;
    }

    var lit = 0;
    var io = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (e) {
          if (!e.isIntersecting) return;
          var idx = steps.indexOf(e.target);
          if (idx < 0) return;
          e.target.classList.add("in");
          lit = Math.max(lit, idx + 1);
          var pct = Math.round((lit / steps.length) * 100);
          track.classList.add("is-lit");
          track.style.setProperty("--beam", pct + "%");
          io.unobserve(e.target);
        });
      },
      { threshold: 0.55 }
    );
    steps.forEach(function (s) {
      io.observe(s);
    });
  }

  function initRouterCascade() {
    var well = document.getElementById("router-well");
    if (!well) return;
    var steps = Array.prototype.slice.call(well.querySelectorAll("[data-router-step]"));
    var reduce =
      window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    if (reduce || !("IntersectionObserver" in window)) {
      steps.forEach(function (s) {
        s.classList.add("in");
      });
      return;
    }

    var started = false;
    var io = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (e) {
          if (!e.isIntersecting || started) return;
          started = true;
          steps.forEach(function (step, i) {
            window.setTimeout(function () {
              step.classList.add("in");
            }, i * 120);
          });
          io.disconnect();
        });
      },
      { threshold: 0.35 }
    );
    io.observe(well);
  }

  function initMagicLink() {
    var form = document.getElementById("magic-form");
    if (!form) return;
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var btn = document.getElementById("magic-btn");
      var msg = document.getElementById("magic-msg");
      var emailInput = document.getElementById("magic-email");
      if (!btn || !msg || !emailInput) return;
      var email = emailInput.value.trim();
      btn.disabled = true;
      msg.style.display = "none";
      fetch("/auth/magic-link", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email }),
      })
        .then(function (res) {
          return res
            .json()
            .catch(function () {
              return {};
            })
            .then(function (data) {
              msg.style.display = "block";
              msg.style.color = res.ok ? "var(--ok)" : "var(--danger)";
              msg.textContent =
                data.detail ||
                (res.ok
                  ? "If that email is allowed, check your inbox for a sign-in link."
                  : "Could not send link. Try again.");
            });
        })
        .catch(function () {
          msg.style.display = "block";
          msg.style.color = "var(--danger)";
          msg.textContent = "Network error — try again.";
        })
        .finally(function () {
          btn.disabled = false;
        });
    });
  }

  function initTopbarScroll() {
    var bar = document.querySelector(".topbar");
    if (!bar) return;
    function update() {
      bar.classList.toggle("is-scrolled", window.scrollY > 8);
    }
    update();
    window.addEventListener("scroll", update, { passive: true });
  }

  function boot() {
    document.documentElement.classList.remove("no-js");
    initThemeToggle();
    initReveal();
    initPipelineBeam();
    initRouterCascade();
    initTopbarScroll();
    initMagicLink();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
