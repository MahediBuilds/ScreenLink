let connectedDevice = null;

let polling = false;

let activeTyping = false;

let latestScreenshotBlob = null;

let latestScreenshotUrl = null;


/* ========================================= */
/* PROMPTS                                   */
/* ========================================= */

const CLICK_PROMPT = `
You are an expert GUI vision agent.

The screenshot resolution is:

Width = {screen_width}
Height = {screen_height}

The screenshot contains a benchmark application.

Read the instruction shown at the top.

The instruction may require selecting ONE object or MULTIPLE objects.

Your job is to identify every object that should be clicked.

Return ONLY valid JSON.

Format:

{
  "steps": [
    {
      "action": "click",
      "target": "Circle",
      "confidence": 0.99,
      "point": {
        "x": 0,
        "y": 0
      }
    }
  ]
}

Rules:

- Return ONE click step for EVERY object that must be selected.
- If multiple objects satisfy the instruction, include multiple click steps.
- Preserve the logical order of clicks.
- Identify the center point of the object that should be clicked.
- Coordinates must be NORMALIZED from 0 to 1000.
- x represents horizontal position.
- y represents vertical position.
- x=0 is the far left of the screenshot.
- x=1000 is the far right of the screenshot.
- y=0 is the top of the screenshot.
- y=1000 is the bottom of the screenshot.
- Confidence should be between 0 and 1.
- Return JSON ONLY.
- No markdown.
- No explanations.

Example:

{
  "steps": [
    {
      "action": "click",
      "target": "Java",
      "confidence": 0.99,
      "point": {
        "x": 366,
        "y": 347
      }
    }
  ]
}
`.trim();


const PROMPTS = {

    python: `
You are an expert Python programmer.

Analyze the screenshot carefully.

Read the complete programming question shown in the screenshot.

Determine exactly what the question is asking.

Write the correct Python solution.

Return ONLY the Python code required to solve the problem.

Do not provide explanations.

Do not provide markdown code fences.

Do not include comments unless comments are explicitly required.

Make sure the code is complete and directly executable.
`.trim(),


    sql: `
You are an expert SQL programmer.

Analyze the screenshot carefully.

Read the database schema, tables, columns, relationships, and question shown in the screenshot.

Determine exactly what SQL query is required.

Return ONLY the SQL query.

Do not provide explanations.

Do not provide markdown code fences.

Do not include additional text.

Make sure the query directly answers the question.
`.trim(),


    fill_blank: `
Analyze the screenshot carefully.

Read the complete question and identify exactly what belongs in the blank.

Return ONLY the answer that should replace the blank.

Do not provide explanations.

Do not repeat the question.

Do not include markdown.

Do not write phrases such as "The answer is".

Return only the required answer.
`.trim(),


    email: `
You are an expert professional email writer.

Analyze the screenshot carefully.

Read the complete instructions shown in the screenshot.

Write the appropriate email based on those instructions.

Return ONLY the complete email.

Do not provide explanations.

Do not provide markdown.

Do not describe what you are doing.

Use an appropriate professional tone unless the screenshot specifically requests a different tone.
`.trim(),


    general: `
Analyze the screenshot carefully.

Read the complete question or task shown in the screenshot.

Determine exactly what is being asked.

Provide the correct answer.

Return ONLY the answer required by the question.

Do not provide unnecessary explanations.

Do not include markdown unless it is explicitly required by the question.
`.trim()

};


const TASK_NAMES = {

    python: "Python",

    sql: "SQL",

    fill_blank: "Fill in the Blank",

    email: "Email",

    general: "General",

    custom: "Custom"

};


/* ========================================= */
/* INITIALIZATION                            */
/* ========================================= */

document.addEventListener(
    "DOMContentLoaded",
    function () {

        document.getElementById(
            "clickPrompt"
        ).value = CLICK_PROMPT;


        changeTaskType();


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
/* TASK TYPE                                 */
/* ========================================= */

function changeTaskType() {

    const select =
        document.getElementById(
            "taskType"
        );


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


    const type =
        select.value;


    title.textContent =
        `${TASK_NAMES[type]} Prompt`;


    if (
        type === "custom"
    ) {

        prompt.readOnly =
            false;


        prompt.value =
            "";


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
            PROMPTS[type];


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
/* ACTIVE PROMPT                             */
/* ========================================= */

function getPrompt(
    type
) {

    if (
        type === "click"
    ) {

        return CLICK_PROMPT;

    }


    const select =
        document.getElementById(
            "taskType"
        );


    const selectedType =
        select.value;


    if (
        selectedType === "custom"
    ) {

        return document.getElementById(
            "typingPrompt"
        ).value.trim();

    }


    return PROMPTS[
        selectedType
    ];

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


    container.innerHTML = `

        <div class="loading-state">

            <div class="loader small"></div>

            <p>
                Capturing screenshot...
            </p>

        </div>

    `;


    actions.classList.add(
        "hidden"
    );


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


        /*
         * Keep the ORIGINAL PNG blob.
         *
         * The displayed image may be scaled
         * by CSS, but this blob remains the
         * original screenshot received from
         * the laptop.
         */

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
            "Image clipboard is not supported by this browser."
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


    } catch (error) {

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


    } catch (error) {

        showTemporaryMessage(
            "Unable to copy the prompt."
        );

    }

}


/* ========================================= */
/* COPY IMAGE + PROMPT                       */
/* ========================================= */

async function copyImageAndPrompt(
    type
) {

    if (
        !latestScreenshotBlob
    ) {

        showTemporaryMessage(
            "Take a screenshot first."
        );

        return;

    }


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


    if (
        !navigator.clipboard
        ||
        !window.ClipboardItem
    ) {

        showTemporaryMessage(
            "Combined clipboard is not supported. Use Copy Image and Copy Prompt separately."
        );

        return;

    }


    try {

        const textBlob =
            new Blob(
                [prompt],
                {
                    type:
                        "text/plain"
                }
            );


        const item =
            new ClipboardItem({

                "image/png":
                    latestScreenshotBlob,

                "text/plain":
                    textBlob

            });


        await navigator.clipboard.write(
            [item]
        );


        showTemporaryMessage(
            "Image + prompt copied."
        );


    } catch (error) {

        showTemporaryMessage(
            "Combined copy failed. Use Copy Image and Copy Prompt separately."
        );

    }

}


/* ========================================= */
/* SHARE IMAGE + PROMPT                      */
/* ========================================= */

async function shareImageAndPrompt(
    type
) {

    if (
        !latestScreenshotBlob
    ) {

        showTemporaryMessage(
            "Take a screenshot first."
        );

        return;

    }


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


    if (
        !navigator.share
    ) {

        showTemporaryMessage(
            "Sharing is not supported by this browser."
        );

        return;

    }


    try {

        const file =
            new File(

                [
                    latestScreenshotBlob
                ],

                "ScreenLink_Screenshot.png",

                {
                    type:
                        "image/png"
                }

            );


        const shareData = {

            title:
                "ScreenLink",

            text:
                prompt,

            files:
                [file]

        };


        if (
            navigator.canShare
            &&
            !navigator.canShare(
                shareData
            )
        ) {

            throw new Error(
                "Files cannot be shared."
            );

        }


        await navigator.share(
            shareData
        );


    } catch (error) {

        if (
            error.name ===
            "AbortError"
        ) {

            return;

        }


        showTemporaryMessage(
            "Unable to share image and prompt."
        );

    }

}


/* ========================================= */
/* CLIPBOARD PASTE                           */
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

        element.focus();


        showTemporaryMessage(
            "Clipboard access was blocked. Use the keyboard paste option."
        );

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
/* RESULT HELPERS                            */
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
/* HTML ESCAPING                             */
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