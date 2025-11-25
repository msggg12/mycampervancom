function getSlug() {
	const parts = window.location.pathname.split('/').filter(Boolean);
	return parts[1];
}

async function fetchVans() {
	const res = await fetch('/api/vans');
	return await res.json();
}

async function fetchAvailability(slug) {
	const res = await fetch(`/api/availability?slug=${encodeURIComponent(slug)}`);
	return await res.json();
}

async function fetchSite() {
	const res = await fetch('/api/site');
	return await res.json();
}

function dateToISO(d) { return d.toISOString().slice(0,10); }
function isoToDate(s) { const [y,m,d] = s.split('-').map(Number); return new Date(y, m-1, d); }

let monthOffset = 0;
let rangeStart = null;
let rangeEnd = null;
let currentBusy = [];
let currentPrice = 0;
let contactPhone = '';
let contactEmail = '';
let currentVan = null;
let stripePublic = '';

function addDays(d, n) { const x = new Date(d); x.setDate(x.getDate()+n); return x; }

function isBusyDate(d) {
	return currentBusy.some(r => {
		const start = isoToDate(r.start);
		const end = isoToDate(r.end);
		return d >= start && d < end;
	});
}

function isInRange(d) {
	if (!rangeStart || !rangeEnd) return false;
	return d >= rangeStart && d < rangeEnd;
}

function nightsBetween(a, bExclusive) {
	const ms = isoToDate(dateToISO(bExclusive)) - isoToDate(dateToISO(a));
	return Math.max(0, Math.round(ms / (1000*60*60*24)));
}

function updateBookingSummary() {
	const summary = document.getElementById('booking-summary');
	const total = document.getElementById('booking-total');
	const btn = document.getElementById('proceed');
	const waBtn = document.getElementById('whatsapp');
	const form = document.getElementById('booking-form');
	
	if (rangeStart && rangeEnd) {
		const nights = nightsBetween(rangeStart, rangeEnd);
		const checkoutInclusive = addDays(rangeEnd, -1);
		const grand = nights * currentPrice;
		summary.textContent = `${dateToISO(rangeStart)} → ${dateToISO(checkoutInclusive)} · ${nights} night${nights!==1?'s':''}`;
		form.style.display = 'block';
		const minNights = 3;
		if (nights < minNights) {
			// Enforce minimum nights
			total.textContent = '';
			btn.disabled = true; 
			waBtn.disabled = true;
			summary.textContent += ` · minimum ${minNights} nights`;
			summary.style.color = 'var(--danger)';
			btn.onclick = null;
			waBtn.onclick = null;
			return;
		} else {
			summary.style.color = '';
			total.textContent = `€${grand.toFixed(2)} total`;
			btn.disabled = false;
			waBtn.disabled = false;
		}
		
		const plain = `Hi! I'd like to book ${currentVan.name} (${currentVan.slug}) from ${dateToISO(rangeStart)} to ${dateToISO(checkoutInclusive)} (${nights} nights). Total: $${grand.toFixed(2)}`;
		
		btn.onclick = async () => {
			const status = document.getElementById('book-status');
			if (nights < 3) { status.textContent = 'Minimum 3 nights required (3+ nights).'; status.style.color = 'var(--danger)'; return; }
			const nameEl = document.getElementById('customer-name');
			const emailEl = document.getElementById('customer-email');
			const phoneEl = document.getElementById('customer-phone');
			const locEl = document.getElementById('customer-location');
			const notesEl = document.getElementById('customer-notes');
			const name = (nameEl?.value || '').trim();
			const email = (emailEl?.value || '').trim();
			const phone = (phoneEl?.value || '').trim();
			const location = (locEl?.value || '').trim();
			const notes = (notesEl?.value || '').trim();
			
			// Clear previous error styles
			[emailEl, locEl].forEach(el => { if (el) el.style.outline = ''; if (el) el.style.borderColor=''; });
			status.style.color = '';
			
			// Validate required fields: email and pickup location
			const errors = [];
			const emailOk = (email && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email));
			if (!email) { errors.push('Email is required.'); if (emailEl) { emailEl.style.outline = '2px solid var(--danger)'; emailEl.style.borderColor = 'var(--danger)'; } }
			else if (!emailOk) { errors.push('Enter a valid email address.'); if (emailEl) { emailEl.style.outline = '2px solid var(--danger)'; emailEl.style.borderColor = 'var(--danger)'; } }
			if (!location) { errors.push('Pickup location is required.'); if (locEl) { locEl.style.outline = '2px solid var(--danger)'; locEl.style.borderColor = 'var(--danger)'; } }
			if (errors.length) {
				status.textContent = errors.join(' ');
				status.style.color = 'var(--danger)';
				return;
			}
			
			status.textContent = 'Sending booking request...';
			status.style.color = '';
			try {
				// Build equipment list string from currentVan.equipment if available
				const equipmentList = Array.isArray(currentVan.equipment) && currentVan.equipment.length ? currentVan.equipment.map(i => `• ${i}`).join('\n') : '';

				const res = await fetch('/api/book', { 
					method: 'POST', 
					headers: { 'Content-Type': 'application/json' }, 
					body: JSON.stringify({ 
						slug: currentVan.slug, 
						start: dateToISO(rangeStart), 
						end: dateToISO(rangeEnd), 
						nights, 
						total: grand, 
						email,
						name,
						phone,
						notes,
						location,
						// Additional info for email confirmation
						emailConfirmation: {
							to: email,
							subject: `Booking Confirmation - ${currentVan.name}`,
							details: {
								customerName: name,
								vanName: currentVan.name,
								checkIn: dateToISO(rangeStart),
								checkOut: dateToISO(checkoutInclusive),
								nights,
								total: grand.toFixed(2),
								pickupLocation: location,
								equipmentList,
								customerPhone: phone,
								specialNotes: notes
							}
						}
					}) 
				});
				const data = await res.json();
				if (data.ok) { 
					status.textContent = 'Booking request sent successfully! We\'ll contact you soon.';
					// Clear form
					document.getElementById('customer-name').value = '';
					document.getElementById('customer-email').value = '';
					document.getElementById('customer-phone').value = '';
					document.getElementById('customer-notes').value = '';
					const locEl = document.getElementById('customer-location'); if (locEl) locEl.selectedIndex = 0;
				} else { 
					status.textContent = 'Error: ' + (data.error || 'Failed to send request'); 
				}
			} catch (e) { 
				status.textContent = 'Network error. Please try again.'; 
			}
		};
		
		waBtn.onclick = () => {
			const status = document.getElementById('book-status');
			if (nights < 3) { status.textContent = 'Minimum 3 nights required (3+ nights).'; status.style.color = 'var(--danger)'; return; }
			const nameEl = document.getElementById('customer-name');
			const emailEl = document.getElementById('customer-email');
			const phoneEl = document.getElementById('customer-phone');
			const locEl = document.getElementById('customer-location');
			const notesEl = document.getElementById('customer-notes');
			const name = (nameEl?.value || '').trim();
			const email = (emailEl?.value || '').trim();
			const phone = (phoneEl?.value || '').trim();
			const location = (locEl?.value || '').trim();
			const notes = (notesEl?.value || '').trim();
			
			// Clear previous error styles
			[emailEl, locEl].forEach(el => { if (el) el.style.outline = ''; if (el) el.style.borderColor=''; });
			status.style.color = '';
			
			const errors = [];
			const emailOk = (email && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email));
			if (!email) { errors.push('Email is required.'); if (emailEl) { emailEl.style.outline = '2px solid var(--danger)'; emailEl.style.borderColor = 'var(--danger)'; } }
			else if (!emailOk) { errors.push('Enter a valid email address.'); if (emailEl) { emailEl.style.outline = '2px solid var(--danger)'; emailEl.style.borderColor = 'var(--danger)'; } }
			if (!location) { errors.push('Pickup location is required.'); if (locEl) { locEl.style.outline = '2px solid var(--danger)'; locEl.style.borderColor = 'var(--danger)'; } }
			if (errors.length) {
				status.textContent = errors.join(' ');
				status.style.color = 'var(--danger)';
				return;
			}
			
			let message = `Hi! I'd like to book ${currentVan.name} (${currentVan.slug}) from ${dateToISO(rangeStart)} to ${dateToISO(checkoutInclusive)} (${nights} nights). Total: €${grand.toFixed(2)}`;
			if (name) message += `\n\nName: ${name}`;
			if (email) message += `\nEmail: ${email}`;
			if (phone) message += `\nPhone: ${phone}`;
			if (location) message += `\nPickup location: ${location}`;
			if (notes) message += `\nNotes: ${notes}`;
			const msg = encodeURIComponent(message);
			const raw = (contactPhone || '').replace(/[^0-9+]/g, '');
			const phoneNum = raw.startsWith('+') ? raw.slice(1) : raw;
			const url = `https://api.whatsapp.com/send?${phoneNum ? 'phone=' + encodeURIComponent(phoneNum) + '&' : ''}text=${msg}`;
			window.open(url, '_blank');
		};
	} else if (rangeStart) {
		summary.textContent = `Check‑in: ${dateToISO(rangeStart)}. Select check‑out.`;
		total.textContent = '';
		form.style.display = 'block';
		btn.disabled = true; waBtn.disabled = true; btn.onclick = null; waBtn.onclick = null;
	} else {
		summary.textContent = 'Select check‑in and check‑out on the calendar';
		total.textContent = '';
		form.style.display = 'block';
		btn.disabled = true; waBtn.disabled = true; btn.onclick = null; waBtn.onclick = null;
	}
}

function renderCalendar() {
	const cal = document.getElementById('calendar');
	const monthLabel = document.getElementById('month');
	cal.innerHTML = '';
	const now = new Date();
	const base = new Date(now.getFullYear(), now.getMonth() + monthOffset, 1);
	const end = new Date(base.getFullYear(), base.getMonth()+1, 0);
	monthLabel.textContent = base.toLocaleString(undefined, { month: 'long', year: 'numeric' });
	const startDay = new Date(base);
	startDay.setDate(1 - ((startDay.getDay() + 6) % 7)); // Monday start
	const totalDays = 42; // 6 weeks view
	for (let i=0;i<totalDays;i++) {
		const d = new Date(startDay);
		d.setDate(startDay.getDate() + i);
		const busy = isBusyDate(d);
		const inMonth = d.getMonth()===base.getMonth();
		const div = document.createElement('div');
		div.className = 'cell ' + (busy ? 'busy' : 'free') + (inMonth ? '' : ' dim') + (isInRange(d) ? ' selected' : '');
		div.textContent = String(d.getDate());
		div.addEventListener('click', () => {
			if (!inMonth || busy) return;
			if (!rangeStart || (rangeStart && rangeEnd)) {
				rangeStart = d; rangeEnd = null;
			} else if (d <= rangeStart) {
				rangeStart = d; rangeEnd = null;
			} else {
				let ok = true; const temp = new Date(rangeStart);
				while (temp < d) { if (isBusyDate(temp)) { ok = false; break; } temp.setDate(temp.getDate()+1); }
				if (ok) rangeEnd = addDays(d, 1); else { rangeStart = d; rangeEnd = null; }
			}
			renderCalendar();
			updateBookingSummary();
		});
		cal.appendChild(div);
	}
}

function setActiveThumb(url) {
	try {
		const target = new URL(url, window.location.origin).pathname;
		document.querySelectorAll('#gallery .thumbs-img').forEach(im => {
			const p = new URL(im.src, window.location.origin).pathname;
			im.classList.toggle('active', p === target);
		});
	} catch {}
}

function renderGallery(van) {
	const strip = document.getElementById('gallery');
	if (!strip) return;
	strip.innerHTML = '';
	const photos = (Array.isArray(van.photos) && van.photos.length) ? van.photos : (van.imageUrl ? [van.imageUrl] : []);
	
	// Only show gallery if more than 1 photo
	const container = strip.closest('.gallery-container');
	if (photos.length <= 1) {
		container.style.display = 'none';
		return;
	}
	container.style.display = 'block';
	
	// Decide layout: grid for 5 or fewer photos, slider for more
	const useSlider = photos.length > 5;
	if (useSlider) {
		strip.classList.add('slider-mode');
	} else {
		strip.classList.remove('slider-mode');
	}
	
	photos.forEach(url => {
		const img = document.createElement('img');
		img.src = url;
		img.alt = van.name;
		img.className = 'thumbs-img';
		img.addEventListener('click', () => {
			document.getElementById('van-image').src = url;
			setActiveThumb(url);
		});
		strip.appendChild(img);
	});
	
	// Highlight active thumbnail
	const main = document.getElementById('van-image')?.src;
	if (main) setActiveThumb(main);

	// Wire navigation buttons - only for slider mode
	const prevBtn = document.getElementById('gallery-prev');
	const nextBtn = document.getElementById('gallery-next');
	if (prevBtn && nextBtn) {
		if (useSlider) {
			prevBtn.style.display = 'flex';
			nextBtn.style.display = 'flex';
			
			const scrollAmount = 128; // width + gap
			prevBtn.onclick = () => {
				strip.scrollBy({ left: -scrollAmount, behavior: 'smooth' });
			};
			nextBtn.onclick = () => {
				strip.scrollBy({ left: scrollAmount, behavior: 'smooth' });
			};
			
			// Hide/show nav buttons based on scroll position
			function updateNavButtons() {
				prevBtn.style.opacity = strip.scrollLeft > 0 ? '1' : '0.3';
				nextBtn.style.opacity = strip.scrollLeft < (strip.scrollWidth - strip.clientWidth) ? '1' : '0.3';
			}
			
			updateNavButtons();
			strip.addEventListener('scroll', updateNavButtons);
		} else {
			// Hide navigation buttons in grid mode
			prevBtn.style.display = 'none';
			nextBtn.style.display = 'none';
		}
	}
}

(async function init() {
	const slug = getSlug();
	const vans = await fetchVans();
	currentVan = vans.find(v => v.slug === slug);
	if (!currentVan) { document.getElementById('van-name').textContent = 'Not found'; return; }
	// Use plain name without emojis
	document.getElementById('van-name').textContent = currentVan.name;
	const initial = (Array.isArray(currentVan.photos) && currentVan.photos.length ? currentVan.photos[0] : currentVan.imageUrl);
	document.getElementById('van-image').src = initial;
	renderGallery(currentVan);
	const phoneElInit = document.getElementById('customer-phone');
	if (phoneElInit) { phoneElInit.addEventListener('input', () => { phoneElInit.value = phoneElInit.value.replace(/[^0-9]/g, ''); }); }
	// Auto-slide photos on all vans
	try {
		const photos = (Array.isArray(currentVan.photos) && currentVan.photos.length) ? currentVan.photos : (currentVan.imageUrl ? [currentVan.imageUrl] : []);
		if (photos.length > 1) {
			let autoIdx = 1; // start from second photo since first is already shown
			const mainEl = document.getElementById('van-image');
			const strip = document.getElementById('gallery');
			
			function advance() {
				const url = photos[autoIdx];
				if (mainEl) mainEl.src = url;
				setActiveThumb(url);
				try {
					const thumb = Array.from(strip?.querySelectorAll?.('.thumbs-img') || []).find(im => {
						return new URL(im.src, window.location.origin).pathname === new URL(url, window.location.origin).pathname;
					});
					if (thumb && strip && strip.classList.contains('slider-mode')) {
						thumb.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
					}
				} catch {}
				autoIdx = (autoIdx + 1) % photos.length;
			}
			
			let timer = setInterval(advance, 2000);
			
			// Pause on hover over gallery or main image
			const container = document.querySelector('.gallery-container');
			[mainEl, strip, container].filter(Boolean).forEach(el => {
				el.addEventListener('mouseenter', () => { if (timer) { clearInterval(timer); timer = null; } });
				el.addEventListener('mouseleave', () => { if (!timer) { timer = setInterval(advance, 2000); } });
			});
			
			// When user clicks a thumbnail, show it and continue sliding from that photo
			strip?.addEventListener('click', (e) => {
				const im = e.target?.closest?.('.thumbs-img');
				if (!im) return;
				try {
					const path = new URL(im.src, window.location.origin).pathname;
					const idx = photos.findIndex(u => new URL(u, window.location.origin).pathname === path);
					if (idx !== -1) {
						// Ensure main image and active thumb reflect the clicked photo
						if (mainEl) mainEl.src = photos[idx];
						setActiveThumb(photos[idx]);
						// Next auto step should be the image after the clicked one
						autoIdx = (idx + 1) % photos.length;
					}
					// Restart the timer so it continues automatically
					if (timer) { clearInterval(timer); }
					timer = setInterval(advance, 2000);
				} catch {}
			});
		}
	} catch {}
	   document.getElementById('van-price').textContent = `€${(currentVan.pricePerNight||0)} / night`;
	   document.getElementById('van-meta').textContent = '';
	   const el = document.getElementById('van-desc');
	   if (el) {
		// Prefer structured equipment list on the van; fallback to description
		if (Array.isArray(currentVan.equipment) && currentVan.equipment.length) {
			el.innerHTML = '<strong>Equipped with</strong><ul>' + currentVan.equipment.map(i => `<li>${i}</li>`).join('') + '</ul>';
		} else {
			const desc = currentVan.description || currentVan.desc || '';
			el.textContent = desc;
		}
		// Apply custom font size if provided (e.g., '16px')
		if (currentVan.descriptionFontSize) {
			try { el.style.fontSize = currentVan.descriptionFontSize; } catch(e) {}
		}
	   }
	currentPrice = currentVan.pricePerNight || 0;
	const site = await fetchSite();
	contactPhone = (site && site.contact && site.contact.whatsapp) || '';
	contactEmail = (site && site.contact && site.contact.email) || '';
	stripePublic = (site && site.stripe && site.stripe.publicKey) || '';
	const data = await fetchAvailability(slug);
	currentBusy = data.busy || [];
	renderCalendar();
	document.getElementById('prev').addEventListener('click', (e) => { e.preventDefault(); e.stopImmediatePropagation(); monthOffset--; renderCalendar && renderCalendar(); });
	document.getElementById('next').addEventListener('click', (e) => { e.preventDefault(); e.stopImmediatePropagation(); monthOffset++; renderCalendar && renderCalendar(); });
	updateBookingSummary();
})();


// == mobile-fix: prevent jump on mobile and select start on first tap ==
(function(){
  if (window.__calendarMobileFixBound) return;
  window.__calendarMobileFixBound = true;

  function parseDateStr(s){
    if(!s) return null;
    var a = String(s).split('-').map(Number);
    if (a.length !== 3) return null;
    return new Date(a[0], a[1]-1, a[2]);
  }
  function ymd(d){ return [d.getFullYear(), ('0'+(d.getMonth()+1)).slice(-2), ('0'+d.getDate()).slice(-2)].join('-'); }
  function cmp(a,b){ return a.getTime()-b.getTime(); }
  function normalize(d){ return new Date(d.getFullYear(), d.getMonth(), d.getDate()); }

  var start = null, end = null;

  function applyVisual(){
    var cells = document.querySelectorAll('#calendar .cell');
    cells.forEach(function(c){
      c.classList.remove('selected','range');
      var ds = parseDateStr(c.dataset.date);
      if (!ds) return;
      ds = normalize(ds);
      if (start && !end && ds.getTime() === start.getTime()) {
        c.classList.add('selected');
      }
      if (start && end) {
        if (ds >= start && ds <= end) c.classList.add('range');
        if (ds.getTime() === start.getTime() || ds.getTime() === end.getTime()) {
          c.classList.add('selected');
        }
      }
    });
  }

  function handleDayTap(dateStr){
    var d = parseDateStr(dateStr);
    if (!d) return;
    d = normalize(d);

    if (!start || (start && end)) {
      start = d; end = null;
    } else {
      if (d < start) { end = start; start = d; }
      else if (d.getTime() === start.getTime()) { end = null; } 
      else { end = d; }
    }
    applyVisual();
    if (typeof updateBookingSummary === 'function') {
      try { updateBookingSummary(start, end); } catch(e){}
    }
  }

  var cal = document.getElementById('calendar');
  if (!cal) return;

  cal.addEventListener('click', function(e){
    var cell = e.target.closest('.cell');
    if (!cell) return;
    e.preventDefault(); e.stopImmediatePropagation();
    handleDayTap(cell.dataset.date);
  }, {passive:false});

  cal.addEventListener('touchend', function(e){
    var cell = e.target.closest('.cell');
    if (!cell) return;
    e.preventDefault(); e.stopImmediatePropagation();
    handleDayTap(cell.dataset.date);
  }, {passive:false});

  ['prev','next'].forEach(function(id){
    var el = document.getElementById(id);
    if (!el) return;
    el.setAttribute('type','button');
    el.addEventListener('click', function(e){
      e.preventDefault(); e.stopImmediatePropagation();
      if (id==='prev') { try{ monthOffset--; }catch(_){} }
      if (id==='next') { try{ monthOffset++; }catch(_){} }
      if (typeof renderCalendar === 'function') renderCalendar();
      // re-apply selection after re-render
      setTimeout(applyVisual, 0);
    }, {passive:false});
  });

  // initial paint
  setTimeout(applyVisual, 0);
})();

