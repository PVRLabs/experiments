const payload = JSON.parse(document.getElementById('chart-data').textContent);
new Chart(document.getElementById('chart'), {
  type: 'line',
  data: {
    datasets: payload.datasets.map(ds => ({
      label: ds.label,
      data: ds.points,
      borderColor: ds.color,
      backgroundColor: ds.color,
      tension: 0.25,
      parsing: {xAxisKey: 'x', yAxisKey: 'y'}
    }))
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    scales: {x: {type: 'linear'}}
  }
});
