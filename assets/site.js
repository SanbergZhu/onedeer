const menu = document.querySelector('.menu');
const nav = document.querySelector('#navigation');
function closeMenu() { nav.classList.remove('open'); menu.setAttribute('aria-expanded', 'false'); }
menu.addEventListener('click', () => { const open = nav.classList.toggle('open'); menu.setAttribute('aria-expanded', String(open)); });
nav.addEventListener('click', e => { if (e.target.closest('a')) closeMenu(); });
document.addEventListener('keydown', e => { if (e.key === 'Escape') { closeMenu(); } });
const goods = document.querySelector('#goods');
const output = document.querySelector('#fee');
function calculate() {
 const value = goods.valueAsNumber;
 if (!Number.isFinite(value) || value < 0) { output.textContent = 'Enter a valid amount'; return; }
 const fee = Math.max(250, Math.min(value,10000)*0.05 + Math.min(Math.max(value-10000,0),40000)*0.03 + Math.max(value-50000,0)*0.02);
 output.textContent = new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',maximumFractionDigits:2}).format(fee).replace('$','US$');
}
goods.addEventListener('input',calculate);
calculate();
