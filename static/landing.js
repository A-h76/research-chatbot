/* Public landing page: theme toggle, motion, evidence demo, magic link. */
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

  function initReveal() {
    var reduce =
      window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) root.classList.add("reduce-motion");

    var nodes = document.querySelectorAll(".reveal");
    if (!reduce && "IntersectionObserver" in window && nodes.length) {
      document.body.classList.add("js-animate");
      var io = new IntersectionObserver(
        function (entries) {
          entries.forEach(function (e) {
            if (e.isIntersecting) e.target.classList.add("in");
          });
        },
        { threshold: 0.12, rootMargin: "0px 0px -32px 0px" }
      );
      nodes.forEach(function (el) {
        io.observe(el);
      });
    } else {
      nodes.forEach(function (el) {
        el.classList.add("in");
      });
    }
  }

  function initEvidenceDemo() {
    var left = document.getElementById("demo-left");
    var right = document.getElementById("demo-right");
    var hint = document.getElementById("demo-hint");
    var demo = document.getElementById("evidence-demo");
    if (!left || !right || !demo) return;

    var evidence = {
      a: {
        meta: "Accepted evidence · [3]",
        title: "Patel et al., 2021 — Hepatic clearance of lipid nanoparticles",
        html:
          "<mark>Kupffer cells accounted for the majority of nanoparticle sequestration</mark> within 30 minutes of intravenous administration in murine models…",
        foot: "PDF · page 7 · Methods · Support: strong",
      },
      b: {
        meta: "Accepted evidence · [9]",
        title: "Chen & Rivera, 2019 — PEGylation and RES evasion",
        html:
          "Surface PEGylation <mark>reduced Kupffer-mediated uptake by approximately 40%</mark> and extended plasma half-life relative to bare lipid particles…",
        foot: "PDF · page 12 · Results · Support: moderate",
      },
      c: {
        meta: "Accepted evidence · [14]",
        title: "Okada et al., 2020 — Species differences in hepatic scavenging",
        html:
          "Authors note <mark>inter-species variability in Kupffer density</mark> that may limit direct translation of murine clearance findings…",
        foot: "PDF · page 3 · Discussion · Conflict noted elsewhere",
      },
    };

    var activeKey = "a";

    function chipsHtml(active) {
      return ["a", "b", "c"]
        .map(function (k, i) {
          var n = [3, 9, 14][i];
          return (
            '<button type="button" class="chip' +
            (k === active ? " is-active" : "") +
            '" data-ev="' +
            k +
            '" aria-pressed="' +
            (k === active) +
            '">[' +
            n +
            "]</button>"
          );
        })
        .join("");
    }

    function renderInspect(key, showAccept) {
      var d = evidence[key] || evidence.a;
      right.innerHTML =
        '<p class="inspect-meta">' +
        d.meta +
        "</p>" +
        '<p class="inspect-title">' +
        d.title +
        "</p>" +
        '<div class="passage">' +
        d.html +
        "</div>" +
        '<p class="inspect-foot">' +
        d.foot +
        "</p>" +
        (showAccept
          ? '<div class="accept-pill">✓ Finding accepted into project evidence</div>'
          : "");
    }

    function bindChips() {
      left.querySelectorAll(".chip[data-ev]").forEach(function (chip) {
        chip.addEventListener("click", function () {
          activeKey = chip.getAttribute("data-ev") || "a";
          setStep(4);
        });
      });
    }

    function setStep(step) {
      demo.querySelectorAll(".story-step").forEach(function (btn) {
        var on = btn.getAttribute("data-step") === String(step);
        btn.classList.toggle("is-active", on);
        btn.setAttribute("aria-selected", on ? "true" : "false");
      });

      if (step === 1) {
        left.innerHTML =
          '<p class="chat-q"><strong>You ask</strong></p>' +
          '<p class="chat-a" style="font-family:var(--serif);font-size:1.08rem">How do Kupffer cells affect nanoparticle clearance in the liver?</p>';
        right.innerHTML =
          '<p class="inspect-meta">Waiting</p>' +
          '<p class="inspect-title">Pose a research question grounded in your library.</p>' +
          '<p class="inspect-foot">Next: Dhund answers with citations you can open.</p>';
        if (hint) hint.textContent = "Step 1 — the research question.";
      } else if (step === 2) {
        left.innerHTML =
          '<p class="chat-q"><strong>You asked</strong></p>' +
          '<p class="chat-a" style="font-family:var(--serif);font-size:1rem;margin-bottom:0.85rem">How do Kupffer cells affect nanoparticle clearance in the liver?</p>' +
          "<p class=\"chat-a\">Kupffer cells are the primary hepatic scavengers of circulating nanoparticles; surface PEGylation reduces uptake and prolongs circulation.</p>";
        right.innerHTML =
          '<p class="inspect-meta">Answer</p>' +
          '<p class="inspect-title">Grounded response — citations arrive next.</p>' +
          '<p class="inspect-foot">Claims stay provisional until you open the source.</p>';
        if (hint) hint.textContent = "Step 2 — an answer before you verify.";
      } else if (step === 3) {
        left.innerHTML =
          '<p class="chat-q"><strong>Answer with evidence chips</strong></p>' +
          "<p class=\"chat-a\">Kupffer cells are the primary hepatic scavengers of circulating nanoparticles; surface PEGylation reduces uptake and prolongs circulation " +
          chipsHtml(activeKey) +
          ".</p>";
        right.innerHTML =
          '<p class="inspect-meta">Citation chips</p>' +
          '<p class="inspect-title">Each chip maps to an evidence object in your project.</p>' +
          '<p class="inspect-foot">Click a chip — or continue to open the passage.</p>';
        if (hint) hint.textContent = "Step 3 — click a chip, or advance to the passage.";
        bindChips();
      } else if (step === 4) {
        left.innerHTML =
          '<p class="chat-q"><strong>Answer · inspectable</strong></p>' +
          "<p class=\"chat-a\">Kupffer cells are the primary hepatic scavengers of circulating nanoparticles; surface PEGylation reduces uptake and prolongs circulation " +
          chipsHtml(activeKey) +
          ".</p>";
        renderInspect(activeKey, false);
        if (hint) hint.textContent = "Step 4 — original PDF passage with highlight.";
        bindChips();
      } else {
        left.innerHTML =
          '<p class="chat-q"><strong>Reviewer</strong></p>' +
          '<p class="chat-a">Support is strong for hepatic scavenging. Accept this finding into the project evidence set used for writing.</p>' +
          '<p class="chat-a">' +
          chipsHtml(activeKey) +
          "</p>";
        renderInspect(activeKey, true);
        if (hint) hint.textContent = "Step 5 — accepted finding joins grounded writing.";
        bindChips();
      }
    }

    demo.querySelectorAll(".story-step").forEach(function (btn) {
      btn.addEventListener("click", function () {
        setStep(Number(btn.getAttribute("data-step")));
      });
    });

    setStep(1);
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
          return res.json().catch(function () {
            return {};
          }).then(function (data) {
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

  function boot() {
    initThemeToggle();
    initReveal();
    initEvidenceDemo();
    initMagicLink();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
