
let cca2_list;

async function fetch_download_stats(prefs) {
    let qs = new URLSearchParams(document.location.hash);
    let project = qs.get("project");
    const outer_chart_area = document.getElementById('chart_area');
    if (!project || project.length < 2 || project.search(/[^-\/a-z0-9]+/) !== -1) {
        outer_chart_area.innerText = "Please enter a valid project name (for instance, netbeans) in the field above to " +
            "fetch download statistics. For podling projects, you may need to add the 'incubator/' prefix, e.g. " +
            "'incubator/ponymail'. Due to caching, new data may take up to two hours to show in the charts."
        return
    }
    let duration = "60d"; // TODO: Make configurable

    outer_chart_area.innerText = "Fetching data, please wait...";

    let download_stats = await (await fetch(`/api/downloads?project=${project}&duration=${duration}`)).json();
    show_download_stats(project, download_stats, duration);
}

// dict_to_pie: Converts a dictionary to a sorted array, collating "others" if limit is exceeded
function dict_to_pie(dict, limit=10) {
    const keys = Object.keys(dict);
    keys.sort((a,b) => { return dict[b] - dict[a]});
    const keys_top = keys.slice(0,limit);
    const pie_array = [];
    let others = 0;
    for (const key of keys) {
        if (key !== "Other" && keys_top.includes(key)) pie_array.push({name: key, value: dict[key]});
        else others += dict[key];
    }
    if (others > 0) { // were there any others?
        pie_array.push({name: "Other", value: others});
    }
    return pie_array.sort((a,b) => b.value - a.value)
}

async function render_dashboard_downloads(project, duration="7d") {
    if (!cca2_list) cca2_list = await (await fetch("/_assets/cca2.json")).json();


    const pinput = document.createElement('input');
    pinput.placeholder = "project or incubator/podling";
    pinput.size = 25; // ensure hint is not truncated
    pinput.style.display = "block";
    pinput.addEventListener('keyup', (ev) => { if (ev.key === "Enter"){
        location.hash = `#downloads&project=${ev.target.value}`;
        fetch_download_stats();
    } });
    document.getElementById('page_description').innerText = "";
    document.getElementById('page_description').appendChild(pinput);
    document.getElementById('page_title').innerText = `Download Statistics`;
    await OAuthGate(fetch_download_stats);
}

function show_download_stats(project, stats_as_json, duration="7d", target_uri="") {
    if (!project || project === "") return
    if (target_uri === "") target_uri = null;

    document.getElementById('page_title').innerText = `Download Statistics for ${project}:`;
    const outer_chart_area = document.getElementById('chart_area');
    outer_chart_area.innerText = "";

    if (stats_as_json.success === false) {
        outer_chart_area.innerText = stats_as_json.message;
        return
    }

    const current_stats = {};

    if (Object.values(stats_as_json).some(x => x.downscaled === true)) {
        const note = document.createElement("div");
        note.innerText = "Note: Due to the high number of different user agents downloading files for this project, the user agent breakdown has been simplified in order to provide these statistics.";
        note.style.color = "orange";
        document.getElementById('page_description').appendChild(note);
    }
    for (let [uri, data] of Object.entries(stats_as_json)) {
        if (uri.length > 72) uri = uri.substring(0, 34) + "[...]" + uri.substring(uri.length-34, uri.length);
        if (!target_uri || target_uri === uri) current_stats[uri] = data;
    }

    const total_downloads_histogram = {};
    const total_downloads_curated = {};
    const total_download_histogram_summed = {};
    const total_downloads_sum = {};
    const total_bytes_histogram = {};
    const total_bytes_curated = {};
    const total_bytes_histogram_summed = {};
    const total_bytes_sum = {};
    const total_by_browser = {};
    const total_by_system = {};
    const uris = Object.keys(current_stats);

    let downloads_as_sum = 0;
    let bytes_as_sum = 0;
    let visitors_as_sum = 0;


    const all_days = [];
    for (const [uri, data] of Object.entries(current_stats)) {
        downloads_as_sum += data.hits;
        bytes_as_sum += data.bytes;
        visitors_as_sum += data.hits_unique;
        for (const entry of data.daily_stats) {
            if (!all_days.includes(entry[0])) all_days.push(entry[0]);
        }
    }
    all_days.sort();

    for (const [uri, data] of Object.entries(current_stats)) {
        total_downloads_histogram[uri] = [];
        total_bytes_histogram[uri] = [];
        for (const [key, val] of Object.entries(data.useragents)) {
            const [os, browser] = key.split(" / ", 2);
            total_by_browser[browser] = (total_by_browser[browser]||0) + val;
            total_by_system[os] = (total_by_system[os]||0) + val;
        }
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
    const uris_top_downloads = uris.slice(0, 30);
    if (!target_uri) {
        total_downloads_curated["Other files"] = [];
        let other_count_total = 0;
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
            other_count_total += other_count;
        }
        if (other_count_total == 0) {
            delete total_downloads_curated["Other files"];
        }
    }
    for (const uri of uris_top_downloads) {
        total_downloads_curated[uri] = total_downloads_histogram[uri];
    }

    // Drop-down selector for URIs
    const uri_filter = document.createElement('select');
    const uris_combined = document.createElement('option');
    uris_combined.innerText = "(show statistics for all top URIs)";
    uris_combined.value = "";
    uri_filter.appendChild(uris_combined);
    uri_filter.style.display = "block";
    const uris_single = document.createElement('option');
    uris_single.innerText = "Individual URIs:";
    uris_single.disabled = true;
    uri_filter.appendChild(uris_single);

    for (let [uri, data] of Object.entries(stats_as_json)) {
        const opt = document.createElement('option');
        if (uri.length > 72) uri = uri.substring(0, 34) + "[...]" + uri.substring(uri.length-34, uri.length);
        opt.innerText = `${uri} - (${data.hits.pretty()} downloads / ${data.bytes.pretty()} bytes)`;
        opt.value = uri;
        if (target_uri && target_uri.length && target_uri === uri) opt.selected = true;
        uri_filter.appendChild(opt);
    }
    uri_filter.addEventListener('change', (ev) => { show_download_stats(project, stats_as_json, duration, ev.target.value)})
    outer_chart_area.appendChild(uri_filter);

    const total_downloads = chart_bar(
        `Downloads, past two months`,
        "",
        total_downloads_curated,
        {
            height: "300px",
            width: "1500px"
        },
        true,
        true,
        {widelegend: target_uri ? false : true}
    );

    outer_chart_area.appendChild(total_downloads);


    uris.sort((a,b) => total_bytes_sum[b] - total_bytes_sum[a]);
    const uris_top_bytes = uris.slice(0, 30);
    if (!target_uri) {
        total_bytes_curated["Other files"] = [];
        let other_count_total = 0;
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
            other_count_total += other_count;
        }
        if (other_count_total == 0) {
            delete total_bytes_curated["Other files"];
        }
    }
    for (const uri of uris_top_bytes) {
        total_bytes_curated[uri] = total_bytes_histogram[uri];
    }

    const total_bytes = chart_bar(
        `Downloads, past two months, by traffic volume`,
        "",
        total_bytes_curated,
        {
            height: "300px",
            width: "1500px"
        },
        true,
        true,
        {binary: true, widelegend: target_uri ? false : true}
    );

    outer_chart_area.appendChild(total_bytes);

    outer_chart_area.appendChild(document.createElement('hr'));


    const cca2_dict = {};
    const cca2_array = [];
    const cca2_array_plain = [];  // for echarts world map
    for (const [uri, data] of Object.entries(current_stats)) {
        for (const [cca2, count] of Object.entries(data.cca2)) {
            cca2_dict[cca2] = (cca2_dict[cca2]||0) + count;
        }
    }
    for (const [k,v] of Object.entries(cca2_dict)) {
        let cname = "??";
        for (const country of cca2_list) {
            if (country.cca2 == k) {
                cname = country.flag + " " + country.name;
                cca2_array.push({name: cname, value: v})
                cca2_array_plain.push({name: country.name, value: v});
                break
            }
        }
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
    const donut_countries = chart_pie("Downloads by Country", "", cca2_array_sorted, {width: "720px", height: "400px"}, donut=true);
    donut_countries.style.maxWidth = "600px";
    donut_countries.style.height = "400px";
    outer_chart_area.appendChild(donut_countries);

    const wmap = chart_map("Downloads by Country", "", cca2_array_plain);
    outer_chart_area.appendChild(wmap);

    let total_hits = 0;

    const jsonlink = document.createElement('a');
    jsonlink.href = `/api/downloads?project=${project}&duration=${duration}`;
    jsonlink.innerText = "Raw JSON data";

    let dlinfotable = {
        "Total downloads": downloads_as_sum.pretty(),
        "Total bytes transferred": bytes_as_sum.pretty(),
        "Unique user count": visitors_as_sum.pretty(),
        "Raw data": jsonlink,
        "Daily stats entries": '[timestamp, downloads, unique ips, bytes]'
    };

    const infotable = chart_table("At a glance", null, dlinfotable);
    outer_chart_area.appendChild(infotable);

    // Downloads by browser and operating system
    outer_chart_area.appendChild(document.createElement('hr'));
    const donut_os = chart_pie("Downloads by Operating System", "This chart shows the distribution of downloads based on the users' operating systems as reported by the browser. The chart only reflects the top 50 most downloaded artifacts.", dict_to_pie(total_by_system), {width: "720px", height: "400px"}, donut=true);
    donut_os.style.maxWidth = "600px";
    donut_os.style.height = "460px";
    outer_chart_area.appendChild(donut_os);
    const donut_browser = chart_pie("Downloads by Browser", "This chart shows the distribution of downloads based on the users' browser clients as reported by the browser. The chart only reflects the top 50 most downloaded artifacts.", dict_to_pie(total_by_browser), {width: "720px", height: "400px"}, donut=true);
    donut_browser.style.maxWidth = "600px";
    donut_browser.style.height = "460px";
    outer_chart_area.appendChild(donut_browser);

}

