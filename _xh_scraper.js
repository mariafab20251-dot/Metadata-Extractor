(async function() {
  'use strict';
  const posts = new Map();

  // ── Floating panel ──
  const panel = document.createElement('div');
  panel.id = '__xhs';
  panel.innerHTML = `
<div style="position:fixed;bottom:20px;right:20px;z-index:99999;
     background:#1a1a2e;color:#fff;padding:16px 20px;border-radius:12px;
     font:14px/1.4 monospace;box-shadow:0 4px 24px rgba(0,0,0,.5);
     min-width:320px;max-width:400px;border:1px solid #ff2442;
     max-height:90vh;overflow-y:auto;">
  <div style="font-weight:700;color:#ff2442;margin-bottom:8px;font-size:15px;">
    RedNote/Xiaohongshu Scraper
  </div>
  <div style="margin:8px 0;">
    <span id="__xhs_c" style="font-size:20px;font-weight:700;">0</span>
    <span style="color:#aaa;">posts</span>
  </div>
  <div id="__xhs_s" style="color:#aaa;font-size:12px;margin-bottom:6px;">Starting...</div>
  <div style="display:flex;gap:6px;flex-wrap:wrap;">
    <button id="__xhs_stop" style="flex:1;padding:6px 0;border:1px solid #ff2442;
           background:transparent;color:#ff2442;border-radius:6px;cursor:pointer;
           font:inherit;min-width:80px;">Stop & Save</button>
    <button id="__xhs_copy" style="padding:6px 10px;border:1px solid #555;
           background:transparent;color:#aaa;border-radius:6px;cursor:pointer;
           font:inherit;">Copy URLs</button>
  </div>
  <div id="__xhs_log" style="margin-top:6px;font-size:11px;color:#666;
       max-height:150px;overflow-y:auto;border-top:1px solid #333;padding-top:4px;"></div>
</div>`.trim();
  document.body.appendChild(panel);

  const $ = id => document.getElementById(id);
  const log = msg => { const e = $('__xhs_log'); if (e) { const d = document.createElement('div'); d.textContent = msg; e.appendChild(d); e.scrollTop = e.scrollHeight; } };
  const updateCount = () => { const c = $('__xhs_c'); if (c) c.textContent = posts.size; };
  const status = msg => { const s = $('__xhs_s'); if (s) s.textContent = msg; };

  // ── Collect explore/reel URLs from DOM ──
  function collectFromDOM() {
    let added = 0;
    document.querySelectorAll('a[href*="/explore/"]').forEach(a => {
      // Xiaohongshu needs the xsec_token — keep full URL with query params
      const m = a.href.match(/\/explore\/([a-f0-9]+)/);
      const key = m ? m[1] : a.href;
      if (!posts.has(key)) { posts.set(key, a.href); added++; }
    });
    if (added > 0) { updateCount(); log('+'+added+' new -> '+posts.size+' total'); }
    return added;
  }

  const observer = new MutationObserver(() => collectFromDOM());
  observer.observe(document.body, { childList: true, subtree: true });
  collectFromDOM();
  log('Initial scan: '+posts.size+' posts');

  let stopped = false, finished = false;
  $('__xhs_stop').onclick = () => { stopped = true; if (!finished) finish(); };
  $('__xhs_copy').onclick = () => {
    const u = [...posts.values()].sort();
    navigator.clipboard.writeText(u.join('\n')).then(() => status('Copied '+u.length+' URLs!'));
  };

  async function scrollPass(label) {
    status(label+' - scrolling...');
    let empty = 0;
    for (let i = 0; i < 300 && !stopped; i++) {
      window.scrollBy(0, window.innerHeight * 1.5);
      await new Promise(r => setTimeout(r, 800 + Math.random() * 700));
      const added = collectFromDOM();
      if (added === 0) {
        empty++;
        if (empty >= 8) {
          status(label+' - checking harder...');
          window.scrollBy(0, window.innerHeight * 3);
          await new Promise(r => setTimeout(r, 3000));
          if (collectFromDOM() === 0) {
            window.scrollBy(0, -window.innerHeight * 2);
            await new Promise(r => setTimeout(r, 1500));
            window.scrollBy(0, window.innerHeight * 3);
            await new Promise(r => setTimeout(r, 3000));
            if (collectFromDOM() === 0) { log(label+' - no more posts'); break; }
            empty = 3;
          } else { empty = 0; }
        }
      } else { empty = Math.max(0, empty - 1); }
      if (i % 20 === 0) status(label+' scroll '+i+', '+posts.size+' posts');
    }
  }

  await scrollPass('Pass 1/2');

  if (!stopped && posts.size > 0) {
    status('Pass 2/2 - resetting...');
    window.scrollTo(0, 0);
    await new Promise(r => setTimeout(r, 3000));
    collectFromDOM();
    await scrollPass('Pass 2/2');
  }

  status('Done - '+posts.size+' posts');
  if (!finished) await finish();

  async function finish() {
    if (finished) return;
    finished = true;
    observer.disconnect();
    const urls = [...posts.values()].sort();
    status('Done - '+urls.length+' unique posts');

    let name = 'xiaohongshu';
    const titleMatch = document.title.match(/@(\w+)/);
    if (titleMatch) name = titleMatch[1];
    else {
      const pathMatch = window.location.pathname.match(/\/user\/profile\/([a-f0-9]+)/);
      if (pathMatch) name = pathMatch[1].slice(0, 16);
    }

    const ts = new Date().toISOString().replace(/[:.]/g,'-').slice(0,-5);
    const blob = new Blob([urls.join('\n')], {type:'text/plain'});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = name+'_xhs_videos_'+ts+'.txt';
    a.click();
    URL.revokeObjectURL(a.href);
    log('Downloaded: '+name+'_xhs_videos_'+ts+'.txt');
  }
})();
