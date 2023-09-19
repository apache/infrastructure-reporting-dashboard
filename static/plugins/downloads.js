
let cca2_list;

async function fetch_download_stats(prefs) {
    let qs = new URLSearchParams(document.location.hash);
    let project = qs.get("project");
    const outer_chart_area = document.getElementById('chart_area');
    if (!project || project.length < 2 || project.search(/[^-\/a-z0-9]+/) !== -1) {
        outer_chart_area.innerText = "Please enter a valid project name (for instance, netbeans) in the field above to fetch download statistics. For podling projects, you may need to add the 'incubator/' prefix, e.g. 'incubator/ponymail'."
        return
    }
    let duration = "60d";

    outer_chart_area.innerText = "Fetching data, please wait...";

    let download_stats = await (await fetch(`/api/downloads?project=${project}&duration=${duration}`)).json();
    show_download_stats(project, download_stats);
}

async function render_dashboard_downloads(project, duration="7d") {
    if (!cca2_list) cca2_list = await (await fetch("/_assets/cca2.json")).json();


    const pinput = document.createElement('input');
    pinput.placeholder = "Type a project name to search for...";
    pinput.addEventListener('keyup', (ev) => { if (ev.key === "Enter"){
        location.hash = `#downloads&project=${ev.target.value}`;
        fetch_download_stats();
    } });
    document.getElementById('page_description').innerText = "";
    document.getElementById('page_description').appendChild(pinput);
    document.getElementById('page_title').innerText = `Download Statistics`;


    await OAuthGate(fetch_download_stats);
}

function show_download_stats(project, stats_as_json) {
    if (!project || project === "") return

    document.getElementById('page_title').innerText = `Download Statistics for ${project}:`;
    const outer_chart_area = document.getElementById('chart_area');
    outer_chart_area.innerText = "";
    if (stats_as_json.success === false) {
        outer_chart_area.innerText = stats_as_json.message;
    }


    const total_downloads_histogram = {};
    const total_downloads_curated = {};
    const total_download_histogram_summed = {};
    const total_downloads_sum = {};
    const total_bytes_histogram = {};
    const total_bytes_curated = {};
    const total_bytes_histogram_summed = {};
    const total_bytes_sum = {};
    const uris = Object.keys(stats_as_json);

    let downloads_as_sum = 0;
    let bytes_as_sum = 0;
    let visitors_as_sum = 0;


    const all_days = [];
    for (const [uri, data] of Object.entries(stats_as_json)) {
        downloads_as_sum += data.hits;
        bytes_as_sum += data.bytes;
        visitors_as_sum += data.hits_unique;
        for (const entry of data.daily_stats) {
            if (!all_days.includes(entry[0])) all_days.push(entry[0]);
        }
    }
    all_days.sort();

    for (const [uri, data] of Object.entries(stats_as_json)) {
        total_downloads_histogram[uri] = [];
        total_bytes_histogram[uri] = [];
        for (const day of all_days) {
            let found_day = false;
            for (const entry of data.daily_stats) {
                if (entry[0] === day) {
                    total_downloads_histogram[uri].push([entry[0], entry[1]]);
                    total_downloads_sum[uri] = (total_downloads_sum[uri] || 0) + entry[1];
                    total_download_histogram_summed[day] = (total_download_histogram_summed[day] || 0) + entry[1];
                    total_bytes_histogram[uri].push([entry[0], entry[3]]);
                    total_bytes_sum[uri] = (total_bytes_sum[uri] || 0) + entry[3];
                    total_bytes_histogram_summed[day] = (total_bytes_histogram_summed[day] || 0) + entry[3];
                    found_day = true;
                    break
                }
            }
            if (!found_day) {
                total_downloads_histogram[uri].push([day, 0]);
                total_bytes_histogram[uri].push([day, 0]);
            }

        }
    }

    uris.sort((a,b) => total_downloads_sum[b] - total_downloads_sum[a]);
    const uris_top_downloads = uris.slice(0, 10);
    total_downloads_curated["Other files"] = [];
    for (const day of all_days) {
        let other_count = 0;
        for (const [uri, entry] of Object.entries(total_downloads_histogram)) {
            if (!uris_top_downloads.includes(uri)) { // Don't include top 10
                for (const el of entry) {
                    if (el[0] === day) {
                        other_count += el[1];
                    }
                }
            }
        }
        total_downloads_curated["Other files"].push([day, other_count]);
    }
    for (const uri of uris_top_downloads) {
        total_downloads_curated[uri] = total_downloads_histogram[uri];
    }

    console.log(total_downloads_curated)
    const total_downloads = chart_bar(
        `Downloads for ${project}, past two months`,
        "",
        total_downloads_curated,
        {
            height: "320px",
            width: "1500px"
        },
        true,
        true,
        {widelegend: true}
    );

    outer_chart_area.appendChild(total_downloads);


    uris.sort((a,b) => total_bytes_sum[b] - total_bytes_sum[a]);
    const uris_top_bytes = uris.slice(0, 10);
    total_bytes_curated["Other files"] = [];
    for (const day of all_days) {
        let other_count = 0;
        for (const [uri, entry] of Object.entries(total_bytes_histogram)) {
            if (!uris_top_bytes.includes(uri)) { // Don't include top 10
                for (const el of entry) {
                    if (el[0] === day) {
                        other_count += el[1];
                    }
                }
            }
        }
        total_bytes_curated["Other files"].push([day, other_count]);
    }
    for (const uri of uris_top_bytes) {
        total_bytes_curated[uri] = total_bytes_histogram[uri];
    }

    const total_bytes = chart_bar(
        `Downloads for ${project}, past two months, by traffic volume`,
        "",
        total_bytes_curated,
        {
            height: "320px",
            width: "1500px"
        },
        true,
        true,
        {binary: true, widelegend: true}
    );

    outer_chart_area.appendChild(total_bytes);


    const cca2_dict = {};
    const cca2_array = [];
    for (const [uri, data] of Object.entries(stats_as_json)) {
        for (const [cca2, count] of Object.entries(data.cca2)) {
            cca2_dict[cca2] = (cca2_dict[cca2]||0) + count;
        }
    }
    for (const [k,v] of Object.entries(cca2_dict)) {
        let cname = "??";
        for (const country of cca2_list) {
            if (country.cca2 == k) {
                cname = country.flag + " " + country.name;
            }
        }
        cca2_array.push({name: cname, value: v})
    }
    const cca2_array_sorted = cca2_array.slice();
    cca2_array_sorted.sort((a,b) => b.value-a.value);
    cca2_array_sorted.splice(20);
    if (cca2_array_sorted.length < cca2_array.length) {
        const sumval = cca2_array.reduce((psum, a) => (psum.value ? psum.value : psum) + (cca2_array_sorted.includes(a) ? 0 : a.value));
        cca2_array_sorted.push({
            name: "(other countries)",
            value: sumval,
            itemStyle: {
                color: "#999"
            }
        });
    }
    const donut_countries = chart_pie("Downloads by Country", "", cca2_array_sorted, {width: "720px", height: "340px"}, donut=true);
    donut_countries.style.maxWidth = "700px";
    donut_countries.style.height = "340px";
    outer_chart_area.appendChild(donut_countries);

    let total_hits = 0;

    let dlinfotable = {
        "Total downloads": downloads_as_sum.pretty(),
        "Total bytes transferred": bytes_as_sum.pretty(),
        "Unique user count": visitors_as_sum.pretty()
    };

    const infotable = chart_table("At a glance", null, dlinfotable);
    outer_chart_area.appendChild(infotable);

    outer_chart_area.appendChild(document.createElement('hr'));

    return

}

