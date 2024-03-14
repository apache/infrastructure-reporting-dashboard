let ghactions_json = null;
const DEFAULT_HOURS = 168;

async function seed_ghactions() {
    let qs = new URLSearchParams(document.location.hash);
    let qsnew = new URLSearchParams();
    if (qs.get("project")) qsnew.set("project", qs.get("project"));
    if (qs.get("hours")) qsnew.set("hours", qs.get("hours"));
    ghactions_json = await (await fetch(`/api/ghactions?${qsnew.toString()}`)).json();
    ghactions_json.all_projects.unshift("All projects");
    show_ghactions(qs.get("project"), qs.get("hours")||DEFAULT_HOURS);
}

async function render_dashboard_ghactions() {
    await OAuthGate(seed_ghactions);
}

function seconds_to_text(seconds) {
    const hours = Math.floor(seconds/3600);
    const minutes = Math.floor(seconds%3600/60);
    return `${hours}h${minutes}m`;
}

function show_ghactions(project, hours = DEFAULT_HOURS, topN = 12) {
    let project_txt = project ? project : "All projects";
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
                projects_by_time[job.name] = (projects_by_time[job.name] ? projects_by_time[job.name] : 0) + job.job_duration
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
    for (const val of [1, 2, 4, 8, 12, 24, 168, 720]) {
        const opt = document.createElement('option');
        opt.value = val;
        opt.text = val > 24 ? Math.floor(val/24) + " days" : val + " hours";
        opt.selected = val == hours ? true : false;
        opt.addEventListener('click', () => {
            if (project) location.hash = `#ghactions&project=${project}&hours=${val}`;
            else location.hash = `#ghactions&hours=${val}`;
            seed_ghactions();
        })
        hourpicker.appendChild(opt);
    }

    const projectpicker = document.createElement('select');
    for (const val of ghactions_json.all_projects) {
        const opt = document.createElement('option');
        opt.value = val;
        opt.text = val > 24 ? Math.floor(val/24) + " days" : val;
        opt.selected = project ? true : false;
        opt.addEventListener('click', () => {
            if (val.includes(" ")) {
                if (hours) location.hash = `#ghactions&hours=${hours}`;
                else location.hash = "#ghactions";
            }
            else {
                if (hours) location.hash = `#ghactions&project=${val}&hours=${hours}`;
                else location.hash = `#ghactions&project=${val}`;
            }
            seed_ghactions();
        })
        projectpicker.appendChild(opt);
    }

    outer_chart_area.appendChild(document.createElement('hr'))
    outer_chart_area.appendChild(hourpicker)
    outer_chart_area.appendChild(projectpicker)

}