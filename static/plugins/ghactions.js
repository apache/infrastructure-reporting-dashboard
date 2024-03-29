let ghactions_json = null;
const DEFAULT_HOURS = 168;
const DEFAULT_LIMIT = 15;  // top N items
const DEFAULT_GROUP = "name"; // Group workflows by name or path

async function seed_ghactions() {
    let qs = new URLSearchParams(document.location.hash);
    let qsnew = new URLSearchParams();
    if (qs.get("project")) qsnew.set("project", qs.get("project"));
    if (qs.get("hours")) qsnew.set("hours", qs.get("hours"));
    if (qs.get("limit")) qsnew.set("limit", qs.get("limit"));
    if (qs.get("group")) qsnew.set("group", qs.get("group"));
    ghactions_json = await (await fetch(`/api/ghactions?${qsnew.toString()}`)).json();
    ghactions_json.all_projects.unshift("All projects");
    show_ghactions(qs.get("project"), parseInt(qs.get("hours")||DEFAULT_HOURS), parseInt(qs.get("limit")||DEFAULT_LIMIT, qs.get("group")||DEFAULT_GROUP));
}

async function render_dashboard_ghactions() {
    await OAuthGate(seed_ghactions);
}

function seconds_to_text(seconds) {
    const hours = Math.floor(seconds/3600);
    const minutes = Math.floor(seconds%3600/60);
    return `${hours}h${minutes}m`;
}

function setHash(project, hours, limit, group) {
    let newHash = "#ghactions";
    if (project) newHash += "&project=" + project;
    if (hours) newHash += "&hours=" + hours;
    if (limit) newHash += "&limit=" + limit;
    if (group) newHash += "&group=" + group;
    location.hash = newHash;
}

function show_ghactions(project, hours = DEFAULT_HOURS, topN = DEFAULT_LIMIT, group = DEFAULT_GROUP) {
    let project_txt = project ? project : "All projects";
    if (!project) group = DEFAULT_GROUP
    document.getElementById('page_title').innerText = `GitHub Actions Statistics, ${project_txt}`;
    document.getElementById('page_description').innerText = "";
    const outer_chart_area = document.getElementById('chart_area');
    outer_chart_area.innerText = "";

    const cost_per_runner_minute_private = 0.01072
    const cost_per_runner_minute_public = 0.006341958
    const projects_by_time = {}
    let total_seconds = 0;


    for (const build of ghactions_json.builds) {
        if (project && project !== build.project) continue
        if (project) {
            for (const job of JSON.parse(build.jobs)) {
                // Group by workflow name or the actions .yml file used
                const groupkey = (group === "name") ? job.name : (ghactions_json.workflow_path||"unknown.yml");
                projects_by_time[groupkey] = (projects_by_time[groupkey] ? projects_by_time[groupkey] : 0) + job.job_duration
            }
        }
        else {
            projects_by_time[build.project] = (projects_by_time[build.project] ? projects_by_time[build.project] : 0) + build.seconds_used;
        }
        total_seconds += build.seconds_used;
    }

    const r_array = [];
    for (const [k,v] of Object.entries(projects_by_time)) {
        r_array.push({name: k, value: v});
    }
    const r_array_sorted = r_array.slice();
    r_array_sorted.sort((a,b) => b.value-a.value);
    r_array_sorted.splice(topN);
    if (r_array_sorted.length < r_array.length) {
        const sumval = r_array.reduce((psum, a) => (psum.value ? psum.value : psum) + (r_array_sorted.includes(a) ? 0 : a.value));
        r_array_sorted.push({
            name: "(other projects)",
            value: sumval,
            itemStyle: {
                color: "#999"
            }
        });
    }
    const legends = r_array.map((x) => x.name);

    const timetxt = hours > 24 ? Math.floor(hours/24) + " days" : hours + " hours";
    const donut_recipients = chart_pie(`GitHub Actions Build Time Used, past ${timetxt}.\nTotal usage: ${Math.round(total_seconds/60).pretty()} minutes, or ${Math.round(total_seconds/(hours*3600))} FT runners. Estimated credit use: \$${(cost_per_runner_minute_public*total_seconds/60).pretty()}`, "", r_array_sorted, {width: "1000px", height: "500px"}, donut=false,
        fmtoptions={
            value: (val) => `${val.data.name}: ${seconds_to_text(val.data.value)}, or ${Math.round(val.data.value/(hours*3600))} FT runner(s)`,
            legend: (val) => `${val.data.name}: \n${((val.data.value/total_seconds)*100).toFixed(2)}%`
        });
    donut_recipients.style.maxWidth = "1000px";
    donut_recipients.style.height = "500px";
    outer_chart_area.appendChild(donut_recipients);

    // filters
    const hourpicker = document.createElement('select');
    hourpicker.style.marginRight = "20px";
    for (const val of [1, 2, 4, 8, 12, 24, 168, 720]) {
        const opt = document.createElement('option');
        opt.value = val;
        opt.text = "Past " + (val > 24 ? Math.floor(val/24) + " days" : val + " hours");
        opt.selected = val === hours;
        hourpicker.appendChild(opt);
    }
    hourpicker.addEventListener('change', (e) => {
        hours = e.target.value;
        setHash(project, hours, topN, group);
        seed_ghactions();
    })

    const projectpicker = document.createElement('select');
    projectpicker.style.marginRight = "20px";
    for (const val of ghactions_json.all_projects) {
        const opt = document.createElement('option');
        opt.value = val;
        opt.text = val;
        opt.selected = project === val;
        projectpicker.appendChild(opt);
    }
    projectpicker.addEventListener('change', (e) => {
        let val = e.target.value;
        project = val.includes(" ") ? null : val;
        setHash(project, hours, topN, group);
        seed_ghactions();
    })

    const limitpicker = document.createElement('select');
    limitpicker.style.marginRight = "20px";
    for (const val of [10, 15, 20, 25, 30, 50]) {
        const opt = document.createElement('option');
        opt.value = val;
        opt.text = "Top " + val;
        opt.selected = val === topN;
        limitpicker.appendChild(opt);
    }
    limitpicker.addEventListener('change', (e) => {
        topN = e.target.value;
        setHash(project, hours, topN, group);
        seed_ghactions();
    })

    // This option is only available when viewing a single project
    if (project) {
        const groupby = document.createElement('select');
        groupby.style.marginRight = "20px";
        for (const val of ['name', 'path']) {
            const opt = document.createElement('option');
            opt.value = val;
            opt.text = "Group workflows by " + val;
            opt.selected = val === group;
            groupby.appendChild(opt);
        }
        groupby.addEventListener('change', (e) => {
            group = e.target.value;
            setHash(project, hours, topN, group);
            seed_ghactions();
        })
    }
    outer_chart_area.appendChild(document.createElement('br'))
    outer_chart_area.appendChild(projectpicker)
    outer_chart_area.appendChild(hourpicker)
    outer_chart_area.appendChild(limitpicker)
    outer_chart_area.appendChild(groupby)

}