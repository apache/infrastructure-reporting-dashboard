const _root_style = document.querySelector(':root');

function set_sidebar_css() {
    const sidebar = document.getElementById('sidebar_left');
    const sidebar_width = Math.round(sidebar.getBoundingClientRect().width);
    _root_style.style.setProperty('--sidebar', `${sidebar_width}px`);
}

async function prime_page() {
    set_sidebar_css();
    if (document.location.hash.length > 1) {
        const pfunc = `render_dashboard_${document.location.hash.substring(1)}`;
        if (typeof window[pfunc] === "function") {
            console.log(`Running ${pfunc}`)
            await window[pfunc]();
        }
    } else {
        await render_home();
    }
}

window.addEventListener('load',prime_page);
window.addEventListener('resize', set_sidebar_css);