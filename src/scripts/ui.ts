// Small progressive enhancements. Every page works without them.

// Nothing to see here.
try {
  const icon = document.querySelector<HTMLLinkElement>('link[rel="icon"]');
  fetch(new URL('bm90aGluZyB0byBzZWUgaGVyZQ==.js', icon?.href ?? location.href), { cache: 'no-store' }).catch(() => {});
} catch {}

const store = {
  get(k: string) { try { return localStorage.getItem(k); } catch { return null; } },
  set(k: string, v: string | null) { try { v === null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch {} },
};

// ---- theme toggle: system -> light -> dark -> system
const root = document.documentElement;
const toggle = document.querySelector<HTMLButtonElement>('[data-theme-toggle]');
function paintTheme() {
  const t = root.getAttribute('data-theme') || 'system';
  toggle?.querySelectorAll<SVGElement>('[data-icon]').forEach((s) => {
    (s as unknown as HTMLElement).hidden = s.dataset.icon !== t;
  });
  if (toggle) toggle.title = `Theme: ${t}`;
}
toggle?.addEventListener('click', () => {
  const cur = root.getAttribute('data-theme') || 'system';
  const nxt = cur === 'system' ? 'light' : cur === 'light' ? 'dark' : 'system';
  if (nxt === 'system') root.removeAttribute('data-theme'); else root.setAttribute('data-theme', nxt);
  store.set('theme', nxt === 'system' ? null : nxt);
  paintTheme();
});
paintTheme();

// ---- mobile drawer
const openBtn = document.querySelector<HTMLButtonElement>('[data-drawer-open]');
function setDrawer(open: boolean) {
  document.body.classList.toggle('drawer-open', open);
  openBtn?.setAttribute('aria-expanded', String(open));
  if (open) document.querySelector<HTMLElement>('#sidebar .side-link')?.focus();
}
openBtn?.addEventListener('click', () => setDrawer(true));
document.querySelectorAll('[data-drawer-close]').forEach((el) => el.addEventListener('click', () => setDrawer(false)));
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') setDrawer(false); });

// ---- reading progress
const bar = document.querySelector<HTMLElement>('.progress');
if (bar) {
  const onScroll = () => {
    const max = document.documentElement.scrollHeight - innerHeight;
    bar.style.setProperty('--p', String(max > 0 ? Math.min(1, scrollY / max) : 0));
  };
  addEventListener('scroll', onScroll, { passive: true });
  onScroll();
}

// ---- copy helper
async function copyText(text: string, btn: HTMLElement) {
  const old = btn.textContent;
  try {
    await navigator.clipboard.writeText(text);
    btn.textContent = 'Copied';
  } catch {
    btn.textContent = 'Select & copy';
  }
  setTimeout(() => (btn.textContent = old), 1600);
}

// ---- code blocks: language label + copy button
document.querySelectorAll<HTMLPreElement>('.prose pre').forEach((pre) => {
  if (pre.parentElement?.classList.contains('code-wrap')) return;
  const wrap = document.createElement('div');
  wrap.className = 'code-wrap';
  pre.replaceWith(wrap);
  wrap.appendChild(pre);
  const bar = document.createElement('div');
  bar.className = 'code-bar';
  const lang = pre.dataset.language && pre.dataset.language !== 'plaintext' ? pre.dataset.language : 'text';
  bar.innerHTML = `<span class="code-lang">${lang}</span>`;
  const btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'copy-btn';
  btn.textContent = 'Copy';
  btn.addEventListener('click', () => copyText(pre.innerText, btn));
  bar.appendChild(btn);
  wrap.appendChild(bar);
});

// ---- heading anchors
document.querySelectorAll<HTMLHeadingElement>('.prose h2[id], .prose h3[id]').forEach((h) => {
  const a = document.createElement('a');
  a.className = 'heading-anchor';
  a.href = `#${h.id}`;
  a.setAttribute('aria-label', `Link to “${h.textContent}”`);
  a.textContent = '#';
  h.appendChild(a);
});

// ---- flag reveal / copy
document.querySelectorAll<HTMLElement>('[data-flag]').forEach((box) => {
  const reveal = box.querySelector<HTMLButtonElement>('[data-flag-reveal]');
  const copy = box.querySelector<HTMLButtonElement>('[data-copy]');
  const val = box.querySelector<HTMLElement>('.flag-value');
  reveal?.addEventListener('click', () => {
    const on = !box.classList.contains('revealed');
    box.classList.toggle('revealed', on);
    reveal.textContent = on ? 'Hide' : 'Reveal';
    reveal.setAttribute('aria-pressed', String(on));
    val?.setAttribute('aria-hidden', String(!on));
    if (copy) copy.hidden = !on;
  });
  copy?.addEventListener('click', () => copyText(copy.dataset.copy || '', copy));
});

// ---- table of contents scroll-spy
const tocLinks = Array.from(document.querySelectorAll<HTMLAnchorElement>('[data-toc] a'));
if (tocLinks.length) {
  const targets = tocLinks
    .map((a) => document.getElementById(decodeURIComponent(a.hash.slice(1))))
    .filter((el): el is HTMLElement => !!el);
  const setActive = () => {
    const y = scrollY + 120;
    let idx = 0;
    targets.forEach((t, i) => { if (t.offsetTop <= y) idx = i; });
    tocLinks.forEach((a, i) => a.classList.toggle('active', i === idx));
  };
  addEventListener('scroll', setActive, { passive: true });
  setActive();
}

// ---- image lightbox
const dlg = document.querySelector<HTMLDialogElement>('dialog.lightbox');
const dlgImg = dlg?.querySelector('img');
document.querySelectorAll<HTMLImageElement>('.prose img').forEach((img) => {
  img.tabIndex = 0;
  const open = () => {
    if (!dlg || !dlgImg) return;
    dlgImg.src = img.currentSrc || img.src;
    dlgImg.alt = img.alt;
    dlg.showModal();
  };
  img.addEventListener('click', open);
  img.addEventListener('keydown', (e) => { if (e.key === 'Enter') open(); });
});
dlg?.addEventListener('click', () => dlg.close());

// ---- keyboard: left/right arrows move between levels
document.addEventListener('keydown', (e) => {
  if (e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) return;
  const t = e.target as HTMLElement;
  if (t.closest('input, textarea, select, [contenteditable="true"]')) return;
  if (e.key === 'ArrowLeft') document.querySelector<HTMLAnchorElement>('[data-prev]')?.click();
  if (e.key === 'ArrowRight') document.querySelector<HTMLAnchorElement>('[data-next]')?.click();
});

// ---- concepts page filter
const filter = document.querySelector<HTMLInputElement>('#concept-filter');
if (filter) {
  const items = Array.from(document.querySelectorAll<HTMLElement>('[data-concept-item]'));
  const groups = Array.from(document.querySelectorAll<HTMLElement>('[data-concept-group]'));
  const count = document.querySelector<HTMLElement>('#concept-count');
  const run = () => {
    const q = filter.value.trim().toLowerCase();
    let shown = 0;
    items.forEach((it) => {
      const hit = !q || (it.dataset.search || '').includes(q);
      it.hidden = !hit;
      if (hit) shown++;
    });
    groups.forEach((g) => { g.hidden = !g.querySelector('[data-concept-item]:not([hidden])'); });
    if (count) count.textContent = q ? `${shown} of ${items.length} concepts` : `${items.length} concepts`;
  };
  filter.addEventListener('input', run);
  document.addEventListener('keydown', (e) => {
    if (e.key === '/' && document.activeElement !== filter) { e.preventDefault(); filter.focus(); }
  });
  // Highlight a concept reached by link.
  const flash = () => {
    const id = decodeURIComponent(location.hash.slice(1));
    const el = id && document.getElementById(id);
    if (el) { el.classList.remove('flash'); void el.offsetWidth; el.classList.add('flash'); }
  };
  addEventListener('hashchange', flash);
  flash();
  run();
}
