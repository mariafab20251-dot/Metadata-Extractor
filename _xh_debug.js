/* Run these one at a time in the console on a FRESH page load (no other scripts running) */

// ═══ 1) List ALL keys on #app element ═══
var el = document.querySelector('#app');
console.log('All keys on #app:', Object.getOwnPropertyNames(el));

// ═══ 2) Try enumerating ALL properties ═══
for (var k in el) { if (k.indexOf('vue') !== -1 || k.indexOf('__v') !== -1 || k.indexOf('__react') !== -1) { console.log('Found:', k); } }

// ═══ 3) Try __vue_app__ directly (it might be a specific key name) ═══
var app = el.__vue_app__ || el._vueApp || el._vnode;
if (app) { console.log('App:', typeof app, Object.keys(app).slice(0, 20)); }

// ═══ 4) Check __vueParentComponent or other Vue internals ═══
var bodyChildren = document.body.children;
for (var i = 0; i < Math.min(10, bodyChildren.length); i++) {
  var c = bodyChildren[i];
  var own = Object.getOwnPropertyNames(c);
  var vueKeys = own.filter(function(k) { return k.indexOf('vue') !== -1 || k.indexOf('__v') !== -1; });
  if (vueKeys.length) { console.log('Child', i, vueKeys); }
}
