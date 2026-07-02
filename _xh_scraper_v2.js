(async function() {
  'use strict';

  // ════════════════════════════════════════════════════════════
  //  Xiaohongshu / RedNote profile URL scraper v2
  //  Strategy: direct API call + fetch/XHR intercept + DOM fallback
  //  Paste this ENTIRE script into the browser console (F12)
  //  on the RedNote profile page (e.g. rednote.com/user/profile/...)
  // ════════════════════════════════════════════════════════════

  // ── Floating panel ──
  var panel = document.createElement('div');
  panel.id = '__xhs2';
  panel.innerHTML = '<div style="position:fixed;bottom:20px;right:20px;z-index:99999;background:#1a1a2e;color:#fff;padding:16px 20px;border-radius:12px;font:14px/1.4 monospace;box-shadow:0 4px 24px rgba(0,0,0,.5);min-width:340px;max-width:420px;border:1px solid #ff2442;max-height:90vh;overflow-y:auto;">' +
    '<div style="font-weight:700;color:#ff2442;margin-bottom:8px;font-size:15px;">RedNote Scraper v2 <span style="color:#888;font-weight:400;font-size:12px;">(direct API)</span></div>' +
    '<div style="margin:8px 0;"><span id="_xhs2c" style="font-size:20px;font-weight:700;">0</span> <span style="color:#aaa;">posts with token</span></div>' +
    '<div id="_xhs2s" style="color:#aaa;font-size:12px;margin-bottom:6px;">Starting...</div>' +
    '<div style="display:flex;gap:6px;flex-wrap:wrap;">' +
    '<button id="_xhs2_stop" style="flex:1;padding:6px 0;border:1px solid #ff2442;background:transparent;color:#ff2442;border-radius:6px;cursor:pointer;font:inherit;min-width:70px;">Stop & Save</button>' +
    '<button id="_xhs2_fetch" style="flex:1;padding:6px 0;border:1px solid #4ade80;background:transparent;color:#4ade80;border-radius:6px;cursor:pointer;font:inherit;min-width:70px;">Fetch API Now</button>' +
    '<button id="_xhs2_copy" style="padding:6px 10px;border:1px solid #555;background:transparent;color:#aaa;border-radius:6px;cursor:pointer;font:inherit;">Copy</button>' +
    '</div>' +
    '<div id="_xhs2_log" style="margin-top:6px;font-size:11px;color:#666;max-height:150px;overflow-y:auto;border-top:1px solid #333;padding-top:4px;"></div>' +
    '</div>';
  document.body.appendChild(panel);

  var $ = function(id) { return document.getElementById(id); };
  var logDiv = $('_xhs2_log');
  var logFn = function(msg) {
    if (!logDiv) return;
    var d = document.createElement('div');
    d.textContent = msg;
    logDiv.appendChild(d);
    logDiv.scrollTop = logDiv.scrollHeight;
  };
  var updateCount = function() {
    var el = $('_xhs2c');
    if (el) el.textContent = posts.size;
  };
  var statusFn = function(msg) {
    var el = $('_xhs2s');
    if (el) el.textContent = msg;
  };

  // ── State ──
  var BASE = 'https://www.rednote.com';
  var posts = new Map();           // noteId -> full URL with xsec_token
  var seenApiIds = new Set();      // dedup for API responses
  var user_id = null;
  var stopped = false;
  var finished = false;

  // ── Extract note data from API response ──
  function extractNotes(data) {
    if (!data || !data.data) return 0;
    var notes = null;
    if (Array.isArray(data.data.notes)) notes = data.data.notes;
    else if (Array.isArray(data.data.items)) notes = data.data.items;
    if (!notes) return 0;
    var count = 0;
    for (var i = 0; i < notes.length; i++) {
      var note = notes[i];
      var nid = note.note_id || note.id || '';
      var token = note.xsec_token || '';
      if (!nid || seenApiIds.has(nid)) continue;
      seenApiIds.add(nid);
      if (token) {
        posts.set(nid, BASE + '/explore/' + nid + '?xsec_token=' + token + '&xsec_source=pc_user');
      } else {
        // Store ID-only as placeholder (no token)
        posts.set(nid, '');
      }
      count++;
    }
    return count;
  }

  // ── Patch fetch to intercept API responses ──
  var origFetch = window.fetch.bind(window);
  window.fetch = function(u, opts) {
    var result = origFetch(u, opts);
    var url = (typeof u === 'string' ? u : (u && u.url ? u.url : '')) || '';
    if (url.indexOf('user_posted') !== -1 || url.indexOf('sns/web/v1') !== -1) {
      result.then(function(resp) {
        try {
          var cloned = resp.clone();
          cloned.text().then(function(text) {
            try {
              var data = JSON.parse(text);
              var n = extractNotes(data);
              if (n > 0) {
                updateCount();
                logFn('  INTERCEPT fetch: +' + n + ' notes -> ' + posts.size + ' total');
              }
            } catch(e) {}
          }).catch(function(){});
        } catch(e) {}
      });
    }
    return result;
  };
  logFn('  fetch() patched');

  // ── Patch XHR to intercept API responses ──
  var origOpen = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function(method, url) {
    if (typeof url === 'string' && (url.indexOf('user_posted') !== -1 || url.indexOf('sns/web/v1') !== -1)) {
      var xhr = this;
      var origOnLoad = xhr.onload;
      xhr.addEventListener('load', function() {
        try {
          var data = JSON.parse(xhr.responseText);
          var n = extractNotes(data);
          if (n > 0) {
            updateCount();
            logFn('  INTERCEPT XHR: +' + n + ' notes -> ' + posts.size + ' total');
          }
        } catch(e) {}
      });
    }
    return origOpen.apply(this, arguments);
  };
  logFn('  XHR patched');

  // ── Direct API call ──
  function getUserIdFromState() {
    // Try to extract user_id from __INITIAL_STATE__
    try {
      if (window.__INITIAL_STATE__ && window.__INITIAL_STATE__.user) {
        var u = window.__INITIAL_STATE__.user;
        return u.user_id || u.userId || u.id || '';
      }
    } catch(e) {}
    // Try to extract from URL
    var m = window.location.pathname.match(/\/user\/profile\/([a-f0-9]+)/);
    if (m) return m[1];
    return '';
  }

  async function callUserPostedAPI(cursor) {
    var uid = getUserIdFromState();
    if (!uid) {
      logFn('  FAIL: could not find user_id in page state');
      return 0;
    }
    var body = JSON.stringify({
      user_id: uid,
      cursor: cursor || '',
      num: 30
    });
    logFn('  Calling API for user_id=' + uid + ' cursor=' + (cursor || 'initial'));
    statusFn('Calling API...');
    try {
      var resp = await fetch('https://webapi.rednote.com/api/sns/web/v1/user_posted', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json;charset=UTF-8',
          'Origin': 'https://www.rednote.com',
          'Referer': 'https://www.rednote.com/',
          'Accept': 'application/json, text/plain, */*'
        },
        body: body
      });
      var text = await resp.text();
      logFn('  API status: ' + resp.status + ' (' + text.length + ' bytes)');
      if (text.length > 10) {
        var data = JSON.parse(text);
        if (data.success === false || data.code === 300017) {
          logFn('  API blocked (code=' + data.code + ') — needs X-S/X-T headers');
          logFn('  Trying without headers (cookies only)...');
          // Try a different approach
          return 'BLOCKED';
        }
        var n = extractNotes(data);
        if (n > 0) {
          updateCount();
          logFn('  DIRECT API: +' + n + ' notes!');
          // Check if pagination cursor is available
          var nextCursor = null;
          try { nextCursor = data.data.cursor || data.data.next_cursor; } catch(e) {}
          return nextCursor ? n : 'DONE:' + n;
        } else {
          logFn('  API returned 0 notes — unexpected response format');
          logFn('  Response preview: ' + text.slice(0, 200));
          return 'NO_NOTES';
        }
      }
      return 'EMPTY:' + text;
    } catch(e) {
      logFn('  API call error: ' + e.message);
      return 'ERROR';
    }
  }

  // ── Extract from __INITIAL_STATE__ (SSR — may lack xsec_token) ──
  function extractFromInitialState() {
    try {
      if (!window.__INITIAL_STATE__) return 0;
      var s = window.__INITIAL_STATE__;
      var notes = [];
      // Navigate the state tree
      try {
        var pages = s.user && s.user.notes;
        if (Array.isArray(pages)) {
          for (var p = 0; p < pages.length; p++) {
            if (Array.isArray(pages[p])) {
              for (var ni = 0; ni < pages[p].length; ni++) {
                notes.push(pages[p][ni]);
              }
            }
          }
        }
      } catch(e) {}
      if (notes.length === 0) {
        // Deep search
        function deepSearch(obj, depth) {
          if (depth > 4 || !obj) return [];
          var found = [];
          if (Array.isArray(obj)) {
            for (var i = 0; i < obj.length; i++) {
              found = found.concat(deepSearch(obj[i], depth + 1));
            }
          } else if (typeof obj === 'object') {
            if (obj.noteCard && obj.xsecToken !== undefined) found.push(obj);
            for (var k in obj) {
              found = found.concat(deepSearch(obj[k], depth + 1));
            }
          }
          return found;
        }
        notes = deepSearch(s, 0);
      }
      var count = 0;
      for (var i = 0; i < notes.length; i++) {
        var item = notes[i];
        var nc = item.noteCard || item;
        var nid = nc.noteId || item.id || '';
        var token = nc.xsecToken || item.xsecToken || '';
        if (nid && !seenApiIds.has(nid)) {
          seenApiIds.add(nid);
          if (token) {
            posts.set(nid, BASE + '/explore/' + nid + '?xsec_token=' + token + '&xsec_source=pc_user');
            count++;
          } else if (nid) {
            posts.set(nid, '');  // placeholder
          }
        }
      }
      return count;
    } catch(e) {
      return 0;
    }
  }

  // ── Collect from DOM (fallback, no token) ──
  function collectDOM() {
    var added = 0;
    var links = document.querySelectorAll('a[href*="/explore/"]');
    for (var i = 0; i < links.length; i++) {
      var href = links[i].getAttribute('href') || '';
      if (href.indexOf('/explore/') === -1) continue;
      var m = href.match(/\/explore\/([a-f0-9]+)/);
      if (!m) continue;
      var nid = m[1];
      if (nid && !posts.has(nid)) {
        // Check if href already has xsec_token
        if (href.indexOf('xsec_token=') !== -1) {
          var fullUrl = href.indexOf('://') !== -1 ? href : BASE + href;
          posts.set(nid, fullUrl);
        } else {
          posts.set(nid, '');  // placeholder
        }
        added++;
      }
    }
    return added;
  }

  // ── Start: try to get data ──
  logFn('Initializing...');

  // Step 1: Extract from __INITIAL_STATE__
  var fromState = extractFromInitialState();
  if (fromState > 0) {
    logFn('  From __INITIAL_STATE__: ' + fromState + ' notes (token=' +
      (posts.size > 0 ? 'YES' : 'NO') + ')');
  } else {
    logFn('  __INITIAL_STATE__: no notes found');
  }

  // Step 2: Collect DOM links
  var fromDOM = collectDOM();
  logFn('  From DOM: ' + fromDOM + ' links');

  // Step 3: Try direct API call
  statusFn('Calling API...');
  var apiResult = await callUserPostedAPI();
  if (apiResult === 'BLOCKED') {
    logFn('  Direct API blocked by X-S/X-T headers');
    logFn('  Switching to scroll-triggered intercept...');
  }

  // Step 4: Set up MutationObserver for DOM changes
  var obs = new MutationObserver(function() {
    var n = collectDOM();
    if (n > 0) updateCount();
  });
  obs.observe(document.body, { childList: true, subtree: true });

  updateCount();
  statusFn(posts.size > 0 ? posts.size + ' posts — scrolling...' : 'Scrolling to trigger API...');

  // ── Button handlers ──
  $('_xhs2_stop').onclick = function() {
    stopped = true;
    if (!finished) finish();
  };
  $('_xhs2_fetch').onclick = function() {
    statusFn('Manual API fetch...');
    callUserPostedAPI().then(function(r) {
      updateCount();
      statusFn('API done: ' + posts.size + ' posts');
      logFn('Manual fetch result: ' + JSON.stringify(r));
    });
  };
  $('_xhs2_copy').onclick = function() {
    var urls = [];
    posts.forEach(function(v) { if (v) urls.push(v); });
    urls.sort();
    navigator.clipboard.writeText(urls.join('\n')).then(function() {
      statusFn('Copied ' + urls.length + ' URLs!');
    });
  };

  // ── Scrolling ──
  async function scrollPass(label) {
    statusFn(label + '...');
    var empty = 0;
    for (var i = 0; i < 300 && !stopped; i++) {
      window.scrollBy(0, window.innerHeight * 1.5);
      await new Promise(function(r) { setTimeout(r, 800 + Math.random() * 700); });
      var before = posts.size;
      collectDOM();
      if (posts.size === before) {
        empty++;
        if (empty >= 8) {
          statusFn(label + ' harder...');
          window.scrollBy(0, window.innerHeight * 3);
          await new Promise(function(r) { setTimeout(r, 3000); });
          var b2 = posts.size;
          collectDOM();
          window.scrollBy(0, -window.innerHeight * 2);
          await new Promise(function(r) { setTimeout(r, 1500); });
          window.scrollBy(0, window.innerHeight * 3);
          await new Promise(function(r) { setTimeout(r, 3000); });
          collectDOM();
          if (posts.size === b2) {
            logFn(label + ' — no more posts at scroll ' + i);
            break;
          }
          empty = 3;
        }
      } else {
        empty = Math.max(0, empty - 1);
      }
      if (i % 20 === 0) {
        statusFn(label + ' scroll ' + i + ', ' + posts.size + ' posts');
      }
    }
  }

  await scrollPass('Pass 1/3');

  if (!stopped) {
    // Try API call again after scrolling (page may have loaded more state)
    var r2 = await callUserPostedAPI();
    if (typeof r2 === 'number' && r2 > 0) {
      logFn('  Post-scroll API returned ' + r2 + ' notes');
    }
  }

  if (!stopped && posts.size > 0) {
    window.scrollTo(0, 0);
    await new Promise(function(r) { setTimeout(r, 3000); });
    await scrollPass('Pass 2/3');
  }

  if (!stopped) {
    window.scrollTo(0, 0);
    await new Promise(function(r) { setTimeout(r, 3000); });
    await scrollPass('Pass 3/3');
  }

  statusFn('Done — ' + posts.size + ' posts');
  if (!finished) await finish();

  async function finish() {
    if (finished) return;
    finished = true;
    stopped = true;
    obs.disconnect();

    // Collect URLs that have xsec_token
    var validUrls = [];
    var missingToken = 0;
    posts.forEach(function(v, k) {
      if (v) { validUrls.push(v); }
      else { missingToken++; }
    });
    validUrls.sort();

    var msg = validUrls.length + ' URLs with token';
    if (missingToken > 0) msg += ' (' + missingToken + ' missing token — not saved)';
    statusFn(msg);
    logFn('Finish: ' + msg);

    // Get channel name
    var name = 'xiaohongshu';
    var titleM = document.title.match(/@(\w+)/);
    if (titleM) name = titleM[1];
    else {
      var pathM = window.location.pathname.match(/\/user\/profile\/([a-f0-9]+)/);
      if (pathM) name = pathM[1].slice(0, 16);
    }

    var ts = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
    var blob = new Blob([validUrls.join('\n')], { type: 'text/plain' });
    var aEl = document.createElement('a');
    aEl.href = URL.createObjectURL(blob);
    aEl.download = name + '_xhs_videos_' + ts + '.txt';
    aEl.click();
    URL.revokeObjectURL(aEl.href);
    logFn('Downloaded: ' + aEl.download);
  }
})();
