let site_source_json = null;

async function seed_site_source() {
    site_source_json = await (await fetch("/api/sitesource")).json();
}

async function render_dashboard_sitesource(assignee, timespan) {
    if (!site_source_json) await seed_site_source();
    document.getElementById('page_title').innerText = "Site Source Checker";
    document.getElementById('page_description').innerText = "This page monitors the sources of all ASF project websites. Sites with any fields marked in red or yellow are not currently being updated. The colored field will indicate the reason for this.";
    const outer_chart_area = document.getElementById('chart_area');
    outer_chart_area.innerText = "";

    const filterfield = document.createElement('input');
    filterfield.type = "text";
    filterfield.placeholder = "Type here to filter on hostname...";
    filterfield.style.display = "block";
    filterfield.style.width = "280px";
    filterfield.style.marginLeft = "10px";
    outer_chart_area.appendChild(filterfield);

    const source_array = [];
    for (const [host, data] of Object.entries(site_source_json)) {
        const asfyaml = document.createElement('span');
        const uses_asfyaml = data.git_url ? !!data.asfyaml : null;
        if (uses_asfyaml === true) {
            asfyaml.innerText = "Yes";
        } else if (uses_asfyaml === false) {
            asfyaml.innerText = "No";
            asfyaml.className = "text-danger";
        } else if (uses_asfyaml === null) {
            asfyaml.innerText = "N/A";
            asfyaml.className = "text-muted";
        }

        const source_url = document.createElement('a');
        if (data.git_url || data.svn_url) source_url.href = data.git_url ? data.git_url : data.svn_url;
        source_url.innerText = data.git_url ? data.git_url : data.svn_url||"N/A";

        const site_url = document.createElement('a');
        site_url.href = `https://${host}`;
        site_url.innerText = host;
        site_url.target = "_blank";

        const retired = document.createElement('span');
        retired.innerText = data.attic ? "Yes" : "No";
        retired.className = data.attic ? "text-warning" : "text-muted";

        source_array.push([
            site_url,
            retired,
            data.git_url ? "Git" : "Subversion",
            source_url,
            data.git_branch || "N/A",
            asfyaml,
            new Date(data.check_time*1000.0).toISOString()
        ])
    }
    const source_table = chart_table_list("ASF project website checker", ["Website", "Retired?", "Source Type", "Source URL", "Branch", "Uses .asf.yaml?", "Last Checked"], source_array);
    source_table.style.width = "100%";
    outer_chart_area.appendChild(source_table);

    filterfield.addEventListener('keyup', () => {
        for (const tr of source_table.getElementsByTagName('tr')) {
            if (tr.firstChild.nodeName === "TH") continue; // Don't hide headers
            if (tr.firstChild.innerText.match(filterfield.value)) {
                tr.style.display = "table-row";
            } else {
                tr.style.display = "none";
            }
        }
    });


}
