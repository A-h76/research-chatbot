/* Auth pages: sign-in, sign-up, forgot/reset password, magic link. */
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
  }

  function initTheme() {
    var toggle = document.getElementById("theme-toggle");
    var stored = null;
    try {
      stored = localStorage.getItem("dhund-landing-theme");
    } catch (e) {}
    if (stored === "light" || stored === "dark") applyTheme(stored);
    else applyTheme(currentTheme());
    if (toggle) {
      toggle.addEventListener("click", function () {
        applyTheme(currentTheme() === "dark" ? "light" : "dark");
      });
    }
  }

  function showMsg(el, text, ok) {
    if (!el) return;
    el.textContent = text || "";
    el.classList.add("show");
    el.classList.toggle("ok", !!ok);
    el.classList.toggle("error", !ok);
  }

  function postJson(url, body) {
    return fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify(body),
    }).then(function (res) {
      return res.json().catch(function () {
        return {};
      }).then(function (data) {
        return { res: res, data: data };
      });
    });
  }

  function passwordStrengthOk(pw) {
    return typeof pw === "string" && pw.length >= 10 && pw.length <= 200;
  }

  function initPasswordLogin() {
    var form = document.getElementById("password-login-form");
    if (!form) return;
    var btn = document.getElementById("password-login-btn");
    var msg = document.getElementById("auth-msg");
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var email = (document.getElementById("email") || {}).value || "";
      var password = (document.getElementById("password") || {}).value || "";
      if (!email || !password) {
        showMsg(msg, "Email and password are required.", false);
        return;
      }
      btn.disabled = true;
      postJson("/auth/password-login", { email: email.trim(), password: password })
        .then(function (r) {
          if (r.res.ok) {
            window.location.href = "/";
            return;
          }
          var err = r.data.error || "login_failed";
          var map = {
            invalid_credentials: "Incorrect email or password.",
            email_unverified: "Verify your email before signing in.",
            account_inactive: "This account is inactive.",
          };
          showMsg(msg, map[err] || "Could not sign in.", false);
        })
        .catch(function () {
          showMsg(msg, "Network error — try again.", false);
        })
        .finally(function () {
          btn.disabled = false;
        });
    });
  }

  function initSignUp() {
    var form = document.getElementById("sign-up-form");
    if (!form) return;
    var btn = document.getElementById("sign-up-btn");
    var msg = document.getElementById("auth-msg");
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var name = ((document.getElementById("name") || {}).value || "").trim();
      var email = ((document.getElementById("email") || {}).value || "").trim();
      var password = (document.getElementById("password") || {}).value || "";
      var confirm = (document.getElementById("confirm_password") || {}).value || "";
      if (!name || !email || !password) {
        showMsg(msg, "All fields are required.", false);
        return;
      }
      if (!passwordStrengthOk(password)) {
        showMsg(msg, "Password must be at least 10 characters.", false);
        return;
      }
      if (password !== confirm) {
        showMsg(msg, "Passwords do not match.", false);
        return;
      }
      btn.disabled = true;
      postJson("/auth/register", {
        name: name,
        email: email,
        password: password,
        confirm_password: confirm,
      })
        .then(function (r) {
          if (r.res.ok) {
            var redirect =
              (r.data && r.data.redirect) ||
              "/auth/verify-email?email=" + encodeURIComponent(email);
            window.location.href = redirect;
            return;
          }
          var err = r.data.error || "";
          var map = {
            email_taken: "An account with that email already exists.",
            not_invited: "This email is not allowed to sign up.",
            password_mismatch: "Passwords do not match.",
            invalid_input: "Check your details and try again.",
          };
          showMsg(msg, map[err] || r.data.detail || "Could not create account.", false);
        })
        .catch(function () {
          showMsg(msg, "Network error — try again.", false);
        })
        .finally(function () {
          btn.disabled = false;
        });
    });
  }

  function initForgot() {
    var form = document.getElementById("forgot-form");
    if (!form) return;
    var btn = document.getElementById("forgot-btn");
    var msg = document.getElementById("auth-msg");
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var email = ((document.getElementById("email") || {}).value || "").trim();
      btn.disabled = true;
      postJson("/auth/forgot-password", { email: email })
        .then(function (r) {
          showMsg(
            msg,
            (r.data && r.data.detail) || "If that account exists, a reset email was sent.",
            true
          );
        })
        .catch(function () {
          showMsg(msg, "Network error — try again.", false);
        })
        .finally(function () {
          btn.disabled = false;
        });
    });
  }

  function initReset() {
    var form = document.getElementById("reset-form");
    if (!form) return;
    var btn = document.getElementById("reset-btn");
    var msg = document.getElementById("auth-msg");
    var token = form.getAttribute("data-token") || "";
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var password = (document.getElementById("password") || {}).value || "";
      var confirm = (document.getElementById("confirm_password") || {}).value || "";
      if (!token) {
        showMsg(msg, "Missing reset token. Open the link from your email.", false);
        return;
      }
      if (!passwordStrengthOk(password)) {
        showMsg(msg, "Password must be at least 10 characters.", false);
        return;
      }
      if (password !== confirm) {
        showMsg(msg, "Passwords do not match.", false);
        return;
      }
      btn.disabled = true;
      postJson("/auth/reset-password", {
        token: token,
        password: password,
        confirm_password: confirm,
      })
        .then(function (r) {
          if (r.res.ok) {
            window.location.href = (r.data && r.data.redirect) || "/auth/password-updated";
            return;
          }
          showMsg(msg, "Could not reset password. The link may be expired.", false);
        })
        .catch(function () {
          showMsg(msg, "Network error — try again.", false);
        })
        .finally(function () {
          btn.disabled = false;
        });
    });
  }

  function initMagic() {
    var form = document.getElementById("magic-form");
    if (!form) return;
    var btn = document.getElementById("magic-btn");
    var msg = document.getElementById("magic-msg");
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var email = ((document.getElementById("magic-email") || {}).value || "").trim();
      if (!email) {
        showMsg(msg, "Enter an email for the magic link.", false);
        return;
      }
      btn.disabled = true;
      postJson("/auth/magic-link", { email: email })
        .then(function (r) {
          showMsg(
            msg,
            (r.data && r.data.detail) || "If that email can sign in, check your inbox.",
            !!r.res.ok
          );
        })
        .catch(function () {
          showMsg(msg, "Network error — try again.", false);
        })
        .finally(function () {
          btn.disabled = false;
        });
    });
  }

  function boot() {
    initTheme();
    initPasswordLogin();
    initSignUp();
    initForgot();
    initReset();
    initMagic();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
