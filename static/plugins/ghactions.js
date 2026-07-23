let ghactions_json = null;
const DEFAULT_HOURS = 168;
const DEFAULT_LIMIT = 15;  // top N items
const DEFAULT_GROUP = "name"; // Group workflows by name or path
const DEFAULT_OTHERS_GHA = "(other projects)";
const DEFAULT_OTHERS_GHA_SINGLE = "(other builds)";
const DEFAULT_OTHERS_GHA_JOBS = "(other jobs)";
const DEFAULT_OTHERS_GHA_STEPS = "(other steps)";
async function seed_ghactions() {
    let qs = new URLSearchParams(document.location.hash);
    let qsnew = new URLSearchParams();
    if (qs.get("project")) qsnew.set("project", qs.get("project"));
    if (qs.get("hours")) qsnew.set("hours", qs.get("hours"));
    if (qs.get("limit")) qsnew.set("limit", qs.get("limit"));
    if (qs.get("group")) qsnew.set("group", qs.get("group"));
    if (qs.get("selfhosted")) qsnew.set("selfhosted", qs.get("selfhosted"));
    ghactions_json = await (await fetch(`/api/ghactions?${qsnew.toString()}`)).json();
    ghactions_json.all_projects.unshift("All projects");
    show_ghactions(qs.get("project"), parseInt(qs.get("hours")||DEFAULT_HOURS), parseInt(qs.get("limit")||DEFAULT_LIMIT), qs.get("group")||DEFAULT_GROUP, qs.get("selfhosted")||false);
}

async function render_dashboard_ghactions() {
    await OAuthGate(seed_ghactions);
}

function seconds_to_text(seconds) {
    const hours = Math.floor(seconds/3600);
    const minutes = Math.floor(seconds%3600/60);
    return `${hours}h${minutes}m`;
}

function setHash(project, hours, limit, group, selfhosted) {
    let newHash = "#ghactions";
    if (project) newHash += "&project=" + project;
    if (hours) newHash += "&hours=" + hours;
    if (limit) newHash += "&limit=" + limit;
    if (group) newHash += "&group=" + group;
    if (selfhosted) newHash += "&selfhosted=true";
    location.hash = newHash;
}


async function click_gha_project(params, old_project, hours, limit, group) {
    if (params && params.name && params.name !== DEFAULT_OTHERS_GHA && !old_project) { // If on global view and we click a project name, show only that project.
        setHash(params.name, hours, limit, group);
        await seed_ghactions();
    }
}

function add_gha_seconds(target, key, seconds) {
    if (!seconds) return;
    target[key] = (target[key] ? target[key] : 0) + seconds;
}

function gha_sorted_chart_values(values, topN, othersName) {
    const sorted = Object.entries(values)
        .map(([name, value]) => ({name, value}))
        .sort((a,b) => b.value-a.value);
    const top = sorted.slice(0, topN);
    if (top.length < sorted.length) {
        const topNames = new Set(top.map((x) => x.name));
        const otherValue = sorted.reduce((sum, item) => sum + (topNames.has(item.name) ? 0 : item.value), 0);
        top.push({
            name: othersName,
            value: otherValue,
            itemStyle: {color: "#999"}
        });
    }
    return top;
}

function gha_drilldown_button(text, onclick) {
    const button = document.createElement('button');
    button.type = "button";
    button.className = "btn btn-sm btn-secondary";
    button.style.margin = "4px";
    button.innerText = text;
    button.addEventListener('click', onclick);
    return button;
}

function gha_expand_chart_card(chart, height="640px", innerHeight="560px") {
    chart.style.maxWidth = "1240px";
    chart.style.height = height;
    chart.style.minHeight = height;
    chart.style.overflow = "visible";
    const inner = chart.firstElementChild;
    if (inner) {
        inner.style.height = innerHeight;
        inner.style.width = "1240px";
        const chartInstance = echarts.getInstanceByDom(inner);
        if (chartInstance) chartInstance.resize();
    }
    return chart;
}

function gha_warning(text) {
    const warning = document.createElement('div');
    warning.className = "alert alert-warning small";
    warning.style.maxWidth = "1240px";
    warning.style.marginTop = "8px";
    warning.innerText = text;
    return warning;
}

function gha_job_name_missing(job) {
    return !job.job_name;
}

function gha_job_step_signature(job) {
    const step_names = [];
    for (const step of job.steps || []) {
        const step_name = step[0];
        if (!step_name || step_name === "Set up job" || step_name === "Checkout" || step_name === "Complete job" || step_name.startsWith("Post ")) continue;
        step_names.push(step_name);
    }
    return step_names.join("\n") || "no recorded steps";
}

function gha_unknown_job_group_name(workflowData, job) {
    const signature = gha_job_step_signature(job);
    if (!workflowData.unknown_job_groups[signature]) {
        workflowData.unknown_job_groups[signature] = `Unnamed job group #${Object.keys(workflowData.unknown_job_groups).length + 1}`;
    }
    return workflowData.unknown_job_groups[signature];
}

function gha_job_display_name(workflowData, job) {
    if (!gha_job_name_missing(job)) return job.job_name;
    return gha_unknown_job_group_name(workflowData, job);
}

function show_gha_step_drilldown(target, workflowName, jobName, steps_by_time, topN, showWorkflowChart, showJobChart) {
    target.innerText = "";
    const step_values = gha_sorted_chart_values(steps_by_time, topN, DEFAULT_OTHERS_GHA_STEPS);
    const total_seconds = Object.values(steps_by_time).reduce((sum, val) => sum + val, 0);
    if (!total_seconds) {
        target.innerText = `No step timing data found for ${jobName}.`;
        return;
    }

    const nav = document.createElement('div');
    nav.appendChild(gha_drilldown_button("Back to workflows", showWorkflowChart));
    nav.appendChild(gha_drilldown_button("Back to jobs", showJobChart));
    target.appendChild(nav);

    const title = `Step Runtime Breakdown\n${workflowName}\n${jobName}`;
    const chart = chart_pie(title, "Summed step durations for this job. Step totals may not equal full job runtime because GitHub does not expose every runner overhead as a step.", step_values, {width: "1240px", height: "560px"}, donut=false,
        fmtoptions={
            value: (val) => `${val.data.name}: ${seconds_to_text(val.data.value)}`,
            legend: (val) => `${val.data.name}: \n${((val.data.value/total_seconds)*100).toFixed(2)}%`
        });
    target.appendChild(gha_expand_chart_card(chart));
}

function show_gha_job_drilldown(target, workflowName, workflowData, topN, showWorkflowChart) {
    target.innerText = "";
    const job_values = gha_sorted_chart_values(workflowData.jobs, topN, DEFAULT_OTHERS_GHA_JOBS);
    const total_seconds = Object.values(workflowData.jobs).reduce((sum, val) => sum + val, 0);
    if (!total_seconds) {
        target.innerText = `No job timing data found for ${workflowName}.`;
        return;
    }

    const showJobChart = () => show_gha_job_drilldown(target, workflowName, workflowData, topN, showWorkflowChart);
    const nav = document.createElement('div');
    nav.appendChild(gha_drilldown_button("Back to workflows", showWorkflowChart));
    target.appendChild(nav);
    if (workflowData.missing_job_names) {
        const group_count = Object.keys(workflowData.unknown_job_groups).length;
        target.appendChild(gha_warning(`${workflowData.missing_job_names} job record(s) do not include a GitHub job name. They are grouped by matching step names into ${group_count} "Unnamed job group #N" bucket(s).`));
    }

    const title = `Job Runtime Breakdown\n${workflowName}`;
    const chart = chart_pie(title, "Click a job to see its step runtime breakdown.", job_values, {width: "1240px", height: "560px"}, donut=false,
        fmtoptions={
            value: (val) => `${val.data.name}: ${seconds_to_text(val.data.value)}`,
            legend: (val) => `${val.data.name}: \n${((val.data.value/total_seconds)*100).toFixed(2)}%`
        }, legend=null, onclick=(params) => {
            if (params && params.name && params.name !== DEFAULT_OTHERS_GHA_JOBS) {
                show_gha_step_drilldown(target, workflowName, params.name, workflowData.steps[params.name] || {}, topN, showWorkflowChart, showJobChart);
            }
    });
    target.appendChild(gha_expand_chart_card(chart));
}

function show_ghactions(project, hours = DEFAULT_HOURS, topN = DEFAULT_LIMIT, group = DEFAULT_GROUP, selfhosted = false) {
    let project_txt = project ? project : "All projects";
    if (!project) group = DEFAULT_GROUP
    document.getElementById('page_title').innerText = `GitHub Actions Statistics, ${project_txt}`;
    document.getElementById('page_description').innerText = "This page shows the GitHub Actions usage for projects you are a part of. If you do not see any data here, your project is likely not using GitHub Actions. By default, builds on self-hosted runners are not included in the stats, but can be included by using the self-hosted checkbox field at the bottom.";
    const outer_chart_area = document.getElementById('chart_area');
    outer_chart_area.innerText = "";

    const cost_per_runner_minute_private = 0.01072
    const cost_per_runner_minute_public = 0.006341958
    const projects_by_time = {}
    const workflows_by_time = {}
    let total_seconds = 0;


    for (const build of ghactions_json.builds) {
        if (project && project !== build.project) continue
        if (project) {
            for (const job of build.jobs) {
                // Skip self-hosted job durations by setting them to 0 seconds, unless we mean to include them.
                let jd = job.job_duration;
                if (!selfhosted) {
                    for (const label of job.labels || []) {
                        if (label.includes("self-hosted")) jd = 0;
                    }
                }
                // Group by workflow name or the actions .yml file used
                const groupkey = (group === "name") ? job.name : (build.workflow_path||"unknown.yml");
                if (jd) {
                    add_gha_seconds(projects_by_time, groupkey, jd);
                    if (!workflows_by_time[groupkey]) workflows_by_time[groupkey] = {jobs: {}, steps: {}, missing_job_names: 0, unknown_job_groups: {}};
                    const workflow_data = workflows_by_time[groupkey];
                    const job_name = gha_job_display_name(workflow_data, job);
                    if (gha_job_name_missing(job)) workflow_data.missing_job_names++;
                    add_gha_seconds(workflows_by_time[groupkey].jobs, job_name, jd);
                    if (!workflows_by_time[groupkey].steps[job_name]) workflows_by_time[groupkey].steps[job_name] = {};
                    for (const step of job.steps || []) {
                        add_gha_seconds(workflows_by_time[groupkey].steps[job_name], step[0] || "Unknown step", step[2]);
                    }
                }
            }
        }
        else if (build.seconds_used) {
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
            name: project ? DEFAULT_OTHERS_GHA_SINGLE : DEFAULT_OTHERS_GHA,
            value: sumval,
            itemStyle: {
                color: "#999"
            }
        });
    }
    const legends = r_array.map((x) => x.name);

    const timetxt = hours > 24 ? Math.floor(hours/24) + " days" : hours + " hours";
    const chart_slot = document.createElement('div');
    const showWorkflowChart = () => {
        chart_slot.innerText = "";
        const chart_click = project ? (params) => {
            if (params && params.name && params.name !== DEFAULT_OTHERS_GHA_SINGLE) {
                show_gha_job_drilldown(chart_slot, params.name, workflows_by_time[params.name] || {jobs: {}, steps: {}}, topN, showWorkflowChart);
            }
        } : (params) => click_gha_project(params, project, hours, topN, group);
        const donut_recipients = chart_pie(`GitHub Actions Build Time Used, past ${timetxt}.\nTotal usage: ${Math.round(total_seconds/60).pretty()} minutes, or ${Math.round(total_seconds/(hours*3600))} FT runners. Estimated credit use: \$${(cost_per_runner_minute_public*total_seconds/60).pretty()}`, "", r_array_sorted, {width: "1240px", height: "500px"}, donut=false,
            fmtoptions={
                value: (val) => `${val.data.name}: ${seconds_to_text(val.data.value)}, or ${Math.round(val.data.value/(hours*3600))} FT runner(s)`,
                legend: (val) => `${val.data.name}: \n${((val.data.value/total_seconds)*100).toFixed(2)}%`
            }, legend=null, onclick=chart_click);
        donut_recipients.style.maxWidth = "1240px";
        donut_recipients.style.height = "500px";
        chart_slot.appendChild(donut_recipients);
    };
    showWorkflowChart();
    outer_chart_area.appendChild(chart_slot);

    // filters
    const hourpicker = document.createElement('select');
    hourpicker.style.marginRight = "20px";
    for (const val of [1, 2, 4, 8, 12, 24, 120, 168, 720]) {
        const opt = document.createElement('option');
        opt.value = val;
        opt.text = "Past " + (val > 24 ? Math.floor(val/24) + " days" : val + " hours");
        opt.selected = val === hours;
        hourpicker.appendChild(opt);
    }
    hourpicker.addEventListener('change', (e) => {
        hours = e.target.value;
        setHash(project, hours, topN, group, selfhosted);
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
        setHash(project, hours, topN, group, selfhosted);
        seed_ghactions();
    })

    outer_chart_area.appendChild(document.createElement('br'))
    outer_chart_area.appendChild(projectpicker)
    outer_chart_area.appendChild(hourpicker)
    outer_chart_area.appendChild(limitpicker)

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
        outer_chart_area.appendChild(groupby)
    }

    // include self-hosted? Only valid in single project view
    if (project) {
        const shcheck = document.createElement('input');
        shcheck.type = "checkbox";
        shcheck.id = "shosted";
        shcheck.checked = !! selfhosted;
        shcheck.addEventListener('change', (e) => {
            selfhosted = e.target.checked;
            setHash(project, hours, topN, group, selfhosted);
            seed_ghactions();
        });
        const lbl = document.createElement('label');
        lbl.setAttribute('for', 'shosted');
        lbl.innerText = "Include self-hosted runners";
        outer_chart_area.appendChild(shcheck);
        outer_chart_area.appendChild(lbl);
    }


}
