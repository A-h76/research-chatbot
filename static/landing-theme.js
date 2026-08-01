/* Landing theme boot — runs in <head> to avoid flash. CSP-safe (external). */
(function () {
  try {
    var t = localStorage.getItem("dhund-landing-theme");
    if (t === "light" || t === "dark") {
      document.documentElement.setAttribute("data-theme", t);
    }
  } catch (e) {}
  document.documentElement.classList.remove("no-js");
  document.documentElement.classList.add("js");
})();
