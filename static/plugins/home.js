async function render_home() {
    const page_title = document.getElementById('page_title');
    page_title.innerText = "ASF Infrastructure Reporting Dashboard";
    const page_description = document.getElementById('page_description');
    page_description.innerText = "This site contains a collection of reports on the overall health and activity of the infrastructure at the ASF. \
    Some reports are open to the public, while others are restricted to those that genuinely need them. If you cannot access a report, chances are \
    you are not supposed to. Use the menu on the left hand side to pick a report to display.";

    const chart_area = document.getElementById('chart_area');
    chart_area.innerText = '';
}