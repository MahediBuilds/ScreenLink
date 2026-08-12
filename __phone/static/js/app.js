let connectedDevice = null;

let polling = false;

let activeTyping = false;


/* ========================================= */
/* INITIALIZATION                            */
/* ========================================= */

document.addEventListener(
    "DOMContentLoaded",
    function () {

        checkConnection();

        setInterval(
            checkConnection,
            2000
        );

    }
);


/* ========================================= */
/* CONNECTION                                */
/* ========================================= */

async function checkConnection() {

    if (polling) {

        return;

    }


    polling = true;


    try {

        const response =
            await fetch(
                "/devices",
                {
                    cache: "no-store"
                }
            );


        if (!response.ok) {

            throw new Error(
                "Server returned an error."
            );

        }


        const data =
            await response.json();


        if (
            !data.success
            ||
            !Array.isArray(
                data.devices
            )
        ) {

            showDisconnected();

            return;

        }


        const device =
            data.devices.find(
                function (item) {

                    return item.online === true;

                }
            );


        if (device) {

            showConnected(
                device
            );

        } else {

            showDisconnected();

        }


    } catch (error) {

        showDisconnected();

    } finally {

        polling = false;

    }

}


/* ========================================= */
/* CONNECTED                                 */
/* ========================================= */

function showConnected(
    device
) {

    connectedDevice =
        device;


    const connectingView =
        document.getElementById(
            "connectingView"
        );


    const controlView =
        document.getElementById(
            "controlView"
        );


    const indicator =
        document.getElementById(
            "connectionIndicator"
        );


    const status =
        document.getElementById(
            "connectionStatus"
        );


    const connectionText =
        document.getElementById(
            "connectionText"
        );


    const deviceInfo =
        document.getElementById(
            "deviceInfo"
        );


    connectingView.classList.add(
        "hidden"
    );


    controlView.classList.remove(
        "hidden"
    );


    indicator.className =
        "connection-indicator connected";


    status.textContent =
        "Connected";


    connectionText.textContent =
        "Laptop connected";


    deviceInfo.textContent =
        `${device.ip}:${device.port}`;

}


/* ========================================= */
/* DISCONNECTED                              */
/* ========================================= */

function showDisconnected() {

    connectedDevice =
        null;


    const connectingView =
        document.getElementById(
            "connectingView"
        );


    const controlView =
        document.getElementById(
            "controlView"
        );


    const indicator =
        document.getElementById(
            "connectionIndicator"
        );


    const status =
        document.getElementById(
            "connectionStatus"
        );


    const connectionText =
        document.getElementById(
            "connectionText"
        );


    connectingView.classList.remove(
        "hidden"
    );


    controlView.classList.add(
        "hidden"
    );


    indicator.className =
        "connection-indicator connecting";


    status.textContent =
        "Connecting";


    connectionText.textContent =
        "Connecting...";

}


/* ========================================= */
/* CLIPBOARD                                 */
/* ========================================= */

async function pasteInto(
    elementId
) {

    const element =
        document.getElementById(
            elementId
        );


    if (!element) {

        return;

    }


    try {

        const text =
            await navigator.clipboard.readText();


        if (!text) {

            return;

        }


        element.value =
            text;


        element.focus();


    } catch (error) {

        /*
         * Clipboard access can be denied by
         * the browser if permission has not
         * been granted.
         */

        element.focus();


        try {

            const success =
                document.execCommand(
                    "paste"
                );


            if (!success) {

                alert(
                    "Clipboard access was blocked. Please paste manually."
                );

            }

        } catch {

            alert(
                "Clipboard access was blocked. Please paste manually."
            );

        }

    }

}


/* ========================================= */
/* CLEAR TEXTBOX                             */
/* ========================================= */

function clearTextbox(
    elementId
) {

    const element =
        document.getElementById(
            elementId
        );


    if (!element) {

        return;

    }


    element.value = "";


    element.focus();


    if (
        elementId === "clickJson"
    ) {

        const result =
            document.getElementById(
                "clickResult"
            );


        if (result) {

            result.textContent =
                "";


            result.className =
                "result";

        }

    }


    if (
        elementId === "typeText"
    ) {

        const result =
            document.getElementById(
                "typeResult"
            );


        if (result) {

            result.textContent =
                "";


            result.className =
                "result";

        }

    }

}


/* ========================================= */
/* SCREENSHOT                                */
/* ========================================= */

async function takeScreenshot() {

    if (!connectedDevice) {

        return;

    }


    const button =
        document.getElementById(
            "screenshotButton"
        );


    const container =
        document.getElementById(
            "screenshotContainer"
        );


    const aiSection =
        document.getElementById(
            "aiClickSection"
        );


    button.disabled =
        true;


    button.textContent =
        "Capturing...";


    aiSection.classList.add(
        "hidden"
    );


    container.innerHTML = `

        <div class="loading-state">

            <div class="loader small"></div>

            <p>
                Capturing screenshot...
            </p>

        </div>

    `;


    try {

        const response =
            await fetch(

                "/screenshot/" +
                encodeURIComponent(
                    connectedDevice.name
                ) +
                "?t=" +
                Date.now(),

                {
                    cache: "no-store"
                }

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


                container.innerHTML = `

                    <div class="error-state">

                        Unable to display screenshot.

                    </div>

                `;

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

            <div class="error-state">

                ${escapeHtml(
                    error.message
                    ||
                    "Screenshot failed."
                )}

            </div>

        `;

    } finally {

        button.disabled =
            false;


        button.textContent =
            "Take Screenshot";

    }

}


/* ========================================= */
/* CHATGPT CLICK EXECUTION                   */
/* ========================================= */

async function executeClicks() {

    if (!connectedDevice) {

        return;

    }


    const input =
        document.getElementById(
            "clickJson"
        );


    const button =
        document.getElementById(
            "executeClickButton"
        );


    const result =
        document.getElementById(
            "clickResult"
        );


    const raw =
        input.value.trim();


    if (!raw) {

        showResult(

            result,

            "Paste the ChatGPT JSON first.",

            "error"

        );


        return;

    }


    let data;


    try {

        data =
            JSON.parse(
                raw
            );

    } catch {

        showResult(

            result,

            "Invalid JSON.",

            "error"

        );


        return;

    }


    if (
        !data
        ||
        !Array.isArray(
            data.steps
        )
    ) {

        showResult(

            result,

            "JSON must contain a steps array.",

            "error"

        );


        return;

    }


    if (
        data.steps.length === 0
    ) {

        showResult(

            result,

            "No click steps found.",

            "error"

        );


        return;

    }


    if (
        data.steps.length > 6
    ) {

        showResult(

            result,

            "Maximum 6 click steps allowed.",

            "error"

        );


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

            showResult(

                result,

                "Every step must use action: click.",

                "error"

            );


            return;

        }


        if (
            !step.point
            ||
            typeof step.point.x !== "number"
            ||
            typeof step.point.y !== "number"
        ) {

            showResult(

                result,

                "Every step needs a normalized point.",

                "error"

            );


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

            showResult(

                result,

                "Coordinates must be between 0 and 1000.",

                "error"

            );


            return;

        }

    }


    button.disabled =
        true;


    button.textContent =
        "Executing...";


    showResult(

        result,

        "Executing clicks...",

        "muted"

    );


    try {

        const response =
            await fetch(

                "/click/" +
                encodeURIComponent(
                    connectedDevice.name
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
            !response.ok
            ||
            !responseData.success
        ) {

            throw new Error(

                responseData.message
                ||
                "Click execution failed."

            );

        }


        showResult(

            result,

            `Executed ${
                responseData.executed || 0
            } click(s).`,

            "success"

        );


    } catch (error) {

        showResult(

            result,

            error.message
            ||
            "Unable to execute clicks.",

            "error"

        );

    } finally {

        button.disabled =
            false;


        button.textContent =
            "Execute Clicks";

    }

}


/* ========================================= */
/* TYPING                                    */
/* ========================================= */

async function startTyping() {

    if (!connectedDevice) {

        return;

    }


    const text =
        document.getElementById(
            "typeText"
        ).value;


    const result =
        document.getElementById(
            "typeResult"
        );


    const startButton =
        document.getElementById(
            "typeButton"
        );


    const stopButton =
        document.getElementById(
            "stopButton"
        );


    if (!text.trim()) {

        showResult(

            result,

            "Enter some text first.",

            "error"

        );


        return;

    }


    startButton.disabled =
        true;


    showResult(

        result,

        "Starting typing...",

        "muted"

    );


    try {

        const response =
            await fetch(

                "/type/" +
                encodeURIComponent(
                    connectedDevice.name
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


        if (
            !response.ok
            ||
            !data.success
        ) {

            throw new Error(

                data.message
                ||
                "Typing failed."

            );

        }


        activeTyping =
            true;


        stopButton.disabled =
            false;


        showResult(

            result,

            "Typing started.",

            "success"

        );


    } catch (error) {

        startButton.disabled =
            false;


        showResult(

            result,

            error.message
            ||
            "Unable to start typing.",

            "error"

        );

    }

}


/* ========================================= */
/* STOP TYPING                               */
/* ========================================= */

async function stopTyping() {

    if (
        !connectedDevice
        ||
        !activeTyping
    ) {

        return;

    }


    const result =
        document.getElementById(
            "typeResult"
        );


    const startButton =
        document.getElementById(
            "typeButton"
        );


    const stopButton =
        document.getElementById(
            "stopButton"
        );


    stopButton.disabled =
        true;


    showResult(

        result,

        "Stopping typing...",

        "muted"

    );


    try {

        const response =
            await fetch(

                "/stop-type/" +
                encodeURIComponent(
                    connectedDevice.name
                ),

                {

                    method:
                        "POST"

                }

            );


        const data =
            await response.json();


        if (
            !response.ok
            ||
            !data.success
        ) {

            throw new Error(

                data.message
                ||
                "Failed to stop typing."

            );

        }


        activeTyping =
            false;


        startButton.disabled =
            false;


        showResult(

            result,

            "Typing stopped.",

            "success"

        );


    } catch (error) {

        stopButton.disabled =
            false;


        showResult(

            result,

            error.message
            ||
            "Unable to stop typing.",

            "error"

        );

    }

}


/* ========================================= */
/* HELPERS                                   */
/* ========================================= */

function showResult(
    element,
    message,
    type
) {

    element.className =
        `result ${type}`;


    element.textContent =
        message;

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