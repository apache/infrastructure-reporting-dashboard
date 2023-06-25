function chart_pie(title, description, values, styles) {
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
        backgroundColor: "#212529",
        animation: false,
        title: {
            text: title ? title : "",
            left: 'center',
            textStyle: {
                color: "#ddd"
            }
        },
        tooltip: {
            trigger: 'item',
            formatter: '{b} : {c} ({d}%)'
        },
        legend: {
            orient: 'vertical',
            left: 'left'
        },
        series: [
            {
                type: 'pie',
                radius: '75%',
                detail: {
                    offsetCenter: [0, 0],
                    formatter: '{value}%',
                    color: '#ddd',
                    borderColor: '#eee'
                },
                title: {
                    fontSize: 14
                },
                label: {
                    formatter: '{c}',
                    position: 'inside'
                },
                data: values
            }
        ]
    };

    var myChart = echarts.init(chartdiv, 'dark');
    myChart.setOption(chart_pie_option);

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

