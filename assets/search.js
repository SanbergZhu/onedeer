(() => {
  'use strict';
  const queryInput = document.querySelector('#product-query');
  const locationInput = document.querySelector('#location-filter');
  const sortInput = document.querySelector('#sort-filter');
  const results = document.querySelector('#results');
  const resultCount = document.querySelector('#result-count');
  const shownCount = document.querySelector('#shown-count');
  const loadMore = document.querySelector('#load-more');
  const emptyState = document.querySelector('#empty-state');
  const errorState = document.querySelector('#error-state');
  const parameters = new URLSearchParams(window.location.search);
  const PAGE_SIZE = 12;
  let products = [];
  let visibleCount = PAGE_SIZE;
  let loaded = false;
  let debounce;
  queryInput.value = (parameters.get('q') || '').slice(0,120);
  if (['relevance','name','price-low','price-high'].includes(parameters.get('sort'))) sortInput.value = parameters.get('sort');
  const normal = value => String(value || '').normalize('NFKD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[’‘]/g,"'").replace(/[^\p{L}\p{N}]+/gu,' ').trim();
  function matches(product, tokens) { return tokens.every(token => product.searchText.includes(token)); }
  function score(product, tokens) {
    const name = normal(`${product.name} ${product.nameZh}`);
    return tokens.reduce((total, token) => total + (name.startsWith(token) ? 4 : name.includes(token) ? 2 : 0), 0);
  }
  function node(tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text != null) element.textContent = text;
    return element;
  }
  const money = new Intl.NumberFormat('en-US',{minimumFractionDigits:2, maximumFractionDigits:2});
  function hasPrice(product) { return Number.isFinite(product.priceMin) && Number.isFinite(product.priceMax); }
  function productCard(product) {
    const article = node('article','product-row');
    const title = node('div','product-name');
    title.append(node('h3','',product.name));
    if (product.nameZh) title.append(node('p','product-name-zh',product.nameZh));
    const location = node('div','product-location');
    location.append(node('span','mobile-label','Supplier location'), node('p','',product.location || 'Available on request'));
    if (product.locationZh) location.append(node('span','location-zh',product.locationZh));
    const price = node('div','product-price');
    price.append(node('span','mobile-label','Indicative FOB / unit'));
    price.append(node('strong','',hasPrice(product) ? `CNY ${money.format(product.priceMin)} – ${money.format(product.priceMax)}` : 'Price on request'));
    const enquiry = node('a','product-enquiry','Enquire ↗');
    enquiry.href = 'mailto:zhu.chaoran@gmail.com?subject=' + encodeURIComponent(`ONEDeer product enquiry — ${product.name}`) + '&body=' + encodeURIComponent(`Product: ${product.name}\nSupplier location: ${product.location || 'Please advise'}\nMy specifications:\nTarget quantity:\nTarget markets:\n`);
    enquiry.setAttribute('aria-label', `Enquire about ${product.name}${product.location ? ' from '+product.location : ''}`);
    article.append(title,location,price,enquiry);
    return article;
  }
  function syncUrl() {
    const parameters = new URLSearchParams();
    if (queryInput.value.trim()) parameters.set('q',queryInput.value.trim());
    if (locationInput.value) parameters.set('location',locationInput.value);
    if (sortInput.value !== 'relevance') parameters.set('sort',sortInput.value);
    window.history.replaceState(null,'',window.location.pathname + (parameters.size ? '?'+parameters.toString() : '') + window.location.hash);
  }
  function render(reset = true) {
    if (!loaded) return;
    if (reset) visibleCount = PAGE_SIZE;
    syncUrl();
    const tokens = normal(queryInput.value).split(' ').filter(Boolean);
    const filtered = products.filter(product => matches(product,tokens) && (!locationInput.value || (locationInput.value === 'unknown' ? !product.location : product.location === locationInput.value)));
    filtered.sort((a,b) => {
      if (sortInput.value.startsWith('price-')) {
        if (!hasPrice(a) || !hasPrice(b)) return Number(hasPrice(b))-Number(hasPrice(a)) || a.name.localeCompare(b.name);
        const difference = sortInput.value==='price-low' ? a.priceMin-b.priceMin : b.priceMax-a.priceMax;
        return difference || a.name.localeCompare(b.name);
      }
      return (sortInput.value==='relevance' ? score(b,tokens)-score(a,tokens) : 0) || a.name.localeCompare(b.name);
    });
    results.replaceChildren(...filtered.slice(0,visibleCount).map(productCard));
    resultCount.textContent = `${filtered.length} ${filtered.length===1?'product':'products'}${tokens.length || locationInput.value ? ' found' : ' to explore'}`;
    shownCount.textContent = filtered.length ? `Showing ${Math.min(visibleCount,filtered.length)} of ${filtered.length} products` : '';
    emptyState.hidden = filtered.length !== 0;
    errorState.hidden = true;
    loadMore.hidden = visibleCount >= filtered.length;
  }
  async function loadCatalog() {
    errorState.hidden = true;
    emptyState.hidden = true;
    results.setAttribute('aria-busy','true');
    resultCount.textContent = 'Loading products…';
    try {
      const response = await fetch('data/products.json',{cache:'no-cache'});
      if (!response.ok) throw new Error('Could not load catalog');
      const data = await response.json();
      if (data.schemaVersion !== 1 || !Array.isArray(data.products) || data.products.length===0) throw new Error('Invalid catalog');
      products = data.products.map(product => {
        if (typeof product.name!=='string' || typeof product.location!=='string' || product.currency!=='CNY' ||
            !((product.priceMin===null && product.priceMax===null) || (Number.isFinite(product.priceMin) && Number.isFinite(product.priceMax) && product.priceMin>0 && product.priceMax>=product.priceMin))) throw new Error('Invalid product');
        return {...product, searchText:normal(`${product.name} ${product.nameZh || ''} ${product.location} ${product.locationZh || ''}`)};
      });
      const currentLocation = loaded ? locationInput.value : (parameters.get('location') || '');
      const locations = [...new Set(products.map(product=>product.location).filter(Boolean))].sort();
      locationInput.replaceChildren(new Option('All locations',''),new Option('Location not recorded','unknown'),...locations.map(location=>new Option(location,location)));
      locationInput.value = currentLocation==='unknown' || locations.includes(currentLocation) ? currentLocation : '';
      const updated = new Date(data.updatedAt);
      document.querySelector('#snapshot-date').textContent = Number.isNaN(updated.getTime()) ? '' : `Directory updated ${new Intl.DateTimeFormat('en-GB',{day:'numeric',month:'short',year:'numeric',timeZone:'Asia/Singapore'}).format(updated)}`;
      loaded = true;
      render();
    } catch {
      loaded = false;
      products = [];
      results.replaceChildren();
      resultCount.textContent = 'Directory unavailable';
      shownCount.textContent = '';
      loadMore.hidden = true;
      errorState.hidden = false;
    } finally { results.setAttribute('aria-busy','false'); }
  }
  document.querySelector('#search-form').addEventListener('submit',event=>{event.preventDefault();clearTimeout(debounce);render();});
  queryInput.addEventListener('input',()=>{clearTimeout(debounce);debounce=setTimeout(()=>render(),180);});
  locationInput.addEventListener('change',()=>render());
  sortInput.addEventListener('change',()=>render());
  document.querySelectorAll('[data-query]').forEach(button=>button.addEventListener('click',()=>{queryInput.value=button.dataset.query;render();}));
  document.querySelector('#clear-search').addEventListener('click',()=>{queryInput.value='';locationInput.value='';sortInput.value='relevance';render();queryInput.focus();});
  loadMore.addEventListener('click',()=>{const previous=visibleCount;visibleCount+=PAGE_SIZE;render(false);const next=results.children[previous];if(next){next.tabIndex=-1;next.focus({preventScroll:true});}});
  document.querySelector('#retry-load').addEventListener('click',loadCatalog);
  loadCatalog();
})();
