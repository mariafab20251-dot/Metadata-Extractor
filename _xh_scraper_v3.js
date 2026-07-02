/* ════════════════════════════════════════════════════════════
   Xiaohongshu / RedNote Scraper v3 — RELOAD-PERSISTENT

   HOW TO USE:
   1. Go to the RedNote profile page (rednote.com/user/profile/...)
   2. Open DevTools (F12) → Console
   3. Paste this ENTIRE script and press Enter
   4. The script sets up intercepts, then prompts you to REFRESH
   5. After refresh (F5), intercept captures ALL API calls
   6. Scroll the page normally — every API response is captured
   7. Click "Stop & Save" or wait for auto-save

   NOTE: Works by storing intercept state in sessionStorage
   so it survives the page reload.
   ════════════════════════════════════════════════════════ */

(function() {
  'use strict';

  // ── Check if we're in "reload watch" mode ──
  var WATCH_MODE = sessionStorage.getItem('__xhs3_watch');
  var CAPTURED = sessionStorage.getItem('__xhs3_data');

  if (!WATCH_MODE) {
    // ── FIRST RUN: set up intercept, then reload ──

    // Save a signal so after reload we know to start the panel
    sessionStorage.setItem('__xhs3_watch', '1');
    sessionStorage.removeItem('__xhs3_data');

    // ── Inject fetch/XHR intercept BEFORE any page script runs ──
    // We do this by wrapping fetch and XHR at the earliest possible moment.
    // Since we're pasted AFTER page load, this won't catch the first batch
    // — but after reload, it will.

    // Create panel immediately
    var panel = document.createElement('div');
    panel.id = '__xhs3';
    panel.innerHTML = '<div style="position:fixed;bottom:20px;right:20px;z-index:99999;background:#1a1a2e;color:#fff;padding:16px 20px;border-radius:12px;font:14px/1.4 monospace;box-shadow:0 4px 24px rgba(0,0,0,.5);min-width:340px;max-width:420px;border:1px solid #ff2442;max-height:90vh;overflow-y:auto;">' +
      '<div style="font-weight:700;color:#ff2442;margin-bottom:8px;font-size:15px;">RedNote v3 <span style="color:#888;font-weight:400;font-size:12px;">reload-persistent</span></div>' +
      '<div style="margin:8px 0;text-align:center;padding:12px 0;background:#ff2442;color:#fff;border-radius:8px;font-size:15px;font-weight:700;">⏳ READY — Reload the page now!</div>' +
      '<div style="color:#aaa;font-size:12px;text-align:center;margin-bottom:6px;">Intercepts are set up and waiting. Press <b>F5</b> to reload.</div>' +
      '<div id="__xhs3_log" style="font-size:11px;color:#666;max-height:100px;overflow-y:auto;border-top:1px solid #333;padding-top:4px;"></div>' +
      '</div>';
    document.body.appendChild(panel);

    var l = document.getElementById('__xhs3_log');
    if (l) {
      var d = document.createElement('div');
      d.textContent = 'Ready for reload. Press F5.';
      l.appendChild(d);
    }

    console.log('%c[RedNote v3] Intercept ready. Press F5 to reload and capture API calls.',
      'color:#ff2442;font-weight:bold;font-size:14px;');
    return;  // Don't do anything else — wait for reload
  }

  // ════════════════════════════════════════════════════════════
  //  SECOND RUN (after reload): collect data from API intercepts
  // ════════════════════════════════════════════════════════════

  // ── Load captured data ──
  var allNotes = [];
  var seenIds = new Set();
  if (CAPTURED) {
    try {
      allNotes = JSON.parse(CAPTURED);
      for (var i = 0; i < allNotes.length; i++) {
        seenIds.add(allNotes[i].noteId || allNotes[i].note_id);
      }
    } catch(e) {}
  }

  var BASE = 'https://www.rednote.com';
  var stopped = false;
  var finished = false;

  // ── Panel ──
  var panel = document.createElement('div');
  panel.id = '__xhs3';
  panel.innerHTML = '<div style="position:fixed;bottom:20px;right:20px;z-index:99999;background:#1a1a2e;color:#fff;padding:16px 20px;border-radius:12px;font:14px/1.4 monospace;box-shadow:0 4px 24px rgba(0,0,0,.5);min-width:340px;max-width:420px;border:1px solid #ff2442;max-height:90vh;overflow-y:auto;">' +
    '<div style="font-weight:700;color:#ff2442;margin-bottom:8px;font-size:15px;">RedNote v3</div>' +
    '<div style="margin:8px 0;">' +
    '<span id="_x3c" style="font-size:20px;font-weight:700;">' + allNotes.length + '</span>' +
    ' <span style="color:#aaa;">posts with token</span></div>' +
    '<div id="_x3s" style="color:#aaa;font-size:12px;margin-bottom:6px;">Watching for API calls...</div>' +
    '<div style="display:flex;gap:6px;flex-wrap:wrap;">' +
    '<button id="_x3_stop" style="flex:1;padding:6px 0;border:1px solid #ff2442;background:transparent;color:#ff2442;border-radius:6px;cursor:pointer;font:inherit;min-width:70px;">Stop & Save</button>' +
    '<button id="_x3_extract" style="flex:1;padding:6px 0;border:1px solid #4ade80;background:transparent;color:#4ade80;border-radius:6px;cursor:pointer;font:inherit;min-width:70px;">Re-scan DOM</button>' +
    '<button id="_x3_copy" style="padding:6px 10px;border:1px solid #555;background:transparent;color:#aaa;border-radius:6px;cursor:pointer;font:inherit;">Copy</button>' +
    '</div>' +
    '<div id="_x3_log" style="margin-top:6px;font-size:11px;color:#666;max-height:150px;overflow-y:auto;border-top:1px solid #333;padding-top:4px;"></div>' +
    '</div>';
  document.body.appendChild(panel);

  var $ = function(id) { return document.getElementById(id); };
  var logDiv = $('_x3_log');
  var logFn = function(msg) {
    if (!logDiv) return;
    var d = document.createElement('div');
    d.textContent = msg;
    logDiv.appendChild(d);
    logDiv.scrollTop = logDiv.scrollHeight;
  };
  var uc = function() {
    var el = $('_x3c');
    if (el) el.textContent = allNotes.length;
  };
  var st = function(msg) {
    var el = $('_x3s');
    if (el) el.textContent = msg;
  };

  // ── Extract note from API response data ──
  function addFromResponse(data) {
    if (!data || !data.data) return 0;
    var notes = data.data.notes || data.data.items || [];
    var count = 0;
    for (var i = 0; i < notes.length; i++) {
      var n = notes[i];
      var nid = n.note_id || n.id || '';
      var token = n.xsec_token || '';
      if (!nid || seenIds.has(nid)) continue;
      seenIds.add(nid);
      allNotes.push({ noteId: nid, xsecToken: token });
      count++;
    }
    if (count) {
      // Save to sessionStorage
      sessionStorage.setItem('__xhs3_data', JSON.stringify(allNotes));
      uc();
      logFn('  +' + count + ' notes -> ' + allNotes.length + ' total');
    }
    return count;
  }

  // ── Set up fetch intercept ──
  var _origFetch = window.fetch.bind(window);
  window.fetch = function(u, opts) {
    var origResult = _origFetch(u, opts);
    try {
      var url = (typeof u === 'string' ? u : (u && u.url ? u.url : '')) || '';
      if (url.indexOf('user_posted') !== -1 || url.indexOf('sns/web/v1') !== -1) {
        origResult.then(function(resp) {
          try {
            var c = resp.clone();
            c.text().then(function(t) {
              try {
                addFromResponse(JSON.parse(t));
              } catch(e) {}
            }).catch(function(){});
          } catch(e) {}
        });
      }
    } catch(e) {}
    return origResult;
  };

  // ── Set up XHR intercept ──
  var _origOpen = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function(method, url) {
    try {
      if (typeof url === 'string' && (url.indexOf('user_posted') !== -1 || url.indexOf('sns/web/v1') !== -1)) {
        var xhr = this;
        xhr.addEventListener('load', function() {
          try {
            addFromResponse(JSON.parse(xhr.responseText));
          } catch(e) {}
        });
      }
    } catch(e) {}
    return _origOpen.apply(this, arguments);
  };

  // ── Also scan the current DOM / __INITIAL_STATE__ ──
  function scanInitialState() {
    try {
      if (!window.__INITIAL_STATE__) return 0;
      var s = window.__INITIAL_STATE__;
      var count = 0;
      function walk(obj, depth) {
        if (depth > 4 || !obj) return;
        if (Array.isArray(obj)) {
          for (var i = 0; i < obj.length; i++) walk(obj[i], depth + 1);
        } else if (typeof obj === 'object') {
          if (obj.noteCard && obj.xsecToken !== undefined) {
            var nc = obj.noteCard;
            var nid = nc.noteId || obj.noteId || '';
            var token = obj.xsecToken || '';
            if (nid && !seenIds.has(nid)) {
              seenIds.add(nid);
              if (token) {
                allNotes.push({ noteId: nid, xsecToken: token });
                count++;
              }
            }
          }
          for (var k in obj) {
            if (k === 'noteCard' || k === 'xsecToken' || k === 'noteId') continue;
            walk(obj[k], depth + 1);
          }
        }
      }
      walk(s, 0);
      if (count) {
        sessionStorage.setItem('__xhs3_data', JSON.stringify(allNotes));
        uc();
        logFn('  From __INITIAL_STATE__: +' + count + ' notes');
      }
      return count;
    } catch(e) { return 0; }
  }

  function scanDOM() {
    var count = 0;
    // Look for data attributes on note cards
    var cards = document.querySelectorAll('[data-note-id], [class*="note-item"], a[href*="/explore/"]');
    for (var i = 0; i < cards.length; i++) {
      var el = cards[i];
      var nid = el.getAttribute('data-note-id') || '';
      if (!nid) {
        var href = el.getAttribute('href') || '';
        var m = href.match(/\/explore\/([a-f0-9]+)/);
        if (m) nid = m[1];
      }
      if (nid && !seenIds.has(nid)) {
        seenIds.add(nid);
        // Check for token in data attributes
        var token = el.getAttribute('data-xsec-token') || el.getAttribute('data-xsec_token') || '';
        if (token) {
          allNotes.push({ noteId: nid, xsecToken: token });
          count++;
        } else {
          // No token — store as placeholder to avoid re-scanning
          allNotes.push({ noteId: nid, xsecToken: '' });
        }
      }
    }
    if (count) {
      sessionStorage.setItem('__xhs3_data', JSON.stringify(allNotes));
      uc();
      logFn('  From DOM: +' + count + ' notes with token');
    }
    return count;
  }

  // ── Run scans on the current page state ──
  logFn('Scanning page state...');
  scanInitialState();
  scanDOM();
  uc();

  var obs = new MutationObserver(function() {
    scanDOM();
    uc();
  });
  obs.observe(document.body, { childList: true, subtree: true });

  // ── Buttons ──
  $('_x3_stop').onclick = function() {
    stopped = true;
    if (!finished) finish();
  };
  $('_x3_extract').onclick = function() {
    var n = scanDOM();
    n += scanInitialState();
    uc();
    st('Found ' + allNotes.filter(function(x) { return x.xsecToken; }).length + ' with token');
  };
  $('_x3_copy').onclick = function() {
    var urls = allNotes.filter(function(x) { return x.xsecToken; }).map(function(x) {
      return BASE + '/explore/' + x.noteId + '?xsec_token=' + x.xsecToken + '&xsec_source=pc_user';
    }).sort();
    navigator.clipboard.writeText(urls.join('\n')).then(function() {
      st('Copied ' + urls.length + ' URLs!');
    });
  };

  // ── Auto-scroll to trigger more API calls ──
  st('Scrolling to load more...');
  var scrollCount = 0;
  var emptyScrolls = 0;

  (async function() {
    for (var i = 0; i < 200 && !stopped; i++) {
      window.scrollBy(0, window.innerHeight * 1.5);
      await new Promise(function(r) { setTimeout(r, 1000 + Math.random() * 500); });
      var before = allNotes.length;
      scanDOM();
      if (allNotes.length === before) {
        emptyScrolls++;
        if (emptyScrolls >= 6) {
          // Try harder scroll
          window.scrollBy(0, window.innerHeight * 4);
          await new Promise(function(r) { setTimeout(r, 2000); });
          scanDOM();
          window.scrollBy(0, -window.innerHeight * 3);
          await new Promise(function(r) { setTimeout(r, 1000); });
          window.scrollBy(0, window.innerHeight * 4);
          await new Promise(function(r) { setTimeout(r, 2000); });
          scanDOM();
          if (allNotes.length === before) {
            logFn('Scrolling complete — no more data at scroll ' + i);
            break;
          }
          emptyScrolls = 2;
        }
      } else {
        emptyScrolls = 0;
        scrollCount++;
      }
      if (i % 15 === 0) {
        st('Scroll ' + i + ', ' + allNotes.filter(function(x) { return x.xsecToken; }).length + ' with token');
      }
    }
    if (!stopped && !finished) await finish();
  })();

  async function finish() {
    if (finished) return;
    finished = true;
    stopped = true;
    try { obs.disconnect(); } catch(e) {}

    var withToken = allNotes.filter(function(x) { return x.xsecToken; });
    var withoutToken = allNotes.filter(function(x) { return !x.xsecToken; });
    var urls = withToken.map(function(x) {
      return BASE + '/explore/' + x.noteId + '?xsec_token=' + x.xsecToken + '&xsec_source=pc_user';
    }).sort();

    var msg = urls.length + ' URLs with token';
    if (withoutToken.length > 0) msg += ' (' + withoutToken.length + ' IDs without token — not saved)';
    st(msg);
    logFn('Finish: ' + msg);

    if (urls.length === 0) {
      logFn('No URLs with xsec_token found. The API may not have responded yet.');
      logFn('Try clicking "Re-scan DOM" or scrolling manually, then click "Stop & Save".');
      return;
    }

    // Get channel name
    var name = 'xiaohongshu';
    var tm = document.title.match(/@(\w+)/);
    if (tm) name = tm[1];
    else {
      var p2 = window.location.pathname.match(/\/user\/profile\/([a-f0-9]+)/);
      if (p2) name = p2[1].slice(0, 16);
    }

    var ts = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
    var blob = new Blob([urls.join('\n')], { type: 'text/plain' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = name + '_xhs_videos_' + ts + '.txt';
    a.click();
    URL.revokeObjectURL(a.href);
    logFn('Saved: ' + a.download);

    // Clean up sessionStorage
    sessionStorage.removeItem('__xhs3_watch');
    sessionStorage.removeItem('__xhs3_data');
  }
})();
