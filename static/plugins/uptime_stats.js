let uptime_json = null;

async function seed_uptime_stats() {
    uptime_json = await (await fetch("/api/uptime")).json();
}

function ralign_pct(pct) {
    const span = document.createElement('span');
    span.innerText = `${pct.toFixed(2)}%`
    span.style.float = 'right';
    return span
}
async function render_dashboard_uptime(assignee, timespan) {
    if (!uptime_json) await seed_uptime_stats();
    document.getElementById('page_title').innerText = "Uptime Statistics";
    document.getElementById('page_description').innerText = "This is a general overview of the uptime statistics, as collected by our monitoring services. Global uptime figures are defined as the average uptime of all services within their respective service categories, or as a whole. On a monthly basis, we conduct nearly five million checks against our infrastructure, comprised of over 50 different service components and spread over more than 250 machines in data centers around the world. ";
    const outer_chart_area = document.getElementById('chart_area');
    outer_chart_area.innerText = "";

    const uptime_collated = {};
    for (const [service, data] of Object.entries(uptime_json.uptime_collated)) {
        uptime_collated[service] = data.monthly;
    }
    const uptime_chart = chart_line(
        "Uptime across service groups, past year",
        "",
        uptime_collated,
        {
            height: "455px",
            width: "1000px"
        }
    );
    outer_chart_area.appendChild(uptime_chart);

    const uptime_list = [];
    for (const [cat, data] of Object.entries(uptime_json.uptime_collated)) {
        uptime_list.push([cat, ralign_pct(data.average), ralign_pct(data.past_month), ralign_pct(data.past_week)]);
    }
    const uptime_table = chart_table_list("Uptime quick stats across service categories", ["Service category", "Uptime, past year", "Uptime, this month", "Uptime, past week"], uptime_list);
    uptime_table.style.height = "475px";
    outer_chart_area.appendChild(uptime_table);


}

seed_uptime_stats();
