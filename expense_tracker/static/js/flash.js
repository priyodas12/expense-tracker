(function () {
  "use strict";

  var SUCCESS_DISMISS_MS = 4000;
  var FADE_MS = 400;

  function dismiss(flash) {
    flash.classList.add("flash-hide");
    setTimeout(function () {
      flash.remove();
    }, FADE_MS);
  }

  document.querySelectorAll(".flash").forEach(function (flash) {
    var close = document.createElement("button");
    close.type = "button";
    close.className = "flash-close";
    close.setAttribute("aria-label", "Dismiss message");
    close.textContent = "×";
    close.addEventListener("click", function () {
      dismiss(flash);
    });
    flash.appendChild(close);

    // Success messages go away on their own. Errors stay until closed.
    if (flash.classList.contains("flash-success")) {
      setTimeout(function () {
        dismiss(flash);
      }, SUCCESS_DISMISS_MS);
    }
  });
})();
