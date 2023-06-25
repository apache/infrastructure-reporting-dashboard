function navtab(navitems, callback) {
    const navid = Math.round(Math.random()*10000000).toString(16);
    const nav_outer = document.createElement('nav');
    const navbar = document.createElement('div');
    navbar.className = "nav nav-tabs";
    navbar.setAttribute('role', 'tablist');
    let buttons = [];
    let n = 0;
    for (const [key, value] of Object.entries(navitems)) {
        const btn = document.createElement('button');
        btn.className = "nav-link";
        btn.id = `nav-tab-${key}`;
        btn.setAttribute('bs-toggle', 'tab');
        btn.setAttribute('bs-target', `#nav-${navid}`);
        btn.type = "button";
        btn.innerText = value;
        if (n === 0) {  // First el is active
            btn.className = "nav-link active selected";
            btn.ariaSelected = true;
        }
        n++;
        btn.addEventListener('click', () => {
            if (callback(key, value) !== false) {
                for (const xbtn of buttons) {
                    if (xbtn.innerText !== value) {
                        xbtn.className = "nav-link";
                        xbtn.ariaSelected = false;
                    } else {
                        xbtn.className = "nav-link active selected";
                        xbtn.ariaSelected = true;
                    }
                }
            }
        });
        buttons.push(btn);
        navbar.appendChild(btn);
    }

    nav_outer.appendChild(navbar);

    const contents = document.createElement('div');
    contents.className = "tab-content";
    const pane = document.createElement('div');
    pane.className = "tab-pane fade show active";
    pane.id = `nav-${navid}`
    pane.setAttribute('role', 'tabpanel');
    contents.appendChild(pane);


    return [nav_outer, contents]
}
