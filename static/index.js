// Dynamically load and display vehicles on the home page
async function loadFeaturedVehicles() {
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
document.addEventListener('DOMContentLoaded', loadFeaturedVehicles);
