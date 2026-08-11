```javascript
let laptopOnline = false;

let activeTyping = false;

let screenshotObjectUrl = null;


async function loadPhoneInfo() {

    try {

        const response =
            await fetch(
                "/status",
                {
                    cache: "no-store"
                }
            );

        const data =
            await response.json();

        if (!data.success) {
            return;
        }

    } catch (error) {

        console.error(
            "Phone status error:",
            error
        );

    }
}


async function loadDevice() {

    try {

        const response =
            await fetch(
                "/device",
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

        if (!data.success) {

            setDisconnected();

            return;
        }

        if (data.device && data.device.online) {

            setConnected();

        } else {

            setDisconnected();

        }

    } catch (error) {

        console.error(
            "Device status error:",
            error
        );

        setDisconnected();

    }
}


function setConnected() {

    if (laptopOnline) {
        return;
    }

    laptopOnline = true;


    const connectingView =
        document.getElementById(
            "connectingView"
        );

    const controlView =
        document.getElementById(
            "controlView"
        );

    const connectionStatus =
        document.getElementById(
            "connectionStatus"
        );

    const connectionText =
        document.getElementById(
            "connectionText"
        );

    const typeButton =
        document.getElementById(
            "typeButton"
        );


    connectingView.classList.add(
        "hidden"
    );

    controlView.classList.remove(
        "hidden"
    );


    connectionStatus.className =
        "connection-status connected";


    connectionText.textContent =
        "Connected";


    if (!activeTyping) {

        typeButton.disabled =
            false;

    }

}


function setDisconnected() {

    if (!laptopOnline) {
        return;
    }

    laptopOnline = false;


    const connectingView =
        document.getElementById(
            "connectingView"
        );

    const controlView =
        document.getElementById(
            "controlView"
        );

    const connectionStatus =
        document.getElementById(
            "connectionStatus"
        );

    const connectionText =
        document.getElementById(
            "connectionText"
        );

    const typeButton =
        document.getElementById(
            "typeButton"
        );

    const stopButton =
        document.getElementById(
            "stopButton"
        );


    connectingView.classList.remove(
        "hidden"
    );

    controlView.classList.add(
        "hidden"
    );


    connectionStatus.className =
        "connection-status connecting";


    connectionText.textContent =
        "Connecting...";


    typeButton.disabled =
        true;

    stopButton.disabled =
        true;


    activeTyping = false;


    clearScreenshot();

}


async function takeScreenshot() {

    const button =
        document.getElementById(
            "screenshotButton"
        );

    const result =
        document.getElementById(
            "screenshotResult"
        );


    if (!laptopOnline) {

        return;

    }


    button.disabled =
        true;


    button.querySelector(
        "span"
    ).textContent =
        "Capturing...";


    clearScreenshot();


    const loading =
        document.createElement(
            "div"
        );

    loading.className =
        "screenshot-loading";

    loading.textContent =
        "Capturing screenshot...";


    result.appendChild(
        loading
    );


    try {

        const response =
            await fetch(
                "/screenshot",
                {
                    method: "GET",

                    cache: "no-store"
                }
            );


        if (!response.ok) {

            let message =
                "Screenshot capture failed.";

            try {

                const data =
                    await response.json();

                if (data.message) {

                    message =
                        data.message;

                }

            } catch (error) {}

            throw new Error(
                message
            );

        }


        const blob =
            await response.blob();


        if (!blob.size) {

            throw new Error(
                "Laptop returned an empty screenshot."
            );

        }


        const imageUrl =
            URL.createObjectURL(
                blob
            );


        screenshotObjectUrl =
            imageUrl;


        const wrapper =
            document.createElement(
                "div"
            );

        wrapper.className =
            "screenshot-wrapper";


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

                if (
                    loading.parentNode
                ) {

                    loading.remove();

                }

            };


        image.onerror =
            function () {

                if (
                    loading.parentNode
                ) {

                    loading.remove();

                }


                if (
                    screenshotObjectUrl
                    === imageUrl
                ) {

                    URL.revokeObjectURL(
                        screenshotObjectUrl
                    );

                    screenshotObjectUrl =
                        null;

                }


                wrapper.remove();


                const error =
                    document.createElement(
                        "div"
                    );

                error.className =
                    "screenshot-error";

                error.textContent =
                    "Unable to display the screenshot.";

                result.appendChild(
                    error
                );

            };


        image.src =
            imageUrl;


        wrapper.appendChild(
            image
        );


        result.appendChild(
            wrapper
        );


        image.decode()
            .catch(
                function () {}
            );


    } catch (error) {

        clearScreenshot();


        const errorElement =
            document.createElement(
                "div"
            );

        errorElement.className =
            "screenshot-error";

        errorElement.textContent =
            error.message ||
            "Screenshot capture failed.";


        result.appendChild(
            errorElement
        );

    } finally {

        button.disabled =
            !laptopOnline;


        button.querySelector(
            "span"
        ).textContent =
            "Take Screenshot";

    }
}


function clearScreenshot() {

    const result =
        document.getElementById(
            "screenshotResult"
        );


    if (
        screenshotObjectUrl
    ) {

        URL.revokeObjectURL(
            screenshotObjectUrl
        );

        screenshotObjectUrl =
            null;

    }


    result.innerHTML = "";

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
            "result error";

        result.textContent =
            "Enter some text first.";

        return;

    }


    if (!laptopOnline) {

        result.className =
            "result error";

        result.textContent =
            "Laptop is not connected.";

        return;

    }


    result.className =
        "result muted";

    result.textContent =
        "Starting typing...";


    typeButton.disabled =
        true;

    stopButton.disabled =
        true;


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


        activeTyping =
            true;


        result.className =
            "result success";

        result.textContent =
            "Typing started.";


        stopButton.disabled =
            false;


    } catch (error) {

        result.className =
            "result error";

        result.textContent =
            error.message ||
            "Unable to start typing.";


        activeTyping =
            false;


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

        return;

    }


    stopButton.disabled =
        true;


    result.className =
        "result muted";

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


        activeTyping =
            false;


        result.className =
            "result success";

        result.textContent =
            "Typing stopped.";


        typeButton.disabled =
            !laptopOnline;

        stopButton.disabled =
            true;


    } catch (error) {

        result.className =
            "result error";

        result.textContent =
            error.message ||
            "Unable to stop typing.";


        stopButton.disabled =
            false;

    }

}


loadPhoneInfo();

loadDevice();


setInterval(
    loadDevice,
    3000
);
```
