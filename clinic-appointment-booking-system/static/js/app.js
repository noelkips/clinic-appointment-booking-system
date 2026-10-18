'use strict';
document.querySelectorAll('.menu-toggle').forEach(button => {
  button.addEventListener('click', () => {
    const nav = document.getElementById(button.getAttribute('aria-controls'));
    const open = button.getAttribute('aria-expanded') !== 'true';
    button.setAttribute('aria-expanded', String(open));
    nav.classList.toggle('open', open);
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
document.querySelectorAll('.workspace-nav nav a').forEach(a => { if (a.pathname === location.pathname) { a.classList.add('active'); a.setAttribute('aria-current','page'); } });
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
