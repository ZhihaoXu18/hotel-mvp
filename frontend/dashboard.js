const chartColors = {
    blue: "#2563eb",
    green: "#16a34a",
    amber: "#d97706",
    red: "#dc2626",
    slate: "#475467",
    lightBlue: "rgba(37, 99, 235, 0.12)",
    line: "#d9dee7"
};

const currency = new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0
});

const number = new Intl.NumberFormat("en-US", {
    maximumFractionDigits: 0
});

const percent = new Intl.NumberFormat("en-US", {
    maximumFractionDigits: 2
});

let activeCharts = [];

Chart.defaults.font.family = "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif";
Chart.defaults.color = "#667085";

document.getElementById("uploadForm").addEventListener("submit", analyzeUploadedCsv);
loadDashboard();

async function loadDashboard() {
    try {
        const data = await fetchResults();
        renderDashboard(data);
    } catch (error) {
        document.getElementById("dashboard").innerHTML = `
            <div class="error">
                <strong>Dashboard data could not be loaded.</strong>
                <p>Start app.py from the repository root so the browser can fetch data and analyze uploaded CSV files.</p>
            </div>
        `;
        console.error(error);
    }
}

async function fetchResults() {
    const paths = ["/api/results", "/data_out/results.json", "../data_out/results.json", "data_out/results.json"];

    for (const path of paths) {
        try {
            const response = await fetch(path);
            if (response.ok) {
                return response.json();
            }
        } catch (error) {
            console.warn(`Unable to load ${path}`, error);
        }
    }

    throw new Error("No results.json path could be loaded.");
}

async function analyzeUploadedCsv(event) {
    event.preventDefault();

    const fileInput = document.getElementById("csvFile");
    const analyzeButton = document.getElementById("analyzeButton");
    const status = document.getElementById("uploadStatus");
    const file = fileInput.files[0];

    if (!file) {
        status.textContent = "Choose a CSV file first.";
        status.classList.add("error-text");
        return;
    }

    const formData = new FormData();
    formData.append("csvFile", file);

    analyzeButton.disabled = true;
    status.classList.remove("error-text");
    status.textContent = `Analyzing ${file.name}...`;

    try {
        const response = await fetch("/api/analyze", {
            method: "POST",
            body: formData
        });
        const payload = await response.json();

        if (!response.ok) {
            throw new Error(payload.error || "CSV analysis failed.");
        }

        renderDashboard(payload.results);
        document.getElementById("dataSourcePill").lastChild.textContent = " Uploaded CSV analyzed";
        status.textContent = `Report generated from ${payload.filename}.`;
    } catch (error) {
        status.textContent = error.message;
        status.classList.add("error-text");
    } finally {
        analyzeButton.disabled = false;
    }
}

function renderDashboard(data) {
    activeCharts.forEach(chart => chart.destroy());
    activeCharts = [];

    renderSummary(data);
    renderTrend(data);
    renderOptimization(data);
    renderAbTesting(data);
}

function renderSummary(data) {
    const scale = data.business_summary.scale;
    const category = data.business_summary.category_dependence;
    const quality = data.business_summary.revenue_quality;

    const cards = [
        {
            label: "Total Revenue",
            value: currency.format(scale.total_revenue),
            note: "Revenue analyzed in current dataset"
        },
        {
            label: "Total Quantity",
            value: number.format(Number(scale.total_quantity)),
            note: "Units sold across transactions"
        },
        {
            label: "Transactions",
            value: number.format(scale.number_of_transactions),
            note: "Rows after filtering for 2023"
        },
        {
            label: "Average Unit Price",
            value: currency.format(scale.average_unit_price),
            note: `Median unit price ${currency.format(quality.median_unit_price)}`
        },
        {
            label: "Top Category",
            value: category.top_category_by_revenue,
            note: `${percent.format(category.top_category_revenue_share * 100)}% of revenue`
        }
    ];

    document.getElementById("summaryCards").innerHTML = cards.map(card => `
        <article class="card">
            <div class="card-label">${card.label}</div>
            <div class="card-value">${card.value}</div>
            <p class="card-note">${card.note}</p>
        </article>
    `).join("");
}

function renderTrend(data) {
    const trend = data.business_summary.volume_price_structure;
    const momentum = data.business_summary.momentum_and_seasonality;
    const labels = trend.map(row => row.month);

    createChart("revenueChart", {
        type: "line",
        data: {
            labels,
            datasets: [
                {
                    label: "Monthly Revenue",
                    data: trend.map(row => row.total_revenue),
                    borderColor: chartColors.blue,
                    backgroundColor: chartColors.lightBlue,
                    borderWidth: 3,
                    pointRadius: 4,
                    tension: 0.28,
                    fill: true,
                    yAxisID: "y"
                },
                {
                    label: "Average Unit Price",
                    data: trend.map(row => row.avg_unit_price),
                    borderColor: chartColors.green,
                    borderWidth: 2,
                    pointRadius: 3,
                    tension: 0.28,
                    yAxisID: "y1"
                }
            ]
        },
        options: baseChartOptions({
            scales: {
                y: {
                    beginAtZero: false,
                    grid: { color: chartColors.line },
                    ticks: { callback: value => compactCurrency(value) }
                },
                y1: {
                    position: "right",
                    beginAtZero: false,
                    grid: { drawOnChartArea: false },
                    ticks: { callback: value => currency.format(value) }
                },
                x: {
                    grid: { display: false }
                }
            }
        })
    });

    document.getElementById("trendInsights").innerHTML = `
        <div class="insight">
            <strong>Strongest revenue month</strong>
            <p>${momentum.strongest_month_by_revenue} generated the highest monthly revenue.</p>
        </div>
        <div class="insight">
            <strong>Weakest revenue month</strong>
            <p>${momentum.weakest_month_by_revenue} is the month to investigate for demand or pricing pressure.</p>
        </div>
        <div class="insight">
            <strong>Highest price month</strong>
            <p>${momentum.highest_price_month} had the highest average unit price.</p>
        </div>
    `;
}

function renderOptimization(data) {
    const optimizationRows = data.optimization_results || [];
    const labels = optimizationRows.map(row => row.category);

    createChart("optimizationChart", {
        type: "bar",
        data: {
            labels,
            datasets: [
                {
                    label: "Baseline Revenue",
                    data: optimizationRows.map(row => row.baseline_revenue),
                    backgroundColor: "#9aa4b2",
                    borderRadius: 5
                },
                {
                    label: "Optimal Revenue",
                    data: optimizationRows.map(row => row.optimal_revenue),
                    backgroundColor: chartColors.blue,
                    borderRadius: 5
                }
            ]
        },
        options: baseChartOptions({
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: chartColors.line },
                    ticks: { callback: value => compactCurrency(value) }
                },
                x: { grid: { display: false } }
            }
        })
    });

    createChart("upliftChart", {
        type: "bar",
        data: {
            labels,
            datasets: [
                {
                    label: "Expected Uplift %",
                    data: optimizationRows.map(row => row.uplift_pct),
                    backgroundColor: optimizationRows.map(row => row.uplift_pct >= 0 ? chartColors.green : chartColors.red),
                    borderRadius: 5
                }
            ]
        },
        options: baseChartOptions({
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: context => `${context.parsed.y}% expected uplift`
                    }
                }
            },
            scales: {
                y: {
                    grid: { color: chartColors.line },
                    ticks: { callback: value => `${value}%` }
                },
                x: { grid: { display: false } }
            }
        })
    });
}

function renderAbTesting(data) {
    const optimizationTests = data.optimization_ab_results || [];
    const scenarioTests = data.scenario_ab_results || [];
    const allTests = [...optimizationTests, ...scenarioTests];
    const counts = countDecisions(allTests);

    document.getElementById("decisionSummary").innerHTML = [
        decisionCard("Deploy", counts.deploy, "Statistically significant positive uplift.", "deploy"),
        decisionCard("Inconclusive", counts.inconclusive, "Promising ideas that need more data.", "inconclusive"),
        decisionCard("Do Not Deploy", counts.stop, "Significant negative or risky outcomes.", "stop")
    ].join("");

    createChart("abRevenueChart", {
        type: "bar",
        data: {
            labels: optimizationTests.map(row => row.category),
            datasets: [
                {
                    label: "Control / Baseline",
                    data: optimizationTests.map(row => row.baseline_revenue),
                    backgroundColor: "#9aa4b2",
                    borderRadius: 5
                },
                {
                    label: "Treatment",
                    data: optimizationTests.map(row => row.treatment_revenue),
                    backgroundColor: chartColors.green,
                    borderRadius: 5
                }
            ]
        },
        options: baseChartOptions({
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: chartColors.line },
                    ticks: { callback: value => compactCurrency(value) }
                },
                x: { grid: { display: false } }
            }
        })
    });

    createChart("decisionChart", {
        type: "doughnut",
        data: {
            labels: ["Deploy", "Inconclusive", "Do Not Deploy"],
            datasets: [
                {
                    data: [counts.deploy, counts.inconclusive, counts.stop],
                    backgroundColor: [chartColors.green, chartColors.amber, chartColors.red],
                    borderColor: "#ffffff",
                    borderWidth: 4
                }
            ]
        },
        options: baseChartOptions({
            cutout: "62%",
            plugins: {
                legend: {
                    position: "bottom",
                    labels: { usePointStyle: true, boxWidth: 8 }
                }
            }
        })
    });

    renderAbTable(allTests);
}

function renderAbTable(rows) {
    const sortedRows = [...rows].sort((a, b) => b.uplift_pct - a.uplift_pct);

    document.getElementById("abTable").innerHTML = `
        <thead>
            <tr>
                <th>Group</th>
                <th>Test Type</th>
                <th>Control Revenue</th>
                <th>Treatment Revenue</th>
                <th>Uplift</th>
                <th>p-value</th>
                <th>Decision</th>
            </tr>
        </thead>
        <tbody>
            ${sortedRows.map(row => {
                const testType = row.price_tier ? `Scenario: ${row.price_tier}` : "Optimization";
                const controlRevenue = row.control_revenue ?? row.baseline_revenue;

                return `
                    <tr>
                        <td>${row.category}</td>
                        <td>${testType}</td>
                        <td>${currency.format(controlRevenue)}</td>
                        <td>${currency.format(row.treatment_revenue)}</td>
                        <td>${percent.format(row.uplift_pct)}%</td>
                        <td>${Number(row.p_value).toFixed(2)}</td>
                        <td><span class="badge ${decisionClass(row.decision)}">${row.decision}</span></td>
                    </tr>
                `;
            }).join("")}
        </tbody>
    `;
}

function createChart(canvasId, config) {
    const chart = new Chart(document.getElementById(canvasId), config);
    activeCharts.push(chart);
    return chart;
}

function decisionCard(label, value, note, className) {
    return `
        <article class="card decision-card ${className}">
            <div class="card-label">${label}</div>
            <div class="card-value">${value}</div>
            <p class="card-note">${note}</p>
        </article>
    `;
}

function countDecisions(rows) {
    return rows.reduce((acc, row) => {
        const decision = row.decision || "";
        if (decision.includes("Deploy")) {
            acc.deploy += 1;
        } else if (decision.includes("Do NOT")) {
            acc.stop += 1;
        } else {
            acc.inconclusive += 1;
        }
        return acc;
    }, { deploy: 0, inconclusive: 0, stop: 0 });
}

function decisionClass(decision) {
    if (decision.includes("Do NOT")) {
        return "stop";
    }

    if (decision.includes("Deploy")) {
        return "deploy";
    }

    return "inconclusive";
}

function baseChartOptions(overrides = {}) {
    return mergeOptions({
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: "bottom",
                labels: {
                    usePointStyle: true,
                    boxWidth: 8,
                    padding: 18
                }
            },
            tooltip: {
                backgroundColor: "#111827",
                padding: 12,
                titleFont: { weight: "700" },
                callbacks: {
                    label: context => {
                        const value = context.parsed.y ?? context.parsed;
                        return `${context.dataset.label}: ${formatTooltipValue(value)}`;
                    }
                }
            }
        },
        scales: {}
    }, overrides);
}

function mergeOptions(base, overrides) {
    return {
        ...base,
        ...overrides,
        plugins: {
            ...base.plugins,
            ...overrides.plugins,
            legend: {
                ...base.plugins.legend,
                ...(overrides.plugins && overrides.plugins.legend)
            },
            tooltip: {
                ...base.plugins.tooltip,
                ...(overrides.plugins && overrides.plugins.tooltip),
                callbacks: {
                    ...base.plugins.tooltip.callbacks,
                    ...((overrides.plugins && overrides.plugins.tooltip && overrides.plugins.tooltip.callbacks) || {})
                }
            }
        },
        scales: {
            ...base.scales,
            ...overrides.scales
        }
    };
}

function compactCurrency(value) {
    if (Math.abs(value) >= 1000000) {
        return `$${(value / 1000000).toFixed(1)}M`;
    }

    if (Math.abs(value) >= 1000) {
        return `$${(value / 1000).toFixed(0)}K`;
    }

    return currency.format(value);
}

function formatTooltipValue(value) {
    if (typeof value !== "number") {
        return value;
    }

    return Math.abs(value) > 100 ? currency.format(value) : `${percent.format(value)}%`;
}
