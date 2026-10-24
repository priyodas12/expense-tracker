(function () {
  "use strict";

  var REFRESH_MS = 5000;
  var SVG_NS = "http://www.w3.org/2000/svg";
  var CENTER = 100;
  var RADIUS = 90;
  var FULL_TURN = Math.PI * 2;

  var card = document.getElementById("category-chart");
  if (!card) {
    return;
  }

  var svg = card.querySelector(".pie");
  var legend = card.querySelector(".pie-legend");
  var empty = card.querySelector(".chart-empty");
  var status = card.querySelector(".chart-status");
  var lastPayload = null;

  function formatMoney(cents) {
    return (cents / 100).toFixed(2);
  }

  function sliceColour(slice) {
    return slice.slot === null ? "var(--series-other)" : "var(--series-" + (slice.slot + 1) + ")";
  }

  function sliceLabel(slice, total) {
    var share = Math.round((slice.cents / total) * 100);
    return slice.name + ": " + formatMoney(slice.cents) + " (" + share + "%)";
  }

  function point(angle) {
    return [CENTER + RADIUS * Math.cos(angle), CENTER + RADIUS * Math.sin(angle)];
  }

  function drawPie(slices, total) {
    svg.querySelectorAll("path, circle").forEach(function (node) {
      node.remove();
    });

    var start = -Math.PI / 2;
    slices.forEach(function (slice) {
      var sweep = (slice.cents / total) * FULL_TURN;
      var path = document.createElementNS(SVG_NS, "path");
      var title = document.createElementNS(SVG_NS, "title");
      title.textContent = sliceLabel(slice, total);
      path.appendChild(title);

      if (slices.length === 1) {
        // A single slice covers the whole circle, which an arc cannot draw.
        path = document.createElementNS(SVG_NS, "circle");
        path.setAttribute("cx", CENTER);
        path.setAttribute("cy", CENTER);
        path.setAttribute("r", RADIUS);
        path.appendChild(title);
      } else {
        var from = point(start);
        var to = point(start + sweep);
        var largeArc = sweep > Math.PI ? 1 : 0;
        path.setAttribute(
          "d",
          "M " + CENTER + " " + CENTER +
          " L " + from[0] + " " + from[1] +
          " A " + RADIUS + " " + RADIUS + " 0 " + largeArc + " 1 " + to[0] + " " + to[1] +
          " Z"
        );
      }

      // Surface-coloured outline leaves a 2px gap between neighbouring slices.
      path.style.fill = sliceColour(slice);
      path.style.stroke = "var(--chart-surface)";
      path.style.strokeWidth = "2";
      svg.appendChild(path);
      start += sweep;
    });
  }

  function drawLegend(slices, total) {
    legend.textContent = "";
    slices.forEach(function (slice) {
      var item = document.createElement("li");

      var swatch = document.createElement("span");
      swatch.className = "swatch";
      swatch.style.background = sliceColour(slice);

      var name = document.createElement("span");
      name.className = "name";
      name.textContent = slice.name;

      var value = document.createElement("span");
      value.className = "value";
      var share = Math.round((slice.cents / total) * 100);
      value.textContent = formatMoney(slice.cents) + " · " + share + "%";

      item.appendChild(swatch);
      item.appendChild(name);
      item.appendChild(value);
      legend.appendChild(item);
    });
  }

  function render(payload) {
    var hasData = payload.total_cents > 0 && payload.slices.length > 0;
    svg.classList.toggle("is-hidden", !hasData);
    legend.classList.toggle("is-hidden", !hasData);
    empty.hidden = hasData;
    if (!hasData) {
      legend.textContent = "";
      svg.querySelectorAll("path, circle").forEach(function (node) {
        node.remove();
      });
      return;
    }
    drawPie(payload.slices, payload.total_cents);
    drawLegend(payload.slices, payload.total_cents);
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
