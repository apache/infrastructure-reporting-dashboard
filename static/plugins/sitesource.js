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
        source_url.href = data.git_url || data.svn_url;
        source_url.innerText = source_url.href || 'N/A';
        if (data.git_url
            && data.git_url.startsWith('https://gitbox.apache.org/repos/asf/')) {
            source_url.innerText = data.git_url.substr(36);
        }
        else if (data.svn_url) {
            if (data.svn_url.startsWith('https://svn-master.apache.org/repos/asf/'))
                source_url.innerText = data.svn_url.substr(40);
            else if (data.svn_url.startsWith('https://svn-master.apache.org/repos/infra/'))
                source_url.innerText = data.svn_url.substr(42);
        }

        const site_url = document.createElement('a');
        site_url.href = `https://${host}`;
        site_url.innerText = host;
        site_url.target = "_blank";

        const website = document.createElement('span');
        website.appendChild(site_url);
        if (data.attic) {
            const status = document.createElement('a');
            status.href = 'https://attic.apache.org/';
            status.innerText = 'retired';
            status.className = 'badge text-bg-warning link-underline link-underline-opacity-25 ms-2';
            website.appendChild(status);
        }

        const source = document.createElement('span');
        const vcs = document.createElement('b');
        if (data.git_url)
            vcs.innerText = 'git:';
        else if (!data.svn_url)
            vcs.innerText = 'NO URL';
        else if (data.svn_url.startsWith('https://svn-master.apache.org/repos/asf/'))
            vcs.innerText = 'svn/asf:';
        else if (data.svn_url.startsWith('http://svn-master.apache.org/repos/asf/'))
            vcs.innerText = 'svn/asf:';
        else if (data.svn_url.startsWith('https://svn-master.apache.org/repos/infra/'))
            vcs.innerText = 'svn/infra:';
        else
            vcs.innerText = 'UNKNOWN';
        vcs.style.display = 'inline-block';
        vcs.style.width = '5em';
        vcs.className = 'me-2';
        source.appendChild(vcs);

        source.appendChild(source_url);

        if (data.git_url) {
            const branch = document.createElement('span');
            branch.innerText = '[branch: ' + data.git_branch + ']';
            branch.className = 'ms-2';
            source.appendChild(branch);

            if (!uses_asfyaml) {
                const not_asfyaml = document.createElement('span');
                not_asfyaml.innerText = 'not .asf.yaml';
                not_asfyaml.className = 'badge text-bg-danger ms-2';
                source.appendChild(not_asfyaml);
            }
        }

        if (data.svn_url && data.svn_url.startsWith('http:')) {
            const not_https = document.createElement('span');
            not_https.innerText = 'not https';
            not_https.className = 'badge text-bg-warning ms-2';
            source.appendChild(not_https);
        }

        source_array.push([
            website,
            source,
            new Date(data.check_time*1000.0).toISOString()
        ])
    }
    const source_table = chart_table_list("ASF project website checker", ["Website", "Source", "Last Checked"], source_array);
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
