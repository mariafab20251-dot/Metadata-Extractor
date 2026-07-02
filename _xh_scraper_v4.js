/* ════════════════════════════════════════════════════════════
   Xiaohongshu / RedNote Profile URL Scraper v4
   ──────────────────────────────────────────────────────────
   Strategy: Override JSON.parse to capture API response data
   at the JavaScript level (before it reaches the page's code).

   HOW TO USE:
   1. Go to the RedNote profile page (rednote.com/user/profile/...)
   2. Open DevTools (F12) → Console
   3. PASTE THIS EXACT TEXT and press Enter
   4. You'll see "⏳ Set up intercept. Press F5 to reload."
   5. Press F5 to reload the page
   6. As the page loads, API responses will be captured
   7. Scroll to load more — every response is captured automatically
   8. The floating panel shows count — click "Stop & Save" when done
   ════════════════════════════════════════════════════════ */

(function(){'use strict';

// ── Session storage: first run sets flag, second run executes ──
var MODE = sessionStorage.getItem('__xhs4_run');

if (!MODE) {
  // ═══════ FIRST RUN: set flag, show panel, then reload ═══════
  sessionStorage.setItem('__xhs4_run','2');
  // Clean any stale data
  sessionStorage.removeItem('__xhs4_data');

  var p = document.createElement('div');
  p.id='__xhs4';
  p.innerHTML='<div style="position:fixed;bottom:20px;right:20px;z-index:99999;background:#1a1a2e;color:#fff;padding:16px 20px;border-radius:12px;font:14px/1.4 monospace;box-shadow:0 4px 24px rgba(0,0,0,.5);min-width:340px;max-width:420px;border:1px solid #ff2442;max-height:90vh;overflow-y:auto;">'+
    '<div style="font-weight:700;color:#ff2442;margin-bottom:8px;font-size:15px;">RedNote v4 <span style="color:#888;font-weight:400;font-size:12px;">JSON.parse intercept</span></div>'+
    '<div style="margin:8px 0;text-align:center;padding:12px 0;background:#ff2442;color:#fff;border-radius:8px;font-size:15px;font-weight:700;">⏳ SET UP — Press F5 to reload</div>'+
    '<div style="color:#aaa;font-size:12px;text-align:center;">JSON.parse is now patched. Reload the page.</div>'+
    '<div id="_x4l" style="margin-top:8px;font-size:11px;color:#666;max-height:80px;overflow-y:auto;border-top:1px solid #333;padding-top:4px;"></div>'+
    '</div>';
  document.body.appendChild(p);
  var l=document.getElementById('_x4l');
  if(l){var d=document.createElement('div');d.textContent='Ready. Press F5.';l.appendChild(d);}
  console.log('%c[RedNote v4] JSON.parse patched. Reload (F5) to capture API data.','color:#ff2442;font-weight:bold;font-size:14px;');
  return;
}

// ═══════ SECOND RUN: intercept mode active ═══════

// ── Restore any previously captured data ──
var capturedStr = sessionStorage.getItem('__xhs4_data');
var entries = [];   // {noteId, xsecToken}
var seen = new Set();
if (capturedStr) {
  try {
    entries = JSON.parse(capturedStr);
    entries.forEach(function(e){if(e.noteId)seen.add(e.noteId);});
  } catch(e){entries=[];}
}

// ── Create control panel ──
var panel = document.createElement('div');
panel.id='__xhs4';
panel.innerHTML='<div style="position:fixed;bottom:20px;right:20px;z-index:99999;background:#1a1a2e;color:#fff;padding:16px 20px;border-radius:12px;font:14px/1.4 monospace;box-shadow:0 4px 24px rgba(0,0,0,.5);min-width:340px;max-width:420px;border:1px solid #ff2442;max-height:90vh;overflow-y:auto;">'+
  '<div style="font-weight:700;color:#ff2442;margin-bottom:8px;font-size:15px;">RedNote v4 <span style="color:#4ade80;font-weight:400;font-size:12px;">⚡ intercepting</span></div>'+
  '<div style="margin:8px 0;"><span id="_x4c" style="font-size:20px;font-weight:700;">'+entries.length+'</span> <span style="color:#aaa;">posts <span id="_x4ct" style="font-size:13px;color:#4ade80;">('+entries.filter(function(e){return e.xsecToken;}).length+' with token)</span></span></div>'+
  '<div id="_x4s" style="color:#aaa;font-size:12px;margin-bottom:6px;">Watching JSON.parse for API responses...</div>'+
  '<div style="display:flex;gap:6px;flex-wrap:wrap;">'+
  '<button id="_x4_stop" style="flex:1;padding:6px 0;border:1px solid #ff2442;background:transparent;color:#ff2442;border-radius:6px;cursor:pointer;font:inherit;min-width:70px;">Stop & Save</button>'+
  '<button id="_x4_scan" style="flex:1;padding:6px 0;border:1px solid #4ade80;background:transparent;color:#4ade80;border-radius:6px;cursor:pointer;font:inherit;min-width:70px;">Scan Page</button>'+
  '<button id="_x4_copy" style="padding:6px 10px;border:1px solid #555;background:transparent;color:#aaa;border-radius:6px;cursor:pointer;font:inherit;">Copy</button>'+
  '</div>'+
  '<div id="_x4l" style="margin-top:6px;font-size:11px;color:#666;max-height:150px;overflow-y:auto;border-top:1px solid #333;padding-top:4px;"></div>'+
  '</div>';
document.body.appendChild(panel);

var $=function(id){return document.getElementById(id);};
var logDiv=$('_x4l');
var logFn=function(msg){if(!logDiv)return;var d=document.createElement('div');d.textContent=msg;logDiv.appendChild(d);logDiv.scrollTop=logDiv.scrollHeight;};
var updateUI=function(){var c=$('_x4c');if(c)c.textContent=entries.length;var ct=$('_x4ct');if(ct)ct.textContent='('+entries.filter(function(e){return e.xsecToken;}).length+' with token)';};
var statusFn=function(msg){var s=$('_x4s');if(s)s.textContent=msg;};

// ════════════════════════════════════════════════════════════
// CORE TRICK: Override JSON.parse to intercept API responses
// ════════════════════════════════════════════════════════════

var origParse = JSON.parse;
JSON.parse = function(text, reviver) {
  // Parse normally first — we need the result
  var result = origParse.call(this, text, reviver);

  // Check if this looks like a user_posted API response
  try {
    if (result && typeof result === 'object' && result.data) {
      var notes = null;
      if (result.data.notes && Array.isArray(result.data.notes)) notes = result.data.notes;
      else if (result.data.items && Array.isArray(result.data.items)) notes = result.data.items;

      if (notes && notes.length > 0) {
        var count = 0;
        for (var i = 0; i < notes.length; i++) {
          var note = notes[i];
          var nid = note.note_id || note.id || '';
          var token = note.xsec_token || '';
          // Also check with underscores
          if (!token) token = note.xsecToken || '';
          if (nid && !seen.has(nid)) {
            seen.add(nid);
            entries.push({noteId: nid, xsecToken: token});
            count++;
          }
        }
        if (count > 0) {
          // Persist immediately
          try { sessionStorage.setItem('__xhs4_data', JSON.stringify(entries)); } catch(e){}
          updateUI();
          logFn('  JSON.parse intercept: +' + count + ' notes (' + entries.filter(function(e){return e.xsecToken;}).length + ' with token, ' + entries.length + ' total)');
          if (count > 0) statusFn(entries.filter(function(e){return e.xsecToken;}).length + ' posts with token');
        }
      }
    }
  } catch(e) {
    // Silent
  }

  return result;
};

logFn('JSON.parse override active — intercepting API responses...');

// ════════════════════════════════════════════════════════════
// Also scan page state: __INITIAL_STATE__, DOM, React fiber
// ════════════════════════════════════════════════════════════

function scanInitialState() {
  try {
    if (!window.__INITIAL_STATE__) return 0;
    var s = window.__INITIAL_STATE__;
    var count = 0;

    function walk(obj, depth) {
      if (depth > 5 || !obj) return;
      if (Array.isArray(obj)) {
        for (var i = 0; i < obj.length; i++) walk(obj[i], depth + 1);
      } else if (typeof obj === 'object' && obj !== null) {
        // Check if this is a note card entry
        var nc = obj.noteCard || obj;
        var nid = nc.noteId || obj.note_id || obj.id || '';
        var token = obj.xsecToken || obj.xsec_token || '';
        if (nid && !seen.has(nid)) {
          seen.add(nid);
          entries.push({noteId: nid, xsecToken: token});
          count++;
        }
        for (var k in obj) {
          if (k === 'noteCard' || k === 'xsecToken' || k === 'note_id') continue;
          if (typeof obj[k] === 'object' && obj[k] !== null) walk(obj[k], depth + 1);
        }
      }
    }

    walk(s, 0);
    if (count > 0) {
      try { sessionStorage.setItem('__xhs4_data', JSON.stringify(entries)); } catch(e){}
      logFn('  __INITIAL_STATE__: +' + count + ' entries');
    }
    return count;
  } catch(e) { return 0; }
}

function scanDOM() {
  var count = 0;
  // 1. Data attributes
  var els = document.querySelectorAll('[data-note-id]');
  for (var i = 0; i < els.length; i++) {
    var nid = els[i].getAttribute('data-note-id') || '';
    var token = els[i].getAttribute('data-xsec-token') || els[i].getAttribute('data-xsec_token') || '';
    if (nid && !seen.has(nid)) {
      seen.add(nid);
      entries.push({noteId: nid, xsecToken: token});
      count++;
    }
  }
  // 2. Anchor tags
  var links = document.querySelectorAll('a[href*="/explore/"]');
  for (var j = 0; j < links.length; j++) {
    var href = links[j].getAttribute('href') || '';
    var m = href.match(/\/explore\/([a-f0-9]+)/);
    if (!m) continue;
    var nid2 = m[1];
    if (nid2 && !seen.has(nid2)) {
      // Check if href already has token
      var tok = '';
      var qm = href.indexOf('xsec_token=');
      if (qm !== -1) {
        tok = href.substring(qm + 11).split('&')[0].split('#')[0];
      }
      seen.add(nid2);
      entries.push({noteId: nid2, xsecToken: tok});
      count++;
    }
  }
  if (count > 0) {
    try { sessionStorage.setItem('__xhs4_data', JSON.stringify(entries)); } catch(e){}
    updateUI();
  }
  return count;
}

// ── Scan existing page state ──
var fromState = scanInitialState();
var fromDOM = scanDOM();
logFn('Initial state: ' + fromState + ' from __INITIAL_STATE__, ' + fromDOM + ' from DOM');
logFn('Total: ' + entries.filter(function(e){return e.xsecToken;}).length + ' entries WITH token');
updateUI();

// ── MutationObserver for DOM changes ──
var obs = new MutationObserver(function(){
  scanDOM();
  updateUI();
});
obs.observe(document.body, {childList: true, subtree: true});

// ── Buttons ──
$('_x4_stop').onclick = function() {
  if (typeof _finish !== 'undefined') _finish();
};
$('_x4_scan').onclick = function() {
  scanDOM();
  updateUI();
  statusFn('Re-scanned: ' + entries.filter(function(e){return e.xsecToken;}).length + ' with token');
};
$('_x4_copy').onclick = function() {
  var urls = entries.filter(function(e){return e.xsecToken;}).map(function(e){
    return 'https://www.rednote.com/explore/' + e.noteId + '?xsec_token=' + e.xsecToken + '&xsec_source=pc_user';
  }).sort();
  navigator.clipboard.writeText(urls.join('\n')).then(function(){
    statusFn('Copied ' + urls.length + ' URLs!');
  });
};

// ── Auto-scroll with API trigger ──
var BASE = 'https://www.rednote.com';
var stopped = false;
var finished = false;

statusFn('Scrolling to trigger more API calls...');
(async function autoScroll() {
  for (var i = 0; i < 200 && !stopped && !finished; i++) {
    window.scrollBy(0, window.innerHeight * 1.5);
    await new Promise(function(r){setTimeout(r, 800 + Math.random() * 700);});
    scanDOM();
    updateUI();
    if (i % 10 === 0) {
      var wt = entries.filter(function(e){return e.xsecToken;}).length;
      statusFn('Scroll ' + i + ', ' + wt + ' with token');
    }
  }
  statusFn('Scrolling done — ' + entries.filter(function(e){return e.xsecToken;}).length + ' with token');
  if (!finished) _finish();
})();

var _finish = function() {
  if (finished) return;
  finished = true;
  stopped = true;
  try { obs.disconnect(); } catch(e){}

  var withToken = entries.filter(function(e){return e.xsecToken;});
  var withoutToken = entries.filter(function(e){return !e.xsecToken;});
  var urls = withToken.map(function(e){
    return BASE + '/explore/' + e.noteId + '?xsec_token=' + e.xsecToken + '&xsec_source=pc_user';
  }).sort();

  var msg = urls.length + ' URLs with token';
  if (withoutToken.length > 0) msg += ' (' + withoutToken.length + ' IDs without token)';
  statusFn(msg);
  logFn('Finish: ' + msg);

  if (urls.length === 0) {
    logFn('No URLs with xsec_token were captured.');
    logFn('The JSON.parse override found ' + entries.length + ' note IDs but none had tokens.');
    logFn('Try the Xiaohongshu scraper in the Settings tab instead.');
    // Clean up
    sessionStorage.removeItem('__xhs4_run');
    sessionStorage.removeItem('__xhs4_data');
    return;
  }

  // Channel name
  var name = 'xiaohongshu';
  var tm = document.title.match(/@([\w一-鿿]+)/);
  if (tm) name = tm[1];
  else {
    var pm = window.location.pathname.match(/\/user\/profile\/([a-f0-9]+)/);
    if (pm) name = pm[1].slice(0, 16);
  }

  var ts = new Date().toISOString().replace(/[:.]/g,'-').slice(0,-5);
  var blob = new Blob([urls.join('\n')], {type:'text/plain'});
  var a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = name + '_xhs_videos_' + ts + '.txt';
  a.click();
  URL.revokeObjectURL(a.href);
  logFn('Saved: ' + a.download);

  // Cleanup
  sessionStorage.removeItem('__xhs4_run');
  sessionStorage.removeItem('__xhs4_data');
};

})();
