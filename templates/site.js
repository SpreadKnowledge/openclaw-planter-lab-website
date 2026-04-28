(function () {
  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

  document.documentElement.classList.add("is-ready");

  if (reduceMotion.matches) {
    return;
  }

  document.addEventListener("click", function (event) {
    if (!(event.target instanceof Element)) {
      return;
    }

    var link = event.target.closest("a[href]");
    if (!link) {
      return;
    }

    var href = link.getAttribute("href");
    if (!href || href.startsWith("#") || link.target || link.hasAttribute("download")) {
      return;
    }

    var url = new URL(link.href, window.location.href);
    if (url.origin !== window.location.origin || (url.pathname === window.location.pathname && url.hash)) {
      return;
    }

    event.preventDefault();
    document.documentElement.classList.add("is-leaving");
    window.setTimeout(function () {
      window.location.href = url.href;
    }, 150);
  });
})();
