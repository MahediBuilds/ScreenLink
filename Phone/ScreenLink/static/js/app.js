async function loadPhoneInfo() {

    try {

        const response =
            await fetch("/status");

        const data =
            await response.json();

        if (data.success) {

            document.getElementById(
                "phoneInfo"
            ).textContent =
                `Phone: ${data.ip}:${data.port}`;

        }

    } catch (error) {

        document.getElementById(
            "phoneInfo"
        ).textContent =
            "Phone server information unavailable.";

    }
}


async function loadDevices() {

    const container =
        document.getElementById("devices");

    container.innerHTML =
        '<p class="muted">Loading...</p>';

    try {

        const response =
            await fetch("/devices");

        const data =
            await response.json();

        if (!data.success) {

            container.innerHTML =
                '<p class="error">Failed to load devices.</p>';

            return;
        }

        if (data.devices.length === 0) {

            container.innerHTML =
                '<p class="muted">No laptops connected.</p>';

            return;
        }

        container.innerHTML = "";

        data.devices.forEach(
            device => {

                const div =
                    document.createElement(
                        "div"
                    );

                div.className =
                    "device";

                const status =
                    device.online
                    ? "ONLINE"
                    : "OFFLINE";

                const statusClass =
                    device.online
                    ? "online"
                    : "offline";

                const button =
                    device.online
                    ?
                    `
                    <button
                        class="capture-button"
                        onclick="takeScreenshot('${escapeHtml(device.name)}')"
                    >
                        Take Screenshot
                    </button>
                    `
                    :
                    "";

                div.innerHTML = `

                    <div class="device-name">
                        ${escapeHtml(device.name)}
                    </div>

                    <div class="device-ip">
                        ${escapeHtml(device.ip)}:${device.port}
                    </div>

                    <div class="status ${statusClass}">
                        ${status}
                    </div>

                    ${button}

                    <div
                        id="screen-${encodeURIComponent(device.name)}"
                    >
                    </div>

                `;

                container.appendChild(div);
            }
        );

    } catch (error) {

        container.innerHTML =
            '<p class="error">Unable to contact server.</p>';

    }
}


async function takeScreenshot(deviceName) {

    const elementId =
        "screen-" +
        encodeURIComponent(deviceName);

    const container =
        document.getElementById(
            elementId
        );

    if (!container) {
        return;
    }

    container.innerHTML =
        '<p class="muted">Capturing screenshot...</p>';

    try {

        const response =
            await fetch(
                "/screenshot/" +
                encodeURIComponent(deviceName)
            );

        if (!response.ok) {

            let message =
                "Screenshot failed.";

            try {

                const data =
                    await response.json();

                if (data.message) {
                    message = data.message;
                }

            } catch {}

            throw new Error(message);
        }

        const blob =
            await response.blob();

        const url =
            URL.createObjectURL(blob);

        container.innerHTML = `

            <img
                class="screenshot"
                src="${url}"
                alt="Laptop screenshot"
            >

        `;

    } catch (error) {

        container.innerHTML = `

            <p class="error">
                ${escapeHtml(error.message)}
            </p>

        `;

    }
}


async function manualConnect() {

    const ip =
        document.getElementById(
            "manualIp"
        ).value.trim();

    const port =
        document.getElementById(
            "manualPort"
        ).value.trim();

    const result =
        document.getElementById(
            "manualResult"
        );

    if (!ip) {

        result.className = "error";

        result.textContent =
            "Enter a laptop IP address.";

        return;
    }

    result.className = "muted";

    result.textContent =
        "Checking laptop...";

    try {

        const response =
            await fetch(
                "/probe",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({

                        ip: ip,

                        port:
                            parseInt(
                                port || "5001"
                            )

                    })
                }
            );

        const data =
            await response.json();

        if (!data.success) {

            result.className =
                "error";

            result.textContent =
                data.message ||
                "Unable to connect.";

            return;
        }

        result.className =
            "success";

        result.textContent =
            `${data.device.name} connected successfully.`;

        document.getElementById(
            "manualIp"
        ).value = "";

        await loadDevices();

    } catch (error) {

        result.className =
            "error";

        result.textContent =
            "Connection failed.";

    }
}


function escapeHtml(value) {

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


loadPhoneInfo();

loadDevices();


setInterval(
    loadDevices,
    5000
);