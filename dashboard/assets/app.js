(function () {
  "use strict";

  var DATA = JSON.parse(document.getElementById("pw-data").textContent);
  var BY_REF = {};
  DATA.people.forEach(function (p) { BY_REF[p.ref] = p; });

  function $(s, root) { return (root || document).querySelector(s); }
  function $$(s, root) { return Array.prototype.slice.call((root || document).querySelectorAll(s)); }

  /* ---------- 路由 ---------- */
  function currentRef() {
    var h = location.hash;
    if (h.indexOf("#/p/") === 0) return decodeURIComponent(h.slice(4));
    return null;
  }

  function route() {
    var ref = currentRef();
    var list = $("#view-list"), detail = $("#view-detail");
    if (ref && BY_REF[ref]) {
      list.hidden = true;
      detail.hidden = false;
      $$(".person-detail", detail).forEach(function (d) {
        d.hidden = d.dataset.ref !== ref;
      });
      renderCharts(ref);
      window.scrollTo(0, 0);
    } else {
      detail.hidden = true;
      list.hidden = false;
    }
  }

  window.addEventListener("hashchange", route);
  $$(".back-btn").forEach(function (b) {
    b.addEventListener("click", function () {
      history.pushState(null, "", location.pathname);
      route();
    });
  });

  /* ---------- 列表：排序 / 搜索 / 筛选 ---------- */
  var cards = $$("#cards .card");
  var box = $("#cards");

  function orderCards() {
    var by = $("#sort").value;
    var arr = cards.slice();
    arr.sort(function (a, b) {
      if (by === "count") return (+b.dataset.count) - (+a.dataset.count);
      if (by === "name") return a.dataset.name.localeCompare(b.dataset.name, "zh");
      return b.dataset.last.localeCompare(a.dataset.last);
    });
    arr.forEach(function (c) { box.appendChild(c); });
  }

  function filterCards() {
    var q = $("#search").value.trim().toLowerCase();
    var rel = $("#relFilter").value;
    cards.forEach(function (c) {
      var ok = true;
      if (rel && c.dataset.relation !== rel) ok = false;
      if (ok && q) {
        var hay = (c.dataset.name + " " + c.dataset.relation + " " + c.dataset.tags).toLowerCase();
        if (hay.indexOf(q) < 0) ok = false;
      }
      c.style.display = ok ? "" : "none";
    });
  }

  $("#search").addEventListener("input", filterCards);
  $("#sort").addEventListener("change", orderCards);
  $("#relFilter").addEventListener("change", filterCards);

  var rels = {};
  cards.forEach(function (c) { if (c.dataset.relation) rels[c.dataset.relation] = 1; });
  Object.keys(rels).sort().forEach(function (r) {
    var op = document.createElement("option");
    op.value = r; op.textContent = r;
    $("#relFilter").appendChild(op);
  });

  /* ---------- 卡片迷你雷达 ---------- */
  function miniRadar(el) {
    var vals = el.dataset.big5.split(",").map(Number);
    var chart = echarts.init(el);
    chart.setOption({
      radar: {
        indicator: DATA.labels.map(function (n) { return { name: n, max: 5 }; }),
        radius: "65%", splitNumber: 2,
        axisName: { color: "#94a3b8", fontSize: 9 },
        splitLine: { lineStyle: { color: "#334155", opacity: .3 } },
        splitArea: { show: false },
        axisLine: { lineStyle: { color: "#334155", opacity: .3 } }
      },
      series: [{
        type: "radar",
        data: [{ value: vals, areaStyle: { opacity: .25 }, itemStyle: { color: "#3b6cf6" } }],
        symbolSize: 2
      }]
    });
    el.addEventListener("mouseenter", function () { chart.resize({ height: 200, width: 260 }); });
    el.addEventListener("mouseleave", function () { chart.resize({ height: 86 }); });
    window.addEventListener("resize", function () { chart.resize(); });
  }
  $$(".mini-radar").forEach(miniRadar);

  /* ---------- 详情图表 ---------- */
  var chartCache = {};

  function renderCharts(ref) {
    var p = BY_REF[ref];
    if (!p) return;

    if (p.big5) {
      var radarEl = $("#radar-" + ref);
      if (radarEl) {
        if (chartCache[ref + "-radar"]) { chartCache[ref + "-radar"].dispose(); delete chartCache[ref + "-radar"]; }
        var c1 = echarts.init(radarEl);
        c1.setOption({
          radar: {
            indicator: DATA.labels.map(function (n) { return { name: n, max: 5 }; }),
            radius: "62%", splitNumber: 4,
            axisName: { color: "#94a3b8" }
          },
          series: [{
            type: "radar",
            data: [{
              value: DATA.labels.map(function (l) { return p.big5[l]; }),
              areaStyle: { opacity: .3 }, itemStyle: { color: "#3b6cf6" }
            }]
          }]
        });
        chartCache[ref + "-radar"] = c1;
      }
    }

    var lineEl = $("#line-" + ref);
    if (lineEl) {
      if (chartCache[ref + "-line"]) { chartCache[ref + "-line"].dispose(); delete chartCache[ref + "-line"]; }
      var series = p.memories.map(function (m) {
        return { date: m.date, val: DATA.emotions.sentiment[m.emotion] || 3, e: m.emotion };
      });
      var c2 = echarts.init(lineEl);
      c2.setOption({
        tooltip: { trigger: "axis", formatter: function (ps) {
          var p0 = ps[0];
          return p0.name + " · " + p0.value + " 分（" + p0.data.e + "）";
        } },
        grid: { left: 34, right: 12, top: 18, bottom: 26 },
        xAxis: { type: "category", data: series.map(function (s) { return s.date; }),
          axisLabel: { fontSize: 10 } },
        yAxis: { type: "value", min: 0.5, max: 5.5, interval: 1 },
        series: [{
          type: "line", data: series, smooth: true,
          lineStyle: { width: 2, color: "#3b6cf6" },
          itemStyle: { color: "#3b6cf6" },
          symbolSize: 7
        }]
      });
      chartCache[ref + "-line"] = c2;
    }
  }

  /* ---------- 主题 ---------- */
  var btn = $("#themeBtn");
  function applyTheme(dark) {
    document.documentElement.classList.toggle("dark", dark);
    btn.textContent = dark ? "亮色" : "暗色";
    try { localStorage.setItem("pw-theme", dark ? "dark" : "light"); } catch (e) {}
    var ref = currentRef();
    if (ref) renderCharts(ref);
  }
  var saved = null;
  try { saved = localStorage.getItem("pw-theme"); } catch (e) {}
  applyTheme(saved === "dark");
  btn.addEventListener("click", function () {
    applyTheme(!document.documentElement.classList.contains("dark"));
  });

  window.addEventListener("resize", function () {
    Object.keys(chartCache).forEach(function (k) { chartCache[k].resize(); });
  });

  route();
})();