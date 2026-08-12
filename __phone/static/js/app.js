let connectedDevice = null;

let polling = false;

let activeTyping = false;

let latestScreenshotBlob = null;

let latestScreenshotUrl = null;

let promptCache = {};


/* ========================================= */
/* PROMPT NAMES                              */
/* ========================================= */

const TASK_NAMES = {

    python:
        "Python",

    sql:
        "SQL",

    fill_blank:
        "Fill in the Blank",

    email:
        "Email",

    general:
        "General",

    custom:
        "Custom"

};


/* ========================================= */
/* INITIALIZATION                            */
/* ========================================= */

document.addEventListener(
    "DOMContentLoaded",
    async function () {

        await loadAllPrompts();

        checkConnection();

        setInterval(
            checkConnection,
            2000
        );

    }
);


/* ========================================= */
/* LOAD PROMPTS                              */
/* ========================================= */

async function loadAllPrompts() {

    const names = [

        "click",

        "python",

        "sql",

        "fill_blank",

        "email",

        "general",

        "custom"

    ];


    for (
        const name
        of names
    ) {

        try {

            const response =
                await fetch(
                    `/prompts/${name}?t=${Date.now()}`,
                    {
                        cache:
                            "no-store"
                    }
                );


            if (!response.ok) {

                throw new Error(
                    `Failed to load ${name}`
                );

            }


            promptCache[name] =
                await response.text();


        } catch (error) {

            console.error(
                `Unable to load prompt: ${name}`,
                error
            );


            promptCache[name] =
                "";

        }

    }


    document.getElementById(
        "clickPrompt"
    ).value =
        promptCache.click || "";


    changeTaskType();

}


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
                    cache:
                        "no-store"
                }
            );


        if (!response.ok) {

            throw new Error(
                "Server unavailable"
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
                item =>
                    item.online === true
            );


        if (device) {

            showConnected(
                device
            );

        } else {

            showDisconnected();

        }


    } catch {

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


    document.getElementById(
        "connectingView"
    ).classList.add(
        "hidden"
    );


    document.getElementById(
        "controlView"
    ).classList.remove(
        "hidden"
    );


    const indicator =
        document.getElementById(
            "connectionIndicator"
        );


    indicator.className =
        "connection-indicator connected";


    document.getElementById(
        "connectionStatus"
    ).textContent =
        "Connected";


    document.getElementById(
        "connectionText"
    ).textContent =
        "Laptop connected";


    document.getElementById(
        "deviceInfo"
    ).textContent =
        `${device.ip}:${device.port}`;

}


/* ========================================= */
/* DISCONNECTED                              */
/* ========================================= */

function showDisconnected() {

    connectedDevice =
        null;


    document.getElementById(
        "connectingView"
    ).classList.remove(
        "hidden"
    );


    document.getElementById(
        "controlView"
    ).classList.add(
        "hidden"
    );


    const indicator =
        document.getElementById(
            "connectionIndicator"
        );


    indicator.className =
        "connection-indicator connecting";


    document.getElementById(
        "connectionStatus"
    ).textContent =
        "Connecting";


    document.getElementById(
        "connectionText"
    ).textContent =
        "Connecting...";

}


/* ========================================= */
/* TASK TYPE                                 */
/* ========================================= */

function changeTaskType() {

    const select =
        document.getElementById(
            "taskType"
        );


    const type =
        select.value;


    const prompt =
        document.getElementById(
            "typingPrompt"
        );


    const title =
        document.getElementById(
            "typingPromptTitle"
        );


    const label =
        document.getElementById(
            "typingPromptLabel"
        );


    const customInfo =
        document.getElementById(
            "customPromptInfo"
        );


    title.textContent =
        `${TASK_NAMES[type]} Prompt`;


    if (
        type === "custom"
    ) {

        prompt.readOnly =
            false;


        prompt.value =
            promptCache.custom || "";


        prompt.placeholder =
            "Write your custom prompt here...";


        label.textContent =
            "Editable";


        label.classList.add(
            "editable"
        );


        customInfo.classList.remove(
            "hidden"
        );


    } else {

        prompt.readOnly =
            true;


        prompt.value =
            promptCache[type] || "";


        prompt.placeholder =
            "";


        label.textContent =
            "Fixed";


        label.classList.remove(
            "editable"
        );


        customInfo.classList.add(
            "hidden"
        );

    }

}


/* ========================================= */
/* GET PROMPT                                */
/* ========================================= */

function getPrompt(
    type
) {

    if (
        type === "click"
    ) {

        return document.getElementById(
            "clickPrompt"
        ).value.trim();

    }


    const selected =
        document.getElementById(
            "taskType"
        ).value;


    if (
        selected === "custom"
    ) {

        return document.getElementById(
            "typingPrompt"
        ).value.trim();

    }


    return (
        promptCache[selected]
        || ""
    ).trim();

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


    const actions =
        document.getElementById(
            "screenshotActions"
        );


    button.disabled =
        true;


    button.textContent =
        "Capturing...";


    actions.classList.add(
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


    latestScreenshotBlob =
        null;


    if (
        latestScreenshotUrl
    ) {

        URL.revokeObjectURL(
            latestScreenshotUrl
        );

        latestScreenshotUrl =
            null;

    }


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
                    cache:
                        "no-store"
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


        latestScreenshotBlob =
            blob;


        latestScreenshotUrl =
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


        image.src =
            latestScreenshotUrl;


        image.onload =
            function () {

                actions.classList.remove(
                    "hidden"
                );


                updateClickPromptDimensions(
                    image.naturalWidth,
                    image.naturalHeight
                );

            };


        image.onerror =
            function () {

                container.innerHTML = `

                    <div class="error-state">
                        Unable to display screenshot.
                    </div>

                `;

            };


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
/* CLICK PROMPT DIMENSIONS                   */
/* ========================================= */

function updateClickPromptDimensions(
    width,
    height
) {

    if (
        !promptCache.click
    ) {

        return;

    }


    let prompt =
        promptCache.click;


    prompt =
        prompt.replace(
            /\{screen_width\}/g,
            String(width)
        );


    prompt =
        prompt.replace(
            /\{screen_height\}/g,
            String(height)
        );


    document.getElementById(
        "clickPrompt"
    ).value =
        prompt;

}


/* ========================================= */
/* COPY IMAGE                                */
/* ========================================= */

async function copyImage() {

    if (
        !latestScreenshotBlob
    ) {

        showTemporaryMessage(
            "Take a screenshot first."
        );

        return;

    }


    if (
        !navigator.clipboard
        ||
        !window.ClipboardItem
    ) {

        showTemporaryMessage(
            "Image copying is not supported by this browser."
        );

        return;

    }


    try {

        const item =
            new ClipboardItem({

                "image/png":
                    latestScreenshotBlob

            });


        await navigator.clipboard.write(
            [item]
        );


        showTemporaryMessage(
            "Original screenshot copied."
        );


    } catch {

        showTemporaryMessage(
            "Unable to copy the image."
        );

    }

}


/* ========================================= */
/* COPY PROMPT                               */
/* ========================================= */

async function copyPrompt(
    type
) {

    const prompt =
        getPrompt(
            type
        );


    if (!prompt) {

        showTemporaryMessage(
            "Prompt is empty."
        );

        return;

    }


    try {

        await navigator.clipboard.writeText(
            prompt
        );


        showTemporaryMessage(
            "Prompt copied."
        );


    } catch {

        showTemporaryMessage(
            "Unable to copy the prompt."
        );

    }

}


/* ========================================= */
/* PASTE                                    */
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


    } catch {

        showTemporaryMessage(
            "Clipboard access was blocked. Use normal Android paste."
        );

    }

}


/* ========================================= */
/* CLEAR                                    */
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


    element.value =
        "";


    element.focus();


    if (
        elementId ===
        "clickJson"
    ) {

        clearResult(
            "clickResult"
        );

    }


    if (
        elementId ===
        "typeText"
    ) {

        clearResult(
            "typeResult"
        );

    }

}


/* ========================================= */
/* EXECUTE CLICKS                            */
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
/* START TYPING                              */
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
            "Paste the ChatGPT answer first.",
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
/* RESULT                                    */
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


function clearResult(
    elementId
) {

    const element =
        document.getElementById(
            elementId
        );


    if (!element) {

        return;

    }


    element.textContent =
        "";


    element.className =
        "result";

}


/* ========================================= */
/* TEMPORARY MESSAGE                         */
/* ========================================= */

let messageTimer = null;


function showTemporaryMessage(
    message
) {

    let element =
        document.getElementById(
            "temporaryMessage"
        );


    if (!element) {

        element =
            document.createElement(
                "div"
            );


        element.id =
            "temporaryMessage";


        element.className =
            "temporary-message";


        document.body.appendChild(
            element
        );

    }


    element.textContent =
        message;


    element.classList.add(
        "visible"
    );


    clearTimeout(
        messageTimer
    );


    messageTimer =
        setTimeout(

            function () {

                element.classList.remove(
                    "visible"
                );

            },

            2800

        );

}


/* ========================================= */
/* ESCAPE                                    */
/* ========================================= */

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