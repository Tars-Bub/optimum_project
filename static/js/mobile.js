/* Optimum - small mobile helpers. Loaded with "defer" at the end of base.html.
   1) menu button + backdrop for the slide-in sidebar
   2) puts column names on table cells so tables can stack on phones
   3) "View cart" shortcut on the Sales screen
   It only adds things; it does not change any form, link or existing script. */
(function () {
  'use strict';
  var body = document.body;

  /* ---- 1. Drawer ---- */
  var sidebar = document.querySelector('.sidebar');
  var topbar = document.querySelector('.topbar');
  if (sidebar && topbar) {
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'menu-btn';
    btn.setAttribute('aria-label', 'Open menu');
    btn.setAttribute('aria-expanded', 'false');
    btn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h16"/></svg>';
    topbar.insertBefore(btn, topbar.firstChild);

    var backdrop = document.createElement('div');
    backdrop.className = 'nav-backdrop';
    body.appendChild(backdrop);

    var setOpen = function (open) {
      body.classList.toggle('nav-open', open);
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
      btn.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
    };
    btn.addEventListener('click', function () { setOpen(!body.classList.contains('nav-open')); });
    backdrop.addEventListener('click', function () { setOpen(false); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') setOpen(false); });
    sidebar.addEventListener('click', function (e) { if (e.target.closest('a')) setOpen(false); });
    window.addEventListener('resize', function () { if (window.innerWidth > 900) setOpen(false); });
    window.addEventListener('pageshow', function () { setOpen(false); });   /* back button */
  }

  /* ---- 2. Stackable tables ---- */
  var tables = document.querySelectorAll('main table, .content table');
  Array.prototype.forEach.call(tables, function (table) {
    if (table.closest('.preform, .slot')) return;          /* keep the form preview as it is */
    var rows = Array.prototype.slice.call(table.rows);
    if (!rows.length) return;

    var first = rows[0];
    var hasHead = first.cells.length > 0 && Array.prototype.every.call(first.cells, function (c) { return c.tagName === 'TH'; });
    if (!hasHead) return;

    var labels = Array.prototype.map.call(first.cells, function (c) { return c.textContent.trim(); });
    table.classList.add('rt');
    first.classList.add('rt-head');

    rows.slice(1).forEach(function (row) {
      Array.prototype.forEach.call(row.cells, function (cell, i) {
        if (cell.colSpan > 1) { cell.classList.add('rt-span'); }
        else if (labels[i]) { cell.setAttribute('data-label', labels[i]); }
        else { cell.classList.add('rt-nolabel'); }

        /* wrap the cell's content so it lays out as one block next to its label */
        var wrap = document.createElement('span');
        wrap.className = 'cell';
        while (cell.firstChild) wrap.appendChild(cell.firstChild);
        cell.appendChild(wrap);
      });
    });
  });

  /* ---- 3. Sales: jump-to-cart button ---- */
  var cart = document.querySelector('.cart');
  if (cart) {
    var lines = cart.querySelectorAll('.line').length;
    if (lines) {
      cart.id = cart.id || 'cart';
      var totalEl = cart.querySelector('.total span:last-child');
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
})();
