let laptopOnline = false;
let activeTyping = false;


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


async function loadDevice() {

    try {

        const response =
            await fetch("/device");

        const data =
            await response.json();

        if (!data.success) {

            showDeviceMessage(
                "Unable to load laptop status.",
                "error"
            );

            return;
        }

        updateDevice(
            data.device
        );

    } catch (error) {

        showDeviceMessage(
            "Unable to contact server.",
            "error"
        );

    }
}


function updateDevice(device) {

    const container =
        document.getElementById(
            "device"
        );

    const typeButton =
        document.getElementById(
            "typeButton"
        );

    const stopButton =
        document.getElementById(
            "stopButton"
        );


    if (!device) {

        laptopOnline = false;

        container.innerHTML = `

            <p class="muted">
                Waiting for laptop registration...
            </p>

        `;

        typeButton.disabled = true;

        if (!activeTyping) {
            stopButton.disabled = true;
        }

        return;
    }


    laptopOnline =
        device.online;


    if (device.online) {

        container.innerHTML = `

            <div class="device">

                <div class="device-name">
                    ${escapeHtml(device.name)}
                </div>

                <div class="device-ip">
                    ${escapeHtml(device.ip)}:${device.port}
                </div>

                <div class="status online">
                    ONLINE
                </div>

                <div class="device-controls">

                    <button
                        class="capture-button"
                        onclick="takeScreenshot()"
                    >
                        Take Screenshot
                    </button>

                </div>

                <div
                    id="screenshot-container"
                    class="screenshot-container"
                ></div>

            </div>

        `;

        if (!activeTyping) {
            typeButton.disabled = false;
        }

    } else {

        container.innerHTML = `

            <div class="device">

                <div class="device-name">
                    ${escapeHtml(device.name)}
                </div>

                <div class="device-ip">
                    ${escapeHtml(device.ip)}:${device.port}
                </div>

                <div class="status offline">
                    OFFLINE
                </div>

            </div>

        `;

        laptopOnline = false;

        typeButton.disabled = true;

        if (!activeTyping) {
            stopButton.disabled = true;
        }
    }
}


function showDeviceMessage(
    message,
    className
) {

    const container =
        document.getElementById(
            "device"
        );

    container.innerHTML =
        `<p class="${className}">
            ${escapeHtml(message)}
        </p>`;

}


async function takeScreenshot() {

    const container =
        document.getElementById(
            "screenshot-container"
        );

    if (!container) {
        return;
    }

    container.innerHTML =
        '<p class="muted">Capturing screenshot...</p>';

    try {

        const response =
            await fetch(
                "/screenshot"
            );

        if (!response.ok) {

            let message =
                "Screenshot failed.";

            try {

                const data =
                    await response.json();

                if (data.message) {

                    message =
                        data.message;

                }

            } catch {}

            throw new Error(
                message
            );
        }

        const blob =
            await response.blob();

        const url =
            URL.createObjectURL(
                blob
            );

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


async function sendTyping() {

    const text =
        document.getElementById(
            "typeText"
        ).value;

    const result =
        document.getElementById(
            "typeResult"
        );

    const typeButton =
        document.getElementById(
            "typeButton"
        );

    const stopButton =
        document.getElementById(
            "stopButton"
        );


    if (!text.trim()) {

        result.className =
            "error";

        result.textContent =
            "Enter some text first.";

        return;
    }


    if (!laptopOnline) {

        result.className =
            "error";

        result.textContent =
            "Laptop is offline.";

        return;
    }


    result.className =
        "muted";

    result.textContent =
        "Starting typing...";


    typeButton.disabled = true;

    stopButton.disabled = true;


    try {

        const response =
            await fetch(
                "/type",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        text: text
                    })
                }
            );


        const data =
            await response.json();


        if (!data.success) {

            throw new Error(
                data.message ||
                "Typing failed."
            );

        }


        activeTyping = true;

        result.className =
            "success";

        result.textContent =
            "Typing started.";

        stopButton.disabled = false;


    } catch (error) {

        result.className =
            "error";

        result.textContent =
            error.message ||
            "Unable to start typing.";

        typeButton.disabled =
            !laptopOnline;

        stopButton.disabled =
            true;

    }
}


async function stopTyping() {

    const result =
        document.getElementById(
            "typeResult"
        );

    const typeButton =
        document.getElementById(
            "typeButton"
        );

    const stopButton =
        document.getElementById(
            "stopButton"
        );


    if (!activeTyping) {

        result.className =
            "error";

        result.textContent =
            "No typing operation is active.";

        return;
    }


    stopButton.disabled = true;

    result.className =
        "muted";

    result.textContent =
        "Stopping typing...";


    try {

        const response =
            await fetch(
                "/stop-type",
                {
                    method: "POST"
                }
            );


        const data =
            await response.json();


        if (!data.success) {

            throw new Error(
                data.message ||
                "Failed to stop typing."
            );

        }


        activeTyping = false;

        result.className =
            "success";

        result.textContent =
            "Typing stopped.";

        typeButton.disabled =
            !laptopOnline;

        stopButton.disabled =
            true;


    } catch (error) {

        result.className =
            "error";

        result.textContent =
            error.message ||
            "Unable to stop typing.";

        stopButton.disabled =
            false;

    }
}


function escapeHtml(value) {

    return String(value)
        .replaceAll(
            "&",
            "&amp;"
        )
        .replaceAll(
            "<",
            "&lt;"
        )
        .replaceAll(
            ">",
            "&gt;"
        )
        .replaceAll(
            '"',
            "&quot;"
        )
        .replaceAll(
            "'",
            "&#039;"
        );
}


loadPhoneInfo();

loadDevice();


setInterval(
    loadDevice,
    5000
);