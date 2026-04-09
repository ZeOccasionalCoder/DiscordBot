/* ============================================================
   Sea Worthy Clan Dashboard — Client-side JS
   ============================================================ */

document.addEventListener('DOMContentLoaded', () => {

    // ---- Generic tab handler ----
    function initTabs(tabSelector, panelSelector) {
        document.querySelectorAll(tabSelector).forEach(tab => {
            tab.addEventListener('click', () => {
                const group = tab.closest('.tab-group');
                if (!group) return;
                group.querySelectorAll(tabSelector).forEach(t => t.classList.remove('active'));
                group.querySelectorAll(panelSelector).forEach(p => p.classList.remove('active'));
                tab.classList.add('active');
                const target = document.getElementById(tab.dataset.target);
                if (target) target.classList.add('active');
            });
        });
    }

    initTabs('.gained-tab', '.gained-panel');
    initTabs('.mode-tab', '.mode-panel');

    // ---- Relative timestamps ----
    document.querySelectorAll('[data-timestamp]').forEach(el => {
        const ts = el.dataset.timestamp;
        if (!ts) return;
        const date = new Date(ts);
        const now = new Date();
        const diffMs = now - date;
        const diffMin = Math.floor(diffMs / 60000);
        const diffHr = Math.floor(diffMs / 3600000);
        const diffDay = Math.floor(diffMs / 86400000);

        let relative;
        if (diffMin < 1) relative = 'just now';
        else if (diffMin < 60) relative = `${diffMin}m ago`;
        else if (diffHr < 24) relative = `${diffHr}h ago`;
        else if (diffDay < 7) relative = `${diffDay}d ago`;
        else relative = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

        el.textContent = relative;
        el.title = date.toLocaleString();
    });

    // ---- Carousel ----
    document.querySelectorAll('.carousel-wrapper').forEach(wrapper => {
        const track = wrapper.querySelector('.carousel-track');
        const slides = wrapper.querySelectorAll('.carousel-slide');
        const prevBtn = wrapper.querySelector('.carousel-btn.prev');
        const nextBtn = wrapper.querySelector('.carousel-btn.next');
        const dotsContainer = wrapper.querySelector('.carousel-dots');
        let currentIndex = 0;
        const total = slides.length;

        if (total <= 1) {
            // Hide controls if only one slide
            if (prevBtn) prevBtn.style.display = 'none';
            if (nextBtn) nextBtn.style.display = 'none';
            if (dotsContainer) dotsContainer.style.display = 'none';
            return;
        }

        function goTo(index) {
            if (index < 0) index = total - 1;
            if (index >= total) index = 0;
            currentIndex = index;
            track.style.transform = `translateX(-${currentIndex * 100}%)`;
            // Update dots
            if (dotsContainer) {
                dotsContainer.querySelectorAll('.carousel-dot').forEach((dot, i) => {
                    dot.classList.toggle('active', i === currentIndex);
                });
            }
        }

        if (prevBtn) prevBtn.addEventListener('click', () => goTo(currentIndex - 1));
        if (nextBtn) nextBtn.addEventListener('click', () => goTo(currentIndex + 1));

        // Create dots
        if (dotsContainer) {
            for (let i = 0; i < total; i++) {
                const dot = document.createElement('div');
                dot.className = 'carousel-dot' + (i === 0 ? ' active' : '');
                dot.addEventListener('click', () => goTo(i));
                dotsContainer.appendChild(dot);
            }
        }

        // Auto-advance every 8 seconds
        setInterval(() => goTo(currentIndex + 1), 8000);
    });
});
