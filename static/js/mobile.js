/* Optimum - mobile helpers. Loaded with "defer" at the end of base.html.
   1) menu button, brand, close button + backdrop for the slide-in sidebar
   2) bottom navigation bar (built from the sidebar links, so it always matches the real menu)
   3) puts column names on table cells so tables can stack on phones
   4) "View cart" shortcut on the Sales screen, chart sizing
   It only adds things; it does not change any form, link or existing script. */
(function () {
  'use strict';
  var body = document.body;
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  /* ---- 1. Drawer ---- */
  var sidebar = $('.sidebar');
  var topbar = $('.topbar');
  var setOpen = function () {};
  if (sidebar && topbar) {
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'menu-btn';
    btn.setAttribute('aria-label', 'Open menu');
    btn.setAttribute('aria-expanded', 'false');
    btn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h16"/></svg>';
    topbar.insertBefore(btn, topbar.firstChild);

    /* small brand next to the menu button */
    var mark = $('.logo .mark', sidebar);
    if (mark) {
      var brand = document.createElement('a');
      brand.className = 'top-brand';
      brand.href = ($('.logo', sidebar) || {}).href || '/';
      brand.setAttribute('aria-label', 'Optimum home');
      brand.innerHTML = '<img src="' + mark.getAttribute('src') + '" alt="" width="30" height="30"><span>Optimum</span>';
      topbar.insertBefore(brand, btn.nextSibling);
    }

    var close = document.createElement('button');
    close.type = 'button';
    close.className = 'drawer-close';
    close.setAttribute('aria-label', 'Close menu');
    close.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>';
    sidebar.appendChild(close);

    var backdrop = document.createElement('div');
    backdrop.className = 'nav-backdrop';
    body.appendChild(backdrop);

    setOpen = function (open) {
      body.classList.toggle('nav-open', open);
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
      btn.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
    };
    btn.addEventListener('click', function () { setOpen(!body.classList.contains('nav-open')); });
    close.addEventListener('click', function () { setOpen(false); });
    backdrop.addEventListener('click', function () { setOpen(false); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') setOpen(false); });
    sidebar.addEventListener('click', function (e) { if (e.target.closest('a')) setOpen(false); });
    window.addEventListener('resize', function () { if (window.innerWidth > 900) setOpen(false); });
    window.addEventListener('pageshow', function () { setOpen(false); });   /* back button */

    /* swipe left on the open drawer to close it */
    var sx = null;
    sidebar.addEventListener('touchstart', function (e) { sx = e.touches[0].clientX; }, { passive: true });
    sidebar.addEventListener('touchend', function (e) {
      if (sx !== null && sx - e.changedTouches[0].clientX > 60) setOpen(false);
      sx = null;
    }, { passive: true });
  }

  /* ---- 2. Bottom navigation (Home / Sales / Stock / Reports / More) ---- */
  if (sidebar) {
    var links = $$('nav a', sidebar);
    var wanted = [
      { match: /dashboard/i, label: 'Home' },
      { match: /^sales/i, label: 'Sales' },
      { match: /^stock/i, label: 'Stock' },
      { match: /^reports/i, label: 'Reports' }
    ];
    var bar = document.createElement('nav');
    bar.className = 'bottom-nav';
    bar.setAttribute('aria-label', 'Main');
    wanted.forEach(function (w) {
      var src = links.filter(function (a) {
        var t = a.querySelector('span');
        return t && w.match.test(t.textContent.trim());
      })[0];
      if (!src) return;
      var a = document.createElement('a');
      a.href = src.getAttribute('href');
      if (src.classList.contains('active')) a.className = 'active';
      var icon = src.querySelector('svg');
      if (icon) a.appendChild(icon.cloneNode(true));
      var span = document.createElement('span');
      span.textContent = w.label;
      a.appendChild(span);
      var count = src.querySelector('.count');
      if (count) {
        var b = document.createElement('i');
        b.className = 'bn-badge';
        b.style.fontStyle = 'normal';
        b.textContent = count.textContent.trim();
        a.appendChild(b);
      }
      bar.appendChild(a);
    });
    var more = document.createElement('button');
    more.type = 'button';
    more.setAttribute('aria-label', 'More menu');
    more.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="5" cy="12" r="1.2"/><circle cx="12" cy="12" r="1.2"/><circle cx="19" cy="12" r="1.2"/></svg><span>More</span>';
    more.addEventListener('click', function () { setOpen(true); });
    /* highlight "More" when the current page is not one of the four shortcuts */
    var activeLink = links.filter(function (a) { return a.classList.contains('active'); })[0];
    if (activeLink && !$('.active', bar)) more.className = 'active';
    bar.appendChild(more);
    if (bar.children.length > 1) body.appendChild(bar);
  }

  /* ---- 3. Stackable tables ---- */
  $$('main table, .content table').forEach(function (table) {
    if (table.closest('.preform, .slot, .sheet')) return;          /* keep the form preview as it is */
    var rows = Array.prototype.slice.call(table.rows);
    if (!rows.length || table.classList.contains('rt')) return;

    var first = rows[0];
    var hasHead = first.cells.length > 0 && Array.prototype.every.call(first.cells, function (c) { return c.tagName === 'TH'; });
    if (!hasHead) return;

    var labels = Array.prototype.map.call(first.cells, function (c) { return c.textContent.trim(); });
    table.classList.add('rt');
    first.classList.add('rt-head');

    rows.slice(1).forEach(function (row) {
      var col = 0;
      Array.prototype.forEach.call(row.cells, function (cell) {
        if (cell.colSpan > 1) { cell.classList.add('rt-span'); }
        else if (labels[col]) { cell.setAttribute('data-label', labels[col]); }
        else { cell.classList.add('rt-nolabel'); }
        col += cell.colSpan || 1;

        /* wrap the cell's content so it lays out as one block next to its label */
        var wrap = document.createElement('span');
        wrap.className = 'cell';
        while (cell.firstChild) wrap.appendChild(cell.firstChild);
        cell.appendChild(wrap);
      });
    });
  });

  /* ---- 4a. Sales: jump-to-cart button ---- */
  var cart = $('.cart');
  if (cart) {
    var lines = cart.querySelectorAll('.line').length;
    if (lines) {
      cart.id = cart.id || 'cart';
      var totalEl = $('.sumrow.big span:last-child', cart);
      var fab = document.createElement('a');
      fab.className = 'cart-fab';
      fab.href = '#' + cart.id;
      fab.textContent = 'View cart (' + lines + ')' + (totalEl ? ' \u00b7 ' + totalEl.textContent.trim() : '');
      body.appendChild(fab);
      if ('IntersectionObserver' in window) {
        new IntersectionObserver(function (entries) {
          fab.classList.toggle('hide', entries[0].isIntersecting);
        }, { threshold: 0.15 }).observe(cart);
      }
    }
  }

  /* ---- 4b. Reports chart: give every bar room so labels never overlap ---- */
  var chart = $('.chart');
  if (chart) {
    var bars = chart.children.length;
    var box = chart.parentNode;
    box.style.setProperty('--bars', bars);
    $$('.chart, .chartlabels', box).forEach(function (el) { el.style.setProperty('--bars', bars); });
  }
})();
