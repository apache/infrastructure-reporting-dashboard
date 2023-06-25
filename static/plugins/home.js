async function render_home() {
    const page_title = document.getElementById('page_title');
    page_title.innerText = "ASF Infrastructure Reporting Dashboard";
    const page_description = document.getElementById('page_description');
    page_description.innerText = "Some intro about our stats here....and so on";

    const chart_area = document.getElementById('chart_area');
    chart_area.innerText = '';
}