const socket = io();

const logs = document.getElementById("logs");

let chart;

// =====================================================
// LOGS
// =====================================================

function log(text) {

    logs.innerHTML += text + "<br>";

    logs.scrollTop = logs.scrollHeight;
}

// =====================================================
// LOAD WALLETS
// =====================================================

async function loadWallets() {

    const res = await fetch("/wallets");

    const data = await res.json();

    const walletsDiv = document.getElementById("wallets");

    const sender = document.getElementById("sender");

    const receiver = document.getElementById("receiver");

    const currentSender = sender.value;

    const currentReceiver = receiver.value;

    walletsDiv.innerHTML = "";

    sender.innerHTML = "";

    receiver.innerHTML = "";

    const names = Object.keys(data);

    names.forEach((name) => {

        walletsDiv.innerHTML += `
            <p>${name}: $${data[name].balance}</p>
        `;

        sender.innerHTML += `
            <option value="${name}">
                ${name}
            </option>
        `;

        receiver.innerHTML += `
            <option value="${name}">
                ${name}
            </option>
        `;
    });

    // Restore previous selections if possible
    if (names.includes(currentSender)) {
        sender.value = currentSender;
    } else {
        sender.value = names[0];
    }

    if (names.includes(currentReceiver)) {
        receiver.value = currentReceiver;
    } else {
        receiver.value = names[1] || names[0];
    }

    // Prevent same wallet selection
    if (sender.value === receiver.value && names.length > 1) {

        receiver.value = names.find(
            n => n !== sender.value
        );
    }
}

// =====================================================
// SEND TRANSACTION
// =====================================================

async function sendTransaction() {

    const sender = document.getElementById("sender").value;

    const receiver = document.getElementById("receiver").value;

    const amount = document.getElementById("amount").value;

    if (sender === receiver) {

        alert("Sender and receiver cannot be same");

        return;
    }

    const res = await fetch("/transaction", {

        method: "POST",

        headers: {
            "Content-Type": "application/json"
        },

        body: JSON.stringify({
            sender,
            receiver,
            amount
        })
    });

    const data = await res.json();

    log(JSON.stringify(data));

    loadWallets();
}

// =====================================================
// MINE BLOCK
// =====================================================

async function mineBlock() {

    const res = await fetch("/mine");

    const data = await res.json();

    log(JSON.stringify(data));

    updateChart();
}

// =====================================================
// SOCKET EVENTS
// =====================================================

socket.on("mining_status", (data) => {

    document.getElementById(
        "mining-status"
    ).innerText = data.status;
});

socket.on("new_block", (data) => {

    log(
        `Block ${data.block} mined | TPS: ${data.tps}`
    );

    updateChart();
});

socket.on("transaction_update", (data) => {

    log(
        `TX: ${data.sender} → ${data.receiver} : ${data.amount}`
    );

    loadWallets();
});

// =====================================================
// TPS GRAPH
// =====================================================

async function updateChart() {

    const res = await fetch("/tps");

    const data = await res.json();

    const ctx = document.getElementById("tpsChart");

    if (chart) {
        chart.destroy();
    }

    chart = new Chart(ctx, {

        type: "line",

        data: {

            labels: data.map((_, i) => i + 1),

            datasets: [{
                label: "TPS",
                data: data
            }]
        }
    });
}

// =====================================================

loadWallets();

updateChart();

setInterval(loadWallets, 2000);