let mailstats_json = null;

async function seed_mail_stats() {
    mailstats_json = await (await fetch("/api/mailstats")).json();
    show_mailstats("collated");
}

async function render_dashboard_mailstats() {
    await OAuthGate(seed_mail_stats);
}

function show_mailstats(hostname="collated") {
    document.getElementById('page_title').innerText = `Mail Transfer Statistics, ${hostname}`;
    document.getElementById('page_description').innerText = "This page is only available to infrastructure staff. If you see a blank chart, that is why.";
    const outer_chart_area = document.getElementById('chart_area');
    outer_chart_area.innerText = "";

    const hostselector = document.createElement('div');
    for (const hostoption of Object.keys(mailstats_json)) {
        const hostbox = document.createElement('input');
        hostbox.type = "radio";
        hostbox.checked = hostname === hostoption;
        hostbox.id = `hostoption_${hostoption}`;
        hostbox.name = "hostoption";
        hostbox.addEventListener('click', () => show_mailstats(hostoption));
        hostselector.appendChild(hostbox);
        const hostlabel = document.createElement('label');
        hostlabel.style.marginRight = "24px";
        hostlabel.className = "p-1"
        hostlabel.setAttribute('for', hostbox.id);
        hostlabel.innerText = hostoption;
        hostselector.appendChild(hostlabel);
    }
    outer_chart_area.appendChild(hostselector);
    outer_chart_area.appendChild(document.createElement('hr'));

    const pending_collated = [];
    const my_stats = mailstats_json[hostname];
    for (const entry of my_stats) {
        pending_collated.push([entry.ts, entry.pending]);
    }
    const queue_chart = chart_line(
        "Mail queue size, past day",
        null,
        {"Queue size": pending_collated},
        {
            height: "250px",
            width: "1200px"
        },
        true,
        true
    );
    outer_chart_area.appendChild(queue_chart);

    outer_chart_area.appendChild(document.createElement('hr'));

    // ---------- RECIPIENTS --------------

    // recipient domain breakdown
    const r_array = [];
    for (const [k,v] of Object.entries(my_stats[my_stats.length-1].pending_by_recipient)) {
        r_array.push({name: k, value: v});
    }
    const r_array_sorted = r_array.slice();
    r_array_sorted.sort((a,b) => b.value-a.value);
    r_array_sorted.splice(9);
    if (r_array_sorted.length < r_array.length) {
        const sumval = r_array.reduce((psum, a) => (psum.value ? psum.value : psum) + (r_array_sorted.includes(a) ? 0 : a.value));
        r_array_sorted.push({
            name: "(other domains)",
            value: sumval,
            itemStyle: {
                color: "#999"
            }
        });
    }
    const donut_recipients = chart_pie("Mail Queue by Recipient Domain", "", r_array_sorted, {width: "690px", height: "380px"}, donut=true);
    donut_recipients.style.maxWidth = "580px";
    donut_recipients.style.height = "380px";
    outer_chart_area.appendChild(donut_recipients);



    // timeline, recipients - only top 20
    let top_domains = {};
    let recipient_timeline_collated = {};
    let all_domains = [];
    for (const entry of my_stats.slice(my_stats.length-48, my_stats.length)) {
        for (const domain in entry.pending_by_recipient) {
            if (!all_domains.includes(domain)) all_domains.push(domain);
        }
    }

    for (const entry of my_stats.slice(my_stats.length-48, my_stats.length)) {
        for (const domain of all_domains) {
            const value = entry.pending_by_recipient[domain] || 0;
            top_domains[domain] = (top_domains[domain] || 0) + value;
            if (!recipient_timeline_collated[domain]) {
                recipient_timeline_collated[domain] = [];
            }
            recipient_timeline_collated[domain].push([entry.ts, value]);
        }
    }

    let top_domains_sorted = Object.keys(top_domains).sort((a,b) => top_domains[b]-top_domains[a]).slice(0,19);
    for (const domain in recipient_timeline_collated) {
        if (!top_domains_sorted.includes(domain)) delete recipient_timeline_collated[domain];
    }
    let rd_sorted_for_chart = {};
    for (const domain of top_domains_sorted) {
        rd_sorted_for_chart[domain] = recipient_timeline_collated[domain];
    }
    let recipient_timeline_chart = chart_bar(
        "Recipients over time, top 20 recipient domains",
        "",
        rd_sorted_for_chart,
        {
            height: "360px",
            width: "800px"
        },
        true,
        true
    );
    outer_chart_area.appendChild(recipient_timeline_chart);

    outer_chart_area.appendChild(document.createElement('hr'));

    // ------------------- SENDERS ---------------

    // sender domain breakdown
    const s_array = [];
    for (const [k,v] of Object.entries(my_stats[my_stats.length-1].pending_by_sender)) {
        s_array.push({name: k, value: v});
    }
    const s_array_sorted = s_array.slice();
    s_array_sorted.sort((a,b) => b.value-a.value);
    s_array_sorted.splice(9);
    if (s_array_sorted.length < s_array.length) {
        const sumval = s_array.reduce((psum, a) => (psum.value ? psum.value : psum) + (s_array_sorted.includes(a) ? 0 : a.value));
        s_array_sorted.push({
            name: "(other domains)",
            value: sumval,
            itemStyle: {
                color: "#999"
            }
        });
    }
    const donut_sender = chart_pie("Mail Queue by Sender Domain", "", s_array_sorted, {width: "690px", height: "380px"}, donut=true);
    donut_sender.style.maxWidth = "580px";
    donut_sender.style.height = "380px";
    outer_chart_area.appendChild(donut_sender);


    // timeline, sender domains - only top 20
    top_domains = {};
    let sender_timeline_collated = {};
    all_domains = [];
    for (const entry of my_stats.slice(my_stats.length-48, my_stats.length)) {
        for (const domain in entry.pending_by_sender) {
            if (!all_domains.includes(domain)) all_domains.push(domain);
        }
    }

    for (const entry of my_stats.slice(my_stats.length-48, my_stats.length)) {
        for (const domain of all_domains) {
            const value = entry.pending_by_sender[domain] || 0;
            top_domains[domain] = (top_domains[domain] || 0) + value;
            if (!sender_timeline_collated[domain]) {
                sender_timeline_collated[domain] = [];
            }
            sender_timeline_collated[domain].push([entry.ts, value]);
        }
    }

    top_domains_sorted = Object.keys(top_domains).sort((a,b) => top_domains[b]-top_domains[a]).slice(0,19);
    for (const domain in recipient_timeline_collated) {
        if (!top_domains_sorted.includes(domain)) delete sender_timeline_collated[domain];
    }
    const sd_sorted_for_chart = {};
    for (const domain of top_domains_sorted) {
        sd_sorted_for_chart[domain] = sender_timeline_collated[domain];
    }
    const sender_timeline_chart = chart_bar(
        "Sender domains over time, top 20 domains",
        "",
        sd_sorted_for_chart,
        {
            height: "360px",
            width: "800px"
        },
        true,
        true
    );
    outer_chart_area.appendChild(sender_timeline_chart);

}

