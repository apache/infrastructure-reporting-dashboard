// Math functions not supplied by JS

Math.median = function (numbers) {
    const numbers_sorted = Array.from(numbers).sort((a, b) => a - b);
    const middle_pos = Math.floor(numbers_sorted.length / 2);
    // Even number of elements, return the average of the two in the middle
    if (numbers_sorted.length % 2 === 0) {
        return (numbers_sorted[middle_pos - 1] + numbers_sorted[middle_pos]) / 2;
    }
    // Odd number of elements, return the middle one
    return numbers_sorted[middle_pos];
}

Math.sum = (numbers) => numbers.reduce((a,b) => a+b);

Number.prototype.pretty = function(fix) {
    if (fix) {
        return String(this.toFixed(fix)).replace(/(\d)(?=(\d{3})+\.)/g, '$1,');
    }
    return String(this.toFixed(0)).replace(/(\d)(?=(\d{3})+$)/g, '$1,');
};