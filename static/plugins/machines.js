let machines_json = null;

async function seed_machines() {
    machines_json = await (await fetch("/api/machines")).json();
}

function split_once(str, splitter) {
    // split a string only once (String.split doesn't allow this)
    if (typeof str === "string") {
        const i = str.indexOf(splitter);
        if (i >= 0) {
          return [str.slice(0,i), str.slice(i+1)]
        }
    }
    return [str, null]
}

async function render_dashboard_machines() {
    document.getElementById('page_title').innerText = "Machine Fingerprints";
    if (!machines_json) await seed_machines();
 
    const outer_chart_area = document.getElementById('chart_area');
    outer_chart_area.innerHTML = machines_json['HTML'];
}
