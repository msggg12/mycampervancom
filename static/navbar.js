// Navbar hide on scroll
(function() {
	let lastScrollTop = 0;
	let scrollThreshold = 100; // Start hiding after scrolling 100px
	const navbar = document.querySelector('.navbar');
	if (!navbar) return;

	// Hide-on-scroll behavior
	window.addEventListener('scroll', function() {
		let scrollTop = window.pageYOffset || document.documentElement.scrollTop;
		if (scrollTop > scrollThreshold && scrollTop > lastScrollTop) {
			navbar.classList.add('hidden');
		} else {
			navbar.classList.remove('hidden');
		}
		lastScrollTop = scrollTop <= 0 ? 0 : scrollTop;
	}, false);

	// Simple hamburger: show/hide stacked nav on mobile
	const inner = navbar.querySelector('.navbar-inner');
	const nav = navbar.querySelector('.nav');
	if (inner && nav) {
		let button = navbar.querySelector('.hamburger');
		if (!button) {
			button = document.createElement('button');
			button.type = 'button';
			button.className = 'hamburger';
			button.setAttribute('aria-label', 'Toggle navigation');
			button.setAttribute('aria-expanded', 'false');
			button.innerHTML = '<span class="bars"></span>';
			inner.appendChild(button);
		}

		function syncForViewport() {
			if (window.innerWidth <= 768) {
				// mobile: collapse by default
				nav.classList.toggle('open', false);
				button.classList.toggle('active', false);
				button.style.display = 'inline-flex';
				button.setAttribute('aria-expanded', 'false');
			} else {
				// desktop: show nav and hide button
				nav.classList.remove('open');
				button.classList.remove('active');
				button.style.display = 'none';
				button.setAttribute('aria-expanded', 'false');
			}
		}

		button.addEventListener('click', function(e){
			e.stopPropagation();
			const isOpen = !nav.classList.contains('open');
			nav.classList.toggle('open', isOpen);
			button.classList.toggle('active', isOpen);
			button.setAttribute('aria-expanded', String(isOpen));
		});

		// Close when clicking outside
		document.addEventListener('click', function(e){
			if (window.innerWidth > 768) return;
			if (!nav.classList.contains('open')) return;
			if (!inner.contains(e.target)) {
				nav.classList.remove('open');
				button.classList.remove('active');
				button.setAttribute('aria-expanded', 'false');
			}
		});

		// Close after navigating
		Array.from(nav.querySelectorAll('a')).forEach(function(a){
			a.addEventListener('click', function(){
				if (window.innerWidth <= 768) {
					nav.classList.remove('open');
					button.classList.remove('active');
					button.setAttribute('aria-expanded', 'false');
				}
			});
		});

		window.addEventListener('resize', syncForViewport);
		syncForViewport();
	}
})();

