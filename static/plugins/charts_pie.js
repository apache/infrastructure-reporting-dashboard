function chart_pie(title, description, values, styles, donut=false, fmtoptions = null, legend = null, onclick=null) {
    const chartdiv = document.createElement('div');
    chartdiv.style.width = "500px";
    chartdiv.style.height = "300px";
    chartdiv.style.display = "inline-block";
    if (styles) {
        for (const [k,v] of Object.entries(styles)) {
            chartdiv.style.setProperty(k, v);
        }
    }
    const chart_pie_option = {
        backgroundColor: sys_theme === 'dark' ? "#212529" : "#0000",
        animation: false,
        title: {
            text: title ? title : "",
            left: 'center',
        },
        tooltip: {
            trigger: 'item',
            formatter: (fmtoptions && fmtoptions.value) ? (val) => fmtoptions.value(val) : '{b} : {c} ({d}%)',
        },
        legend: {
            orient: 'vertical',
            left: 0,
            top: 'center',
            data: legend ? legend : null,
        },
        series: [
            {
                type: 'pie',
                radius: donut? ['30%', '60%'] : '80%',
                left: '15%',
                top: title.includes("\n") ? 30 * (title.match(/\n/)||[]).length : 0,
                itemStyle: donut ? {
                    borderRadius: 10,
                        borderColor: '#fff',
                        borderWidth: 2
                } : null,
                detail: {
                    offsetCenter: [0, 0],
                    formatter: '{value}%',
                    borderColor: '#eee'
                },
                title: {
                    fontSize: 14
                },
                label: {
                    valueFormatter: (fmtoptions && fmtoptions.value) ? (val) => fmtoptions.value(val) : null,
                    formatter: (fmtoptions && fmtoptions.legend) ? (val) => fmtoptions.legend(val) : '{c}',
                    position: (fmtoptions && fmtoptions.legend) ? null :'inside',
                    show: true,
                    labelLine: {show: true}
                },
                data: values
            }
        ]
    };

    var myChart = echarts.init(chartdiv, sys_theme);
    myChart.setOption(chart_pie_option);
    if (onclick) myChart.on("click", onclick);

    const outerdiv = document.createElement('div');

    outerdiv.style.maxWidth = "400px";
    outerdiv.style.height = "380px";
    outerdiv.className = 'card';
    outerdiv.style.overflow = "hidden";
    outerdiv.style.display = 'inline-block';
    outerdiv.style.margin = '4px';
    outerdiv.style.padding = '6px';
    outerdiv.appendChild(chartdiv)
    if (description) {
        const descdiv = document.createElement('p');
        descdiv.innerText = description;
        descdiv.className = 'card-text small';
        outerdiv.appendChild(descdiv);
    }
    return outerdiv
}

