'use strict';

// One accessible drawer controller serves both public and workspace navigation.
const drawerControllers = [];
document.querySelectorAll('[data-nav-panel]').forEach(panel => {
  const mobileNavigation = window.matchMedia('(max-width: ' + (panel.dataset.navBreakpoint || '800px') + ')');
  const trigger = document.querySelector('[data-nav-trigger="' + panel.id + '"]');
  const backdrop = document.querySelector('[data-nav-backdrop="' + panel.id + '"]');
  if (!trigger || !backdrop) return;
  let opened = false;
  let restoreTarget = null;
  let backgroundState = [];
  function focusable() {
    return Array.from(panel.querySelectorAll('a[href],button,input,select,textarea,summary,[tabindex]:not([tabindex="-1"])'))
      .filter(el => !el.disabled && !el.closest('[inert]') && el.getClientRects().length);
  }
  function close(restore = true) {
    if (!opened) return;
    opened = false;
    panel.classList.remove('navigation-open');
    backdrop.hidden = true;
    trigger.setAttribute('aria-expanded','false');
    backgroundState.forEach(([el, previous]) => { el.inert = previous; });
    backgroundState = [];
    document.body.classList.remove('navigation-locked');
    panel.removeAttribute('aria-modal');
    panel.removeAttribute('role');
    if (restore && restoreTarget && restoreTarget.isConnected) restoreTarget.focus({preventScroll:true});
    panel.inert = mobileNavigation.matches;
    if (mobileNavigation.matches) panel.setAttribute('aria-hidden','true');
  }
  function sync() {
    close(false);
    panel.inert = mobileNavigation.matches;
    if (mobileNavigation.matches) panel.setAttribute('aria-hidden','true');
    else panel.removeAttribute('aria-hidden');
  }
  function open() {
    if (!mobileNavigation.matches) return;
    drawerControllers.forEach(controller => controller.close(false));
    restoreTarget = document.activeElement;
    panel.inert = false;
    panel.removeAttribute('aria-hidden');
    panel.setAttribute('role','dialog');
    panel.setAttribute('aria-modal','true');
    panel.classList.add('navigation-open');
    backdrop.hidden = false;
    trigger.setAttribute('aria-expanded','true');
    document.body.classList.add('navigation-locked');
    backgroundState = Array.from(document.querySelectorAll('[data-nav-background]'))
      .filter(el => !el.contains(panel)).map(el => [el,el.inert]);
    backgroundState.forEach(([el]) => { el.inert=true; });
    opened = true;
    const first = panel.querySelector('[data-nav-close]') || focusable()[0];
    if (first) first.focus({preventScroll:true});
  }
  trigger.addEventListener('click', () => opened ? close() : open());
  backdrop.addEventListener('click', () => close());
  panel.querySelectorAll('[data-nav-close]').forEach(button => button.addEventListener('click', () => close()));
  panel.querySelectorAll('a[href]').forEach(link => link.addEventListener('click', () => close()));
  document.addEventListener('keydown', event => {
    if (!opened) return;
    if (event.key === 'Escape') { event.preventDefault(); close(); return; }
    if (event.key === 'Tab') {
      const items=focusable();
      const first=items[0], last=items[items.length-1];
      if (!first) { event.preventDefault(); return; }
      if (event.shiftKey && (document.activeElement === first || !panel.contains(document.activeElement))) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && (document.activeElement === last || !panel.contains(document.activeElement))) { event.preventDefault(); first.focus(); }
    }
  });
  mobileNavigation.addEventListener('change', sync);
  drawerControllers.push({close});
  sync();
});

const collapseControl = document.querySelector('[data-sidebar-collapse]');
if (collapseControl) {
  function setCollapsed(collapsed) {
    document.body.classList.toggle('sidebar-collapsed', collapsed);
    collapseControl.setAttribute('aria-expanded',String(!collapsed));
    collapseControl.setAttribute('aria-label',collapsed ? 'Expand sidebar' : 'Collapse sidebar');
    collapseControl.title=collapsed ? 'Expand sidebar' : 'Collapse sidebar';
  }
  try { setCollapsed(localStorage.getItem('savannah.sidebarCollapsed') === 'true'); } catch (_) { setCollapsed(false); }
  collapseControl.addEventListener('click', () => {
    const collapsed=!document.body.classList.contains('sidebar-collapsed');
    setCollapsed(collapsed);
    try { localStorage.setItem('savannah.sidebarCollapsed',String(collapsed)); } catch (_) { /* Navigation remains functional without storage. */ }
  });
}

document.querySelectorAll('[data-user-menu]').forEach(menu => {
  document.addEventListener('click', event => { if (!menu.contains(event.target)) menu.open=false; });
  menu.addEventListener('keydown', event => {
    if (event.key==='Escape' && menu.open) { event.preventDefault(); menu.open=false; menu.querySelector('summary').focus(); }
  });
});

const publicHeader = document.querySelector('[data-public-header]');
if (publicHeader) {
  const updateHeader=() => publicHeader.classList.toggle('is-scrolled',window.scrollY>8);
  window.addEventListener('scroll',updateHeader,{passive:true});
  updateHeader();
}
function markSection(id) {
  document.querySelectorAll('[data-section]').forEach(link => {
    const active=link.dataset.section===id;
    link.classList.toggle('active',active);
    if (active) link.setAttribute('aria-current','location'); else link.removeAttribute('aria-current');
  });
  const home=document.querySelector('[data-page-home]');
  if (home && document.getElementById('how-it-works')) {
    home.classList.toggle('active',!id);
    if (!id) home.setAttribute('aria-current','page'); else home.removeAttribute('aria-current');
  }
}
const howSection=document.getElementById('how-it-works');
if (howSection && 'IntersectionObserver' in window) {
  new IntersectionObserver(entries => { if (entries[0]) markSection(entries[0].isIntersecting ? 'how-it-works' : ''); },{rootMargin:'-100px 0px -35% 0px'}).observe(howSection);
}
document.querySelectorAll('a[href]').forEach(link => {
  link.addEventListener('click',event => {
    if (event.defaultPrevented || event.button!==0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    const url=new URL(link.href,location.href);
    if (url.origin!==location.origin || url.pathname!==location.pathname || url.search!==location.search || !url.hash) return;
    const target=document.getElementById(decodeURIComponent(url.hash.slice(1)));
    if (!target) return;
    event.preventDefault();
    drawerControllers.forEach(controller => controller.close(false));
    if (!target.hasAttribute('tabindex')) target.setAttribute('tabindex','-1');
    target.focus({preventScroll:true});
    target.scrollIntoView({behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth',block:'start'});
    history.pushState(null,'',url.hash);
    markSection(target.id);
  });
});

document.querySelectorAll('[data-password]').forEach(button => {
  button.addEventListener('click', () => {
    const input = document.getElementById(button.dataset.password);
    const show = input.type === 'password';
    input.type = show ? 'text' : 'password';
    button.textContent = show ? 'Hide' : 'Show';
    button.setAttribute('aria-label', show ? 'Hide password' : 'Show password');
  });
});
document.querySelectorAll('[data-confirm]').forEach(button => {
  button.addEventListener('click', event => { if (!window.confirm(button.dataset.confirm)) event.preventDefault(); });
});
document.addEventListener('visibilitychange', () => document.body.classList.toggle('motion-paused', document.hidden));
document.querySelectorAll('[data-slot-form]').forEach(form => {
  const doctor = form.querySelector('[name=doctor]');
  const date = form.querySelector('[name=date]');
  const select = form.querySelector('[name=starts_at]');
  const status = form.querySelector('[data-slot-status]');
  const initial = new URLSearchParams(location.search).get('slot');
  let requestNumber = 0;
  async function load() {
    const id = doctor ? doctor.value : form.dataset.doctor;
    if (!id || !date.value) return;
    const current = ++requestNumber;
    select.replaceChildren(new Option('Loading available times...', ''));
    select.disabled = true;
    try {
      const response = await fetch('/api/doctors/' + encodeURIComponent(id) + '/availability?date=' + encodeURIComponent(date.value), {credentials:'same-origin'});
      if (!response.ok) throw new Error('Could not load availability. Please try again.');
      const data = await response.json();
      if (current !== requestNumber) return;
      select.replaceChildren(new Option(data.slots.length ? 'Choose a time' : 'No available times', ''));
      data.slots.forEach(value => {
        const label = new Intl.DateTimeFormat('en-GB',{hour:'2-digit',minute:'2-digit',timeZone:'Africa/Nairobi'}).format(new Date(value));
        select.add(new Option(label, value, false, value === initial));
      });
      status.textContent = data.slots.length ? 'Available 30-minute slots, in Nairobi time.' : 'No available slots. Please choose another date.';
    } catch (error) {
      if (current === requestNumber) { select.replaceChildren(new Option('Try another date', '')); status.textContent = error.message; }
    } finally { if (current === requestNumber) select.disabled = false; }
  }
  if (doctor) doctor.addEventListener('change', load);
  date.addEventListener('change', load);
  load();
});
