
async function chart_map(title, description, values, styles) {
    const chartdiv = document.createElement('div');
    chartdiv.style.width = "700px";
    chartdiv.style.height = "400px";
    chartdiv.style.display = "inline-block";
    if (styles) {
        for (const [k,v] of Object.entries(styles)) {
            chartdiv.style.setProperty(k, v);
        }
    }


    // Test for label calculation.
    worldJson.features.forEach(feature => {
        feature.properties && (feature.properties.cp = null);
    });

    echarts.registerMap('world', worldJson);
    var chart = echarts.init(chartdiv, sys_theme, {

    });

    let maxVal = 1;
    for (const el of values) {
        if (el.value > maxVal) maxVal = el.value;
    }

    var itemStyle = {
        normal:{
            borderWidth: 0.5,
            borderColor: 'black'
        },
        emphasis:{
            label:{show:true}
        }
    };

    chart.setOption({
        backgroundColor: sys_theme === 'dark' ? "#212529" : "#0000",
        title : {
            text: title,
            subtext: description,
            left: 'center',
            top: 'top'
        },
        tooltip : {
            trigger: 'item',
            formatter : function (params) {
                const value = params.value ? params.value.pretty() : '0';
                return params.seriesName + '<br/>' + params.name + ' : ' + value;
            }
        },
        visualMap: {
            min: 0,
            max: maxVal,
            text:['High','Low'],
            realtime: true,
            calculable : true,
            color: ['orangered','yellow','lightgreen', 'lightskyblue']
        },
        series : [
            {
                name: title,
                type: 'map',
                map: 'world',
                roam: true,
                top: 60,
                width: '80%',
                label: {
                    //show: true,
                    textBorderColor: '#fff',
                    textBorderWidth: 1
                },
                itemStyle: itemStyle,
                data: values
            }
        ]
    });

    const outerdiv = document.createElement('div');

    outerdiv.style.maxWidth = "700px";
    outerdiv.style.height = "400px";
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

