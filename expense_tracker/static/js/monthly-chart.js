(function () {
  "use strict";

  var REFRESH_MS = 5000;
  var MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

  var card = document.getElementById("monthly-chart");
  if (!card) {
    return;
  }

  var list = card.querySelector(".bars");
  var empty = card.querySelector(".chart-empty");
  var status = card.querySelector(".chart-status");
  var lastPayload = null;

  function formatMoney(cents) {
    return (cents / 100).toFixed(2);
  }

  // "2026-10" becomes "Oct", with the year added on January and on the first bar.
  function monthLabel(month, isFirst) {
    var year = month.slice(0, 4);
    var name = MONTH_NAMES[parseInt(month.slice(5, 7), 10) - 1];
    return month.slice(5, 7) === "01" || isFirst ? name + " " + year : name;
  }

  function render(payload) {
    var hasData = payload.total_cents > 0;
    list.classList.toggle("is-hidden", !hasData);
    empty.hidden = hasData;
    list.textContent = "";
    if (!hasData) {
      return;
    }

    var peak = Math.max.apply(null, payload.months.map(function (m) {
      return m.cents;
    }));

    payload.months.forEach(function (month, index) {
      var item = document.createElement("li");
      item.className = "bar-item";
      item.title = monthLabel(month.month, index === 0) + ": " + formatMoney(month.cents) +
        " (" + month.count + (month.count === 1 ? " expense)" : " expenses)");

      var value = document.createElement("span");
      value.className = "bar-value";
      value.textContent = month.cents > 0 ? formatMoney(month.cents) : "";

      var track = document.createElement("span");
      track.className = "bar-track";

      var bar = document.createElement("span");
      bar.className = "bar";
      bar.style.height = (month.cents / peak) * 100 + "%";
      track.appendChild(bar);

      var label = document.createElement("span");
      label.className = "bar-label";
      label.textContent = monthLabel(month.month, index === 0);

      item.appendChild(value);
      item.appendChild(track);
      item.appendChild(label);
      list.appendChild(item);
    });
  }

  function refresh() {
    // Polling is pointless while the tab is hidden; the visibility listener catches up.
    if (document.hidden) {
      return;
    }

    fetch(card.dataset.url + window.location.search, {
      headers: { Accept: "application/json" },
      credentials: "same-origin",
    })
      .then(function (response) {
        if (!response.ok) {
          throw new Error("HTTP " + response.status);
        }
        return response.json();
      })
      .then(function (payload) {
        status.textContent = "";
        var key = JSON.stringify(payload);
        if (key !== lastPayload) {
          lastPayload = key;
          render(payload);
        }
      })
      .catch(function () {
        status.textContent = "Chart could not refresh. Retrying...";
      });
  }

  document.addEventListener("visibilitychange", function () {
    if (!document.hidden) {
      refresh();
    }
  });

  refresh();
  setInterval(refresh, REFRESH_MS);
})();
