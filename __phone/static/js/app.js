let activeTypingDevice = null;


async function loadPhoneInfo() {

    try {

        const response =
            await fetch(
                "/status"
            );


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

    try {

        const response =
            await fetch(
                "/devices"
            );


        const data =
            await response.json();


        if (!data.success) {

            showDeviceMessage(
                "Failed to load devices.",
                "error"
            );


            return;

        }


        updateDevices(
            data.devices
        );


    } catch (error) {

        showDeviceMessage(
            "Unable to contact server.",
            "error"
        );

    }

}


function updateDevices(
    devices
) {

    const container =
        document.getElementById(
            "devices"
        );


    const existing =
        new Map();


    container
        .querySelectorAll(
            ".device"
        )
        .forEach(
            element => {

                existing.set(

                    element.dataset.deviceName,

                    element

                );

            }
        );


    if (
        devices.length === 0
    ) {

        if (
            !container.querySelector(
                ".no-devices"
            )
        ) {

            container.innerHTML =
                '<p class="muted no-devices">No laptops connected.</p>';

        }


        return;

    }


    const emptyMessage =
        container.querySelector(
            ".no-devices"
        );


    if (emptyMessage) {

        emptyMessage.remove();

    }


    const currentNames =
        new Set();


    devices.forEach(
        device => {

            currentNames.add(
                device.name
            );


            let element =
                existing.get(
                    device.name
                );


            if (!element) {

                element =
                    createDeviceElement(
                        device
                    );


                container.appendChild(
                    element
                );

            }


            updateDeviceElement(
                element,
                device
            );

        }
    );


    existing.forEach(
        (
            element,
            name
        ) => {

            if (
                !currentNames.has(
                    name
                )
            ) {

                element.remove();

            }

        }
    );

}


function createDeviceElement(
    device
) {

    const div =
        document.createElement(
            "div"
        );


    div.className =
        "device";


    div.dataset.deviceName =
        device.name;


    div.innerHTML = `

        <div class="device-name"></div>

        <div class="device-ip"></div>

        <div class="status"></div>

        <div class="device-controls"></div>

        <div class="screenshot-container"></div>

        <div class="ai-click-section hidden">

            <h3>
                ChatGPT Click Instructions
            </h3>

            <p class="muted">
                Give the screenshot to ChatGPT,
                then paste its normalized JSON here.
            </p>

            <textarea
                class="click-json"
                placeholder='Paste ChatGPT JSON here...'
                rows="8"
            ></textarea>

            <button
                class="execute-click-button"
                onclick="executeClicks(this)"
            >
                Execute Clicks
            </button>

            <p class="click-result"></p>

        </div>

    `;


    return div;

}


function updateDeviceElement(
    element,
    device
) {

    element.querySelector(
        ".device-name"
    ).textContent =
        device.name;


    element.querySelector(
        ".device-ip"
    ).textContent =
        `${device.ip}:${device.port}`;


    const status =
        element.querySelector(
            ".status"
        );


    status.textContent =
        device.online
        ? "ONLINE"
        : "OFFLINE";


    status.className =
        device.online
        ? "status online"
        : "status offline";


    const controls =
        element.querySelector(
            ".device-controls"
        );


    if (device.online) {

        controls.innerHTML = `

            <button
                class="capture-button"
                onclick="takeScreenshot(
                    '${escapeHtml(
                        device.name
                    )}'
                )"
            >
                Take Screenshot
            </button>

        `;


    } else {

        controls.innerHTML = "";


        if (
            activeTypingDevice
            === device.name
        ) {

            activeTypingDevice = null;

        }


        const aiSection =
            element.querySelector(
                ".ai-click-section"
            );


        if (aiSection) {

            aiSection.classList.add(
                "hidden"
            );

        }

    }

}


function showDeviceMessage(
    message,
    className
) {

    const container =
        document.getElementById(
            "devices"
        );


    if (
        container.querySelector(
            ".device"
        )
    ) {

        return;

    }


    container.innerHTML =
        `<p class="${className}">
            ${escapeHtml(message)}
        </p>`;

}


async function takeScreenshot(
    deviceName
) {

    const element =
        document.querySelector(
            `.device[data-device-name="${cssEscape(
                deviceName
            )}"]`
        );


    if (!element) {

        return;

    }


    const container =
        element.querySelector(
            ".screenshot-container"
        );


    const aiSection =
        element.querySelector(
            ".ai-click-section"
        );


    container.innerHTML =
        '<p class="muted">Capturing screenshot...</p>';


    aiSection.classList.add(
        "hidden"
    );


    try {

        const response =
            await fetch(

                "/screenshot/" +
                encodeURIComponent(
                    deviceName
                )

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


        if (!blob.size) {

            throw new Error(
                "Screenshot is empty."
            );

        }


        const url =
            URL.createObjectURL(
                blob
            );


        const image =
            document.createElement(
                "img"
            );


        image.className =
            "screenshot";


        image.alt =
            "Laptop screenshot";


        image.onload =
            function () {

                aiSection.classList.remove(
                    "hidden"
                );

            };


        image.onerror =
            function () {

                URL.revokeObjectURL(
                    url
                );


                container.innerHTML =
                    '<p class="error">Unable to display screenshot.</p>';

            };


        image.src =
            url;


        container.innerHTML =
            "";


        container.appendChild(
            image
        );


    } catch (error) {

        container.innerHTML = `

            <p class="error">
                ${escapeHtml(
                    error.message
                )}
            </p>

        `;

    }

}


async function executeClicks(
    button
) {

    const deviceElement =
        button.closest(
            ".device"
        );


    if (!deviceElement) {

        return;

    }


    const deviceName =
        deviceElement.dataset.deviceName;


    const input =
        deviceElement.querySelector(
            ".click-json"
        );


    const result =
        deviceElement.querySelector(
            ".click-result"
        );


    const raw =
        input.value.trim();


    if (!raw) {

        result.className =
            "error";


        result.textContent =
            "Paste the ChatGPT JSON first.";


        return;

    }


    let data;


    try {

        data =
            JSON.parse(
                raw
            );


    } catch (error) {

        result.className =
            "error";


        result.textContent =
            "Invalid JSON.";


        return;

    }


    if (
        !data
        ||
        !Array.isArray(
            data.steps
        )
    ) {

        result.className =
            "error";


        result.textContent =
            "JSON must contain a steps array.";


        return;

    }


    if (
        data.steps.length === 0
    ) {

        result.className =
            "error";


        result.textContent =
            "No click steps found.";


        return;

    }


    if (
        data.steps.length > 6
    ) {

        result.className =
            "error";


        result.textContent =
            "Maximum 6 click steps allowed.";


        return;

    }


    for (
        const step
        of data.steps
    ) {

        if (
            !step
            ||
            step.action !== "click"
        ) {

            result.className =
                "error";


            result.textContent =
                "Every step must use action: click.";


            return;

        }


        if (
            !step.point
            ||
            typeof step.point.x !== "number"
            ||
            typeof step.point.y !== "number"
        ) {

            result.className =
                "error";


            result.textContent =
                "Every step needs a normalized point.";


            return;

        }


        if (

            step.point.x < 0
            ||
            step.point.x > 1000
            ||
            step.point.y < 0
            ||
            step.point.y > 1000

        ) {

            result.className =
                "error";


            result.textContent =
                "Coordinates must be between 0 and 1000.";


            return;

        }

    }


    button.disabled =
        true;


    result.className =
        "muted";


    result.textContent =
        "Executing clicks...";


    try {

        const response =
            await fetch(

                "/click/" +
                encodeURIComponent(
                    deviceName
                ),

                {

                    method:
                        "POST",

                    headers: {

                        "Content-Type":
                            "application/json"

                    },

                    body:
                        JSON.stringify(
                            data
                        )

                }

            );


        const responseData =
            await response.json();


        if (
            !responseData.success
        ) {

            throw new Error(

                responseData.message
                ||
                "Click execution failed."

            );

        }


        result.className =
            "success";


        result.textContent =
            `Executed ${
                responseData.executed || 0
            } click(s).`;


    } catch (error) {

        result.className =
            "error";


        result.textContent =
            error.message
            ||
            "Unable to execute clicks.";


    } finally {

        button.disabled =
            false;

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

        result.className =
            "error";


        result.textContent =
            "Enter a laptop IP address.";


        return;

    }


    result.className =
        "muted";


    result.textContent =
        "Checking laptop...";


    try {

        const response =
            await fetch(

                "/probe",

                {

                    method:
                        "POST",

                    headers: {

                        "Content-Type":
                            "application/json"

                    },

                    body:
                        JSON.stringify({

                            ip:
                                ip,

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
                data.message
                ||
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


    result.className =
        "muted";


    result.textContent =
        "Starting typing...";


    typeButton.disabled =
        true;


    stopButton.disabled =
        true;


    try {

        const devicesResponse =
            await fetch(
                "/devices"
            );


        const devicesData =
            await devicesResponse.json();


        if (!devicesData.success) {

            throw new Error(
                "Failed to load devices."
            );

        }


        const onlineDevice =
            devicesData.devices.find(

                device =>
                    device.online

            );


        if (!onlineDevice) {

            throw new Error(
                "No laptop is online."
            );

        }


        const response =
            await fetch(

                "/type/" +
                encodeURIComponent(
                    onlineDevice.name
                ),

                {

                    method:
                        "POST",

                    headers: {

                        "Content-Type":
                            "application/json"

                    },

                    body:
                        JSON.stringify({

                            text:
                                text

                        })

                }

            );


        const data =
            await response.json();


        if (!data.success) {

            throw new Error(

                data.message
                ||
                "Typing failed."

            );

        }


        activeTypingDevice =
            onlineDevice.name;


        result.className =
            "success";


        result.textContent =
            "Typing started.";


        stopButton.disabled =
            false;


    } catch (error) {

        result.className =
            "error";


        result.textContent =
            error.message
            ||
            "Unable to start typing.";


        typeButton.disabled =
            false;


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


    if (!activeTypingDevice) {

        result.className =
            "error";


        result.textContent =
            "No typing operation is active.";


        return;

    }


    stopButton.disabled =
        true;


    result.className =
        "muted";


    result.textContent =
        "Stopping typing...";


    try {

        const response =
            await fetch(

                "/stop-type/" +
                encodeURIComponent(
                    activeTypingDevice
                ),

                {

                    method:
                        "POST"

                }

            );


        const data =
            await response.json();


        if (!data.success) {

            throw new Error(

                data.message
                ||
                "Failed to stop typing."

            );

        }


        result.className =
            "success";


        result.textContent =
            "Typing stopped.";


        activeTypingDevice =
            null;


        typeButton.disabled =
            false;


        stopButton.disabled =
            true;


    } catch (error) {

        result.className =
            "error";


        result.textContent =
            error.message
            ||
            "Unable to stop typing.";


        stopButton.disabled =
            false;

    }

}


function escapeHtml(
    value
) {

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


function cssEscape(
    value
) {

    if (

        window.CSS

        &&

        typeof window.CSS.escape
        === "function"

    ) {

        return window.CSS.escape(
            value
        );

    }


    return String(value)
        .replace(
            /([^\w-])/g,
            "\\$1"
        );

}


loadPhoneInfo();


loadDevices();


setInterval(
    loadDevices,
    5000
);