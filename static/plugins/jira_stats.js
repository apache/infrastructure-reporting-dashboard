let jira_json = null;
let jira_panel = null;
const ticket_status_enum = [
    "Infra",
    "User",
    "Planned"
];

const ticket_status_colors = ['primary', 'warning', 'secondary'];

function ticket_to_row(data) {
    // Converts a ticket data entry to a row in the 'open tickets' table
    let ticket_status = 0; // Default to WFI
    if (data.paused) ticket_status = 1; // WFU, paused
    if (data.issuetype === "Planned Work") ticket_status = 2; // Planned work, paused


    const hours_spent_wfi = Math.round(data.sla_time_counted/3600);
    let response_time = Math.round(data.response_time/3600);
    if (!data.first_response) response_time = Math.round(data.sla_time_counted/3600);

    let response_time_text = "N/A";
    let resolve_time_text = "N/A";
    if (data.sla && ticket_status != 2) {  // Disregard planned work
        response_time_text = `${response_time} / ${data.sla.respond} hours`
        resolve_time_text = `${hours_spent_wfi} / ${data.sla.resolve} hours`
    }

    const response_time_div = document.createElement('div');
    response_time_div.className = (data.sla_met_respond === false && ticket_status !== 2) ? 'badge text-danger' : 'badge bg-transparent';
    response_time_div.innerText = response_time_text;
    response_time_div.style.width = "120px";

    const resolve_time_div = document.createElement('div');
    resolve_time_div.className = (data.sla_met_resolve === false && ticket_status !== 2) ? 'badge text-danger' : 'badge bg-transparent';
    resolve_time_div.innerText = resolve_time_text;
    resolve_time_div.style.width = "120px";

    const title_cell = document.createElement('a');
    title_cell.className = "text-truncate"
    title_cell.href = data.url;
    title_cell.target = "_blank";
    title_cell.innerText = `${data.key}: ${data.summary}`;
    title_cell.style.overflow = "hidden";
    title_cell.style.whiteSpace = "nowrap";
    title_cell.style.textOverflow = "ellipsis";

    title_cell.style.maxWidth = "calc(100vw - 590px - var(--sidebar))";
    title_cell.style.display = "inline-block";
    title_cell.title = data.summary;

    const status_div = document.createElement('div');
    status_div.style.height = "100%";
    status_div.style.minWidth = "100px";
    status_div.style.maxWidth = "7vw";
    status_div.className = `badge px-1 text-bg-${ticket_status_colors[ticket_status]}`;
    status_div.innerText = ticket_status_enum[ticket_status];
    return [
        ticket_status,
        status_div,
        title_cell,
        response_time_div,
        resolve_time_div,
        data.assignee || "Unassigned"
    ];
}

async function seed_jira_stats() {
    jira_json = await (await fetch("/api/jira?action=stats")).json();
    const outer_chart_area = document.getElementById('chart_area');
    outer_chart_area.innerText = "";

    // Top 10 folks, past three months
    const d = new Date();
    const now = d.getTime()/1000;
    d.setDate(d.getDate()-30);
    const deadline = d.getTime()/1000;

    const top10 = {};
    for (const [key, data] of Object.entries(jira_json)) {
        if (!data.created_at) continue // No creation date, invalid data
        if (data.assignee && data.created_at >= deadline) {
            top10[data.assignee] = top10[data.assignee] ? top10[data.assignee]+1 : 1;
        }
    }
    let toplist = Object.keys(top10);
    toplist.sort((a,b) => top10[b]-top10[a]);
    toplist.splice(10);

    let navitems = {
        undefined: "(Everyone)"
    };

    Object.assign(navitems, Object.fromEntries(toplist.map(x => [x,x])));

    const [navmenu, chart_area] = navtab(
        navitems,
        (val) => render_jira_stats(val)
    );
    outer_chart_area.appendChild(navmenu);
    outer_chart_area.appendChild(chart_area);
    jira_panel = chart_area;
    render_jira_stats();
}

function render_jira_stats(assignee, timespan) {
    jira_panel.innerText = ''; // Clear charts

    // Ensure the parameters are usable
    if (!timespan) timespan = 30;
    if (assignee === 'undefined') assignee = undefined

    // Init breakdown dict
    const jira_breakdown = {
        issues_opened: 0,
        issues_responded_to: 0,
        issues_resolved: 0,
        issues_touched: 0,
        total_time_respond: 0,
        total_time_resolve: 0,
        longest_time_respond: 0,
        longest_time_resolve: 0,
        priority_changes: 0,
        resolved_within_sla: 0,
        responded_within_sla: 0,
        fully_done_within_sla: 0,
        failed_sla: 0,
        failed_sla_fixtime: 0,
        open_issues: 0,
        unassigned_issues: 0,
        priorities: {}
    };

    // Grab cutoff date for stats. Any ticket older than this will not be counted
    const d = new Date();
    const now = d.getTime()/1000;
    d.setDate(d.getDate()-timespan);
    const deadline = d.getTime()/1000;

    // Process all tickets, compile stats
    const my_ticket_list = [];
    for (const [key, data] of Object.entries(jira_json)) {
        if (!data.key) data.key = `INFRA-${key}`;
        if (!data.created_at) continue // No creation date, invalid data
        if (data.closed && (!data.closed_at || data.closed_at < deadline)) continue  // Closed before this timespan
        if (assignee && data.assignee !== assignee) continue  // Viewing assignee and this isn't assigned to them
        if (data.closed === true) jira_breakdown.issues_resolved++;
        if (data.created_at >= deadline) jira_breakdown.issues_opened++;
        if (data.closed === true && data.resolve_time) jira_breakdown.total_time_resolve += data.resolve_time;
        if (data.response_time) {
            jira_breakdown.total_time_respond += data.response_time;
            jira_breakdown.issues_responded_to++;
        }
        if (data.closed || data.created_at >= deadline) jira_breakdown.issues_touched++;  // closed or opened in this timespan

        // sla stats
        if (data.sla && data.issuetype !== "Planned Work") {
            const sla_fix_time = data.sla.resolve * 3600; // Max time to close within SLA
            const sla_respond_time = data.sla.respond * 3600; // Max time to respond within SLA
            let n = 0; // if n === 2, then both response and resolve was within SLA limits
            if (data.closed && data.resolve_time <= sla_fix_time) { n++; jira_breakdown.resolved_within_sla++; }
            if (data.response_time && data.response_time <= sla_respond_time) { n++; jira_breakdown.responded_within_sla++; }
            if (n === 2) jira_breakdown.fully_done_within_sla++;
            else if (data.closed === false && data.sla_time_counted > sla_fix_time) { jira_breakdown.failed_sla++; jira_breakdown.failed_sla_fixtime++;}
            else if (data.closed && data.response_time > sla_respond_time) { jira_breakdown.failed_sla++}
        }

        if (data.priority) {
            jira_breakdown.priorities[data.priority] = jira_breakdown.priorities[data.priority] ? jira_breakdown.priorities[data.priority]+1:1;
        }

        // If open ticket, add to bottom table
        if (data.closed === false) {
            jira_breakdown.open_issues++;
            if (!data.assignee) jira_breakdown.unassigned_issues++;
            my_ticket_list.push(ticket_to_row(data));
        }
    }

    // Title and description
    const page_title = document.getElementById('page_title');
    page_title.innerText = assignee ? `Jira Handling Statistics for ${assignee}` : "Global Jira Handling Statistics";
    page_title.innerText += `, past ${timespan} days`

    const page_description = document.getElementById('page_description');
    page_description.innerText = "Some intro about Jira stats here....and so on";


    const total_progress = chart_progress(
        "Tickets handled fully in time",
        `${jira_breakdown.fully_done_within_sla} tickets were fully handled within SLA limits, out of a total of \
        ${jira_breakdown.fully_done_within_sla + jira_breakdown.failed_sla} tickets that were either closed in time \
        or failed one or more SLA deadlines.`,
        jira_breakdown.fully_done_within_sla,
        jira_breakdown.fully_done_within_sla + jira_breakdown.failed_sla,
        {
            height: "270px",
            width: "320px"
        }
    );
    jira_panel.appendChild(total_progress);

    const respond_progress = chart_progress(
        "Tickets responded to in time",
        `${jira_breakdown.responded_within_sla} tickets were responded to within SLA limits, out of a total of \
        ${jira_breakdown.issues_responded_to} tickets that were either responded to or failed to meet the \
        response deadline set in the SLA guidelines.`,
        jira_breakdown.responded_within_sla,
        jira_breakdown.issues_responded_to,
        {
            height: "270px",
            width: "320px"
        }
    );
    jira_panel.appendChild(respond_progress);

    const resolved_progress = chart_progress(
        "Tickets resolved in time",
        `${jira_breakdown.resolved_within_sla} tickets were resolved within SLA limits, out of a total of \
        ${jira_breakdown.resolved_within_sla + jira_breakdown.failed_sla} tickets that were either resolved in time \
        or failed to be resolved within the SLA deadlines.`,
        jira_breakdown.resolved_within_sla,
        jira_breakdown.resolved_within_sla + jira_breakdown.failed_sla,
        {
            height: "270px",
            width: "320px"
        }
    );

    jira_panel.appendChild(resolved_progress);

    const breakdown = [];
    for (const [k,v] of Object.entries(jira_breakdown.priorities)) {
        breakdown.push({
            value: v,
            name: k
        });
    }
    const pie_breakdown = chart_pie(
        "Priority Breakdown",
        "This shows the breakdown of tickets that were interacted with, and their priority levels",
        breakdown,
        {
            height: "260px",
            width: "360px"
        }
        );
    jira_panel.appendChild(pie_breakdown);

    const infotable = {};
    infotable[assignee ? "New issues assigned to self" : "Issues created"] = jira_breakdown.issues_opened;
    infotable["Issues responded to"] = jira_breakdown.issues_responded_to;
    infotable["Average time to respond"] = Math.round(jira_breakdown.total_time_respond/jira_breakdown.issues_responded_to/3600) + " hours";
    infotable["Issues resolved"] = jira_breakdown.issues_resolved;
    infotable["Average time to resolve"] = Math.round(jira_breakdown.total_time_resolve/jira_breakdown.issues_resolved/3600) + " hours";
    const introtable = chart_table("Quick Stats", null, infotable);

    jira_panel.appendChild(introtable);

    my_ticket_list.sort((a, b) => {
        if (a.at(-1) === 'Unassigned') {
            if (b.at(-1) !== 'Unassigned') return -1
            if (a[0] === b[0]) return b[2].innerText.localeCompare(a[2].innerText)
            return a[0]-b[0] // reverse priority: WFI, WFU, Planned
        } else if (b.at(-1) === 'Unassigned') return 1
        else if (a.at(-1) === b.at(-1)) {
            if (a[0] === b[0]) return b[2].innerText.localeCompare(a[2].innerText)
            return a[0]-b[0] // reverse priority: WFI, WFU, Planned
        }
        return a.at(-1).localeCompare(b.at(-1))
    })
    for (const item of my_ticket_list) {
        item.shift(); // remove integer status
    }
    const tbl_title = assignee ? `Currently open tickets (${jira_breakdown.open_issues})` : `Currently open tickets (${jira_breakdown.open_issues}, ${jira_breakdown.unassigned_issues} unassigned)`;
    const open_tickets = chart_table_list(
        tbl_title,
        ["Waiting for", "Ticket", "Time to respond", "Time to resolve", "Assignee"],
        my_ticket_list
    )
    open_tickets.style.width = "100%";
    jira_panel.appendChild(open_tickets);

}

function render_dashboard_jira() {
    seed_jira_stats();
}


