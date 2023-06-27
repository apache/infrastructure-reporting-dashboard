function chart_bar(title, description, series, styles, timeseries=false, stacked=false) {
    const chartdiv = document.createElement('div');
    chartdiv.style.width = "500px";
    chartdiv.style.height = "300px";
    chartdiv.style.display = "inline-block";
    if (styles) {
        for (const [k,v] of Object.entries(styles)) {
            chartdiv.style.setProperty(k, v);
        }
    }
    const series_converted = [];
    // Grab all value keys
    const keys = [];
    for (const [k, v] of Object.entries(series)) {
        if (typeof v === "object") {
            for (const datakey in v) {
                if (!keys.includes(datakey)) {
                    keys.push(datakey);
                }
            }
        }
    }

    for (const [k,v] of Object.entries(series)) {
        let data_values = [];
        if (typeof v === "object") {
            if (!timeseries) {
                for (const [key, val] of Object.entries(v)) {
                    let i = keys.indexOf(key);
                    data_values[i] = val;
                }
            } else {
                for (const entry of v) {
                    data_values.push([new Date(entry[0]*1000.0), entry[1]]);
                }
            }
        } else {
            data_values = v;
        }
        series_converted.push({
            name: k,
            type: "bar",
            data: data_values,
            stack: stacked ? 'stack' : null,
        })
    }
    const chart_line_option = {
        backgroundColor: sys_theme === 'dark' ? "#212529" : "#0000",
        animation: false,
        title: {
            text: title ? title : "",
            left: 'center',
        },

        tooltip: {
            trigger: 'axis',
            confine: true,
            valueFormatter: timeseries ? null : (val) => `${val.toFixed(2)}%`,
            formatter: stacked ? (params) => {
                let output = `<h6>${params[0].axisValueLabel}</h6><table class="w-full">`;
                params.reverse().forEach(function (param) {
                    const value =param.data;
                    if (value[1] !== 0) {
                        output += `<tr>
                          <td>${param.marker}</td>
                          <td>${param.seriesName}</td>
                          <td class="text-right font-bold tabular-nums">${value[1]}</td>
                        </tr>`;
                    }
                });
                return output + '</table>';
            } : null,
        },
        legend: {
            orient: 'vertical',
            type: 'scroll',
            align: 'right',
            right: 0
        },
        grid: {
            right: 200
        },
        xAxis: {
            type: timeseries ? 'time' : 'category',
            boundaryGap: true,
            data: keys,
        },
        yAxis: {
            type: 'value',
            min: 'dataMin',
            boundaryGap: true
        },
        series: series_converted
    };

    var myChart = echarts.init(chartdiv, sys_theme);
    myChart.setOption(chart_line_option);

    const outerdiv = document.createElement('div');

    outerdiv.style.maxWidth = "1600px";
    outerdiv.style.maxHeight = "600px";
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

