const _root_style = document.querySelector(':root');
let worldJson;

function set_sidebar_css() {
    const sidebar = document.getElementById('sidebar_left');
    const sidebar_width = Math.round(sidebar.getBoundingClientRect().width);
    _root_style.style.setProperty('--sidebar', `${sidebar_width}px`);
}

async function prime_page() {
    set_sidebar_css();
    await OAuthGate(null, true);
    worldJson = await (await fetch("/_assets/world.json")).json();
    if (document.location.hash.length > 1) {
        const paction = document.location.hash.substring(1).match(/[-_a-z0-9]+/)[0];
        const pfunc = `render_dashboard_${paction}`;
        if (typeof window[pfunc] === "function") {
            console.log(`Running ${pfunc}`)
            await window[pfunc]();
        }
    } else {
        await render_home();
    }
}

// Basic check for whether sessionStorage is supported or not
function sessionStorageSupported() {
    try {
        const storage = window.sessionStorage;
        storage.setItem('test', 'test');
        storage.removeItem('test');
        return true;
    } catch (e) {
        return false;
    }
}

// Simple UUID generator for debugging and oauth requests
function uuid() {
    return Math.random().toString(20).substring(2, 8)
        + Math.random().toString(20).substring(2, 8)
        + Math.random().toString(20).substring(2, 8);
}


async function OAuthGate(callback, oauth_optional=false) {
    const QSDict = new URLSearchParams(document.location.search);
    if (QSDict.get('action') === 'oauth') { // OAuth callback?
        const OAuthResponse = await fetch(`/api/oauth?${QSDict.toString()}`);
        if (OAuthResponse.status === 200) {
            if (sessionStorageSupported()) {
                const OriginURL = window.sessionStorage.getItem('ird_origin');
                // Do we have a stored URL to redirect back to, now that OAuth worked?
                if (OriginURL) {
                    window.sessionStorage.removeItem('ird_origin');
                    document.location.href = OriginURL;
                }
                return;
            }
        } else {
            // Something went wrong. For now, just spit out the response as an alert.
            alert(await OAuthResponse.text());
        }
    }
    if (oauth_optional) return
    const session = await fetch('/api/session');
    if (session.status === 403) { // No session set for this client yet, run the oauth process
        if (sessionStorageSupported()) {
            window.sessionStorage.setItem('ird_origin', document.location.href); // Store where we came from
        }
        // Construct OAuth URL and redirect to it
        const state = uuid();
        const OAuthURL = encodeURIComponent(`https://${document.location.hostname}/?action=oauth&state=${state}`);
        document.location.href = `https://oauth.apache.org/oauth-oidc?redirect_uri=${OAuthURL}&state=${state}`;
    } else if (session.status === 200) { // Found a working session
        const preferences = await session.json();
        const ue = document.getElementById('useremail');
        const um = document.getElementById('usermenu');
        if (ue) ue.innerText = `${preferences.uid}@apache.org`;
        if (um) um.style.display = "block";
        if (callback) callback(preferences, QSDict);
    } else { // Something went wrong on the backend, spit out the error msg
        alert(await session.text());
    }
}

window.addEventListener('load',prime_page);
window.addEventListener('resize', set_sidebar_css);