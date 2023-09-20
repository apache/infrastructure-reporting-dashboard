function chart_table(title, headers, dict) {
    // Generates a striped table with optional headers and rows corresponding to the provided key/value dictionary.
    // If a key has no corresponding value (is null), the row is treated as a sub-header.
    const table_div = document.createElement('div');
    table_div.style.width = "500px";
    table_div.style.height = "380px";
    table_div.style.margin = "4px";
    table_div.style.padding = "6px";
    table_div.style.overflow = "hidden";
    table_div.className = "card";
    table_div.style.display = "inline-block";

    if (title) {
        const titletxt = document.createElement('h4');
        titletxt.innerText = title;
        titletxt.className = 'text-center';
        table_div.appendChild(titletxt);
    }

    const table = document.createElement('table');
    table.className = 'table';
    table_div.appendChild(table);

    if (headers) {
        const table_header = document.createElement('thead');
        const tr = document.createElement('tr');
        for (const col of headers) {
            const th = document.createElement('th');
            th.innerText = col;
            tr.appendChild(th);
        }
        table_header.appendChild(tr);
        table.appendChild(table_header);
    }

    if (dict) {
        const table_body = document.createElement('tbody');
        for (const [key, value] of Object.entries(dict)) {
            const tr = document.createElement('tr');
            const td_key = document.createElement('td');
            td_key.innerText = key + ":";
            td_key.style.fontWeight = 'bold';
            tr.appendChild(td_key);
            if (value === null) { // If value is null, this row is treated as a sub-header
                td_key.colSpan = 2;
                td_key.style.textAlign = 'center';
                td_key.style.fontVariant = 'small-caps';
            } else {
                const td_value = document.createElement('td');
                if (typeof value === "object") td_value.appendChild(value);
                else td_value.innerText = value;
                tr.appendChild(td_value);
            }
            table_body.appendChild(tr);
        }
        table.appendChild(table_body);
    }



    return table_div
}

function chart_table_list(title, headers, items) {
    const table_div = document.createElement('div');
    table_div.style.minWidth = "500px";
    table_div.style.minHeight = "400px";
    table_div.style.margin = "4px";
    table_div.style.padding = "6px";
    table_div.style.overflow = "hidden";
    table_div.className = "card";
    table_div.style.display = "inline-block";


    if (title) {
        const titletxt = document.createElement('h4');
        titletxt.innerText = title;
        titletxt.className = 'text-center';
        table_div.appendChild(titletxt);
    }

    const table = document.createElement('table');
    table.className = 'table table-striped';

    table_div.appendChild(table);

    if (headers) {
        const table_header = document.createElement('thead');
        const tr = document.createElement('tr');
        for (const col of headers) {
            const th = document.createElement('th');
            th.style.fontSize = "0.9rem";
            th.innerText = col;
            tr.appendChild(th);
        }
        table_header.appendChild(tr);
        table.appendChild(table_header);
    }

    if (items) {
        const table_body = document.createElement('tbody');
        for (const item of items) {
            const tr = document.createElement('tr');
            for (const col of item) {
                const td = document.createElement('td');
                if (typeof col === "string") {
                    td.innerText = col;
                } else if (typeof col === "object") {
                    td.appendChild(col);
                } else {
                    td.innerText = "fooo"
                }
                tr.appendChild(td);
            }
            table_body.appendChild(tr);
        }
        table.appendChild(table_body);
    }



    return table_div
}