// Dynamically load and display vehicles on the vans page
async function loadAllVehicles() {
	try {
		const response = await fetch('/api/vans');
		const vans = await response.json();
		
		const container = document.getElementById('featured');
		if (!container) return;
		
		// Clear existing content
		container.innerHTML = '';
		
		// Add each vehicle as a card
		vans.forEach(van => {
			const card = document.createElement('a');
			card.className = 'card v';
			card.href = `/van/${van.slug}`;
			
			const imageUrl = van.imageUrl || (van.photos && van.photos[0]) || '/static/images/placeholder.jpg';
			const price = van.pricePerNight ? `€${van.pricePerNight} / night` : 'Ask for details';
			const description = van.description || 'Contact us for more information.';
			
			// Determine badge text based on vehicle type
			let badgeText = 'Van';
			const slugLower = van.slug.toLowerCase();
			if (slugLower.includes('car') || slugLower.includes('nissan')) {
				badgeText = 'Car';
			} else if (slugLower.includes('moto') || slugLower.includes('bike')) {
				badgeText = 'Moto';
			}
			
			card.innerHTML = `
				<img class="thumb" src="${imageUrl}" alt="${van.name}" />
				<div class="body">
					<div class="title">${van.name} <span class="badge-accent">${badgeText}</span></div>
					<div class="sub">${price}</div>
					<div class="desc">${description}</div>
				</div>
			`;
			
			container.appendChild(card);
		});
		
		// Add "Coming soon" moto card if there are less than 4 vehicles
		if (vans.length < 4) {
			const comingSoonCard = document.createElement('a');
			comingSoonCard.className = 'card v coming-soon';
			comingSoonCard.href = '#';
			comingSoonCard.setAttribute('aria-disabled', 'true');
			comingSoonCard.onclick = () => false;
			
			comingSoonCard.innerHTML = `
				<div class="overlay-badge">Coming soon</div>
				<img class="thumb" src="/static/images/moto/IMG-20250512-WA0025.jpg" alt="Moto" />
				<div class="body">
					<div class="title">Moto <span class="badge-accent">Moto</span></div>
					<div class="sub">Coming soon</div>
				</div>
			`;
			
			container.appendChild(comingSoonCard);
		}
	} catch (error) {
		console.error('Error loading vehicles:', error);
	}
}

// Load vehicles when page loads
document.addEventListener('DOMContentLoaded', loadAllVehicles);

// == mobile-fix-first-tap ==
(function(){
  if (window.__calFixBound) return; window.__calFixBound = true;
  let start=null, end=null;

  function parse(s){ const a=String(s).split('-').map(Number); return new Date(a[0],a[1]-1,a[2]); }
  function norm(d){ return new Date(d.getFullYear(),d.getMonth(),d.getDate()); }
  function same(a,b){ return a && b && a.getTime()===b.getTime(); }

  function applyVisual(){
    const cells = document.querySelectorAll('#calendar .cell');
    cells.forEach(c=>{
      c.classList.remove('selected','range');
      const dsAttr = c.dataset.date;
      if (!dsAttr) return;
      const ds = norm(parse(dsAttr));
      if (start && !end && same(ds,start)) c.classList.add('selected');
      if (start && end){
        if (ds>=start && ds<=end) c.classList.add('range');
        if (same(ds,start) || same(ds,end)) c.classList.add('selected');
      }
    });
  }

  function tapDate(dsStr){
    let d = norm(parse(dsStr));
    if (!start || (start && end)){ start=d; end=null; }
    else {
      if (d < start){ end=start; start=d; }
      else if (same(d,start)){ end=null; }
      else { end=d; }
    }
    applyVisual();
    if (typeof updateBookingSummary==='function'){ try{ updateBookingSummary(start,end); }catch(e){} }
  }

  const cal = document.getElementById('calendar');
  if (!cal) return;

  cal.addEventListener('click', (e)=>{
    const cell = e.target.closest('.cell');
    if (!cell) return;
    e.preventDefault(); e.stopPropagation();
    tapDate(cell.dataset.date);
  }, {passive:false});

  cal.addEventListener('touchend', (e)=>{
    const cell = e.target.closest('.cell');
    if (!cell) return;
    e.preventDefault(); e.stopPropagation();
    tapDate(cell.dataset.date);
  }, {passive:false});

  ['prev','next'].forEach(id=>{
    const el = document.getElementById(id);
    if (!el) return;
    el.setAttribute('type','button');
    el.addEventListener('click',(e)=>{
      e.preventDefault(); e.stopPropagation();
      if (id==='prev') { try{ monthOffset--; }catch(_){} }
      if (id==='next') { try{ monthOffset++; }catch(_){} }
      if (typeof renderCalendar==='function') renderCalendar();
      setTimeout(applyVisual,0);
    }, {passive:false});
  });

  setTimeout(applyVisual,0);
})();

// == mobile-fix-any-data-date ==
// Event delegation: იმუშავე ნებისმიერ ელემენტზე, რომელსაც აქვს data-date
(function(){
  const cal = document.getElementById('calendar');
  if (!cal) return;

  function parseDateStr(s){
    if(!s) return null;
    const a = String(s).split('-').map(Number);
    if (a.length!==3) return null;
    return new Date(a[0], a[1]-1, a[2]);
  }
  function norm(d){ return new Date(d.getFullYear(), d.getMonth(), d.getDate()); }
  function same(a,b){ return a && b && a.getTime()===b.getTime(); }

  let start = null, end = null;

  function applyVisual(){
    const nodes = cal.querySelectorAll('[data-date]');
    nodes.forEach(c=>{
      c.classList && (c.classList.remove('selected','range'));
      const ds = c.getAttribute('data-date'); if(!ds) return;
      const d = norm(parseDateStr(ds));
      if (start && !end && same(d,start)) c.classList && c.classList.add('selected');
      if (start && end){
        if (d>=start && d<=end) c.classList && c.classList.add('range');
        if (same(d,start) || same(d,end)) c.classList && c.classList.add('selected');
      }
    });
  }

  function tap(ds){
    const d = norm(parseDateStr(ds)); if(!d) return;
    if (!start || (start && end)) { start=d; end=null; }
    else {
      if (d < start) { end=start; start=d; }
      else if (same(d,start)) { end=null; }
      else { end=d; }
    }
    applyVisual();
    if (typeof updateBookingSummary==='function'){ try{ updateBookingSummary(start,end); }catch(e){} }
  }

  function handler(e){
    const t = e.target.closest('[data-date]');
    if (!t) return;
    e.preventDefault(); e.stopPropagation();
    tap(t.getAttribute('data-date'));
  }

  cal.addEventListener('click', handler, {passive:false});
  cal.addEventListener('touchend', handler, {passive:false});
})();
