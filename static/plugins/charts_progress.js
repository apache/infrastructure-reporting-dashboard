function chart_progress(title, description, value, total, styles) {

    const value_max = total ? total : value;
    const value_pct = total ? Math.round(100*value/total) : value;

    // Set the color of the progress gauge depending on value
    let progress_color = '#50A0FF';
    if (value_pct < 30) progress_color = "#ef4545";
    else if (value_pct < 45) progress_color = "#ffb351";
    else if (value_pct < 60) progress_color = "#ffdc51";
    else if (value_pct < 75) progress_color = "#f3ff51";
    else if (value_pct < 90) progress_color = "#51ff71";

    const chartdiv = document.createElement('div');
    chartdiv.style.width = "380px";
    chartdiv.style.height = "300px";
    chartdiv.style.display = "inline-block";

    if (styles) {
        for (const [k,v] of Object.entries(styles)) {
            chartdiv.style.setProperty(k, v);
        }
    }

    const chart_progress_option = {
        backgroundColor: sys_theme === 'dark' ? "#212529" : "#0000",
        animation: false,
        title: {
            text: title ? title : "",
            left: 'center',
        },
        series: [
            {
                type: 'gauge',
                startAngle: 90,
                endAngle: -270,
                pointer: {
                    show: false
                },
                progress: {
                    show: true,
                    overlap: false,
                    roundCap: false,
                    clip: false,
                    itemStyle: {
                        borderWidth: 1
                    }
                },
                axisLine: {
                    lineStyle: {
                        width: 16
                    }
                },
                axisTick: {
                    show: true
                },
                axisLabel: {
                    distance: 25,
                    show: true
                },
                detail: {
                    offsetCenter: [0, 0],
                    formatter: '{value}%',
                    //color: '#ddd',
                    borderColor: '#f00'
                },
                title: {
                    fontSize: 14
                },
                data: [
                    {
                        value: value_pct,
                        name: total ? `${value}/${total}` : value,
                        itemStyle: {
                            color: progress_color
                        }
                    }
                ]
            }
        ]
    };

    var myChart = echarts.init(chartdiv, sys_theme);
    myChart.setOption(chart_progress_option);

    const outerdiv = document.createElement('div');
    outerdiv.style.maxWidth = "340px";
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

