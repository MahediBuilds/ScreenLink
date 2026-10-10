package com.mahedibuilds.screenlink

import android.app.Application
import android.content.Context
import android.graphics.BitmapFactory
import android.os.Build
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.text.DateFormat
import java.util.Date

enum class ConnState { NOT_CONNECTED, CHECKING, CONNECTED, NOT_PAIRED, FAILED }

enum class MessageKind { INFO, SUCCESS, ERROR }

data class OpMessage(val kind: MessageKind, val text: String)

class ScreenLinkViewModel(application: Application) : AndroidViewModel(application) {

    private val prefs = application.getSharedPreferences("screenlink", Context.MODE_PRIVATE)
    private var token: String? = prefs.getString(KEY_TOKEN, null)
        set(value) {
            field = value
            hasToken = value != null
        }
    private var hasToken by mutableStateOf(token != null)

    // Connection
    var host by mutableStateOf(prefs.getString(KEY_HOST, "") ?: ""); private set
    var port by mutableStateOf(prefs.getInt(KEY_PORT, 5001).toString()); private set
    var connState by mutableStateOf(ConnState.NOT_CONNECTED); private set
    var connMessage by mutableStateOf("Enter the laptop's IP address and tap Connect."); private set
    var laptopName by mutableStateOf<String?>(null); private set
    var pairingCode by mutableStateOf("")

    // Screenshot
    var screenshot by mutableStateOf<Screenshot?>(null); private set
    var screenshotImage by mutableStateOf<ImageBitmap?>(null); private set
    var screenshotTime by mutableStateOf<String?>(null); private set
    var screenshotLoading by mutableStateOf(false); private set
    var screenshotError by mutableStateOf<String?>(null); private set

    // Prompts: the file-based tabs are read from assets/prompts each time the app starts.
    val prompts: List<Prompt> = PromptLibrary.load(
        list = { application.assets.list(PromptLibrary.FOLDER)?.toList().orEmpty() },
        read = { file ->
            application.assets.open("${PromptLibrary.FOLDER}/$file").bufferedReader().use { it.readText() }
        },
    )

    /** Name of the selected file-based prompt, or null when the Custom tab is selected. */
    var selectedPrompt by mutableStateOf(initialPromptSelection()); private set
    val isCustomSelected get() = selectedPrompt == null
    var customPrompt by mutableStateOf(
        prefs.getString(KEY_CUSTOM_PROMPT, null) ?: application.getString(R.string.custom_prompt_default)
    ); private set

    // Response and desktop actions
    var response by mutableStateOf("")
    var typingJob by mutableStateOf<TypingJob?>(null); private set
    var typingActive by mutableStateOf(false); private set
    var cancelRequested by mutableStateOf(false); private set
    var clickBusy by mutableStateOf(false); private set
    var message by mutableStateOf<OpMessage?>(null); private set

    /** Paired and not mid-check. Actions are allowed after a failure too; a success reconnects. */
    val isReady get() = hasToken && connState != ConnState.CHECKING && connState != ConnState.NOT_PAIRED
    val actionBusy get() = typingActive || clickBusy

    init {
        if (host.isNotBlank()) connect()
    }

    // ----- connection -------------------------------------------------------

    private fun api(): LaptopApi? {
        val p = port.toIntOrNull()
        if (host.isBlank() || p == null || p !in 1..65535) {
            connState = ConnState.FAILED
            connMessage = "Enter a valid IP address and port (1-65535)."
            return null
        }
        return LaptopApi(host.trim(), p, token)
    }

    fun updateAddress(newHost: String = host, newPort: String = port) {
        if (newHost == host && newPort == port) return
        host = newHost
        port = newPort
        if (connState != ConnState.CHECKING) {
            connState = ConnState.NOT_CONNECTED
            connMessage = "Address changed. Tap Connect."
        }
    }

    fun connect() {
        val api = api() ?: return
        prefs.edit().putString(KEY_HOST, host.trim()).putInt(KEY_PORT, port.toInt()).apply()
        connState = ConnState.CHECKING
        connMessage = "Contacting ${host.trim()}:$port..."
        viewModelScope.launch {
            try {
                val status = io { api.status() }
                laptopName = status.hostname
                if (status.authorized) {
                    connState = ConnState.CONNECTED
                    connMessage = "Connected to ${status.hostname}."
                } else {
                    connState = ConnState.NOT_PAIRED
                    connMessage = if (status.pairingEnabled) {
                        "Reached ${status.hostname}, but this phone is not paired. Enter the pairing code shown in the laptop console."
                    } else {
                        "Reached ${status.hostname}, but pairing is locked after too many wrong codes. Restart the laptop client."
                    }
                }
            } catch (e: LaptopException) {
                connState = ConnState.FAILED
                connMessage = e.message ?: "Connection failed."
            }
        }
    }

    fun pair() {
        val api = api() ?: return
        val code = pairingCode.trim()
        if (code.isEmpty()) {
            connMessage = "Enter the pairing code shown in the laptop console."
            return
        }
        connState = ConnState.CHECKING
        connMessage = "Pairing..."
        viewModelScope.launch {
            try {
                val newToken = io { api.pair(code, "${Build.MANUFACTURER} ${Build.MODEL}") }
                token = newToken
                prefs.edit().putString(KEY_TOKEN, newToken).apply()
                pairingCode = ""
                connect()
            } catch (e: LaptopException) {
                connState = if (e is NetworkException) ConnState.FAILED else ConnState.NOT_PAIRED
                connMessage = e.message ?: "Pairing failed."
            }
        }
    }

    fun forgetPairing() {
        token = null
        prefs.edit().remove(KEY_TOKEN).apply()
        connState = ConnState.NOT_PAIRED
        connMessage = "Pairing removed from this phone. Enter a new pairing code to pair again."
    }

    private fun markConnected() {
        connState = ConnState.CONNECTED
        connMessage = "Connected to ${laptopName ?: host}."
    }

    /** Updates connection state after a failed action so the status card stays truthful. */
    private fun onActionError(e: LaptopException, what: String) {
        when (e) {
            is NotPairedException -> {
                connState = ConnState.NOT_PAIRED
                connMessage = e.message ?: "Not paired."
            }
            is NetworkException -> {
                connState = ConnState.FAILED
                connMessage = e.message ?: "Lost connection."
            }
            else -> Unit
        }
        message = OpMessage(MessageKind.ERROR, "$what failed: ${e.message}")
    }

    // ----- screenshot -------------------------------------------------------

    fun takeScreenshot() {
        val api = api() ?: return
        screenshotLoading = true
        screenshotError = null
        viewModelScope.launch {
            try {
                val shot = io { api.screenshot() }
                val image = io { decode(shot.jpeg) }
                    ?: throw LaptopException("Laptop sent image data that could not be decoded.")
                screenshot = shot
                screenshotImage = image
                screenshotTime = DateFormat.getTimeInstance(DateFormat.MEDIUM).format(Date())
                markConnected()
            } catch (e: LaptopException) {
                screenshotError = e.message
                onActionError(e, "Screenshot")
            } finally {
                screenshotLoading = false
            }
        }
    }

    /** Decodes for display, downsampling very large screens to keep memory reasonable. */
    private fun decode(jpeg: ByteArray): ImageBitmap? {
        val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        BitmapFactory.decodeByteArray(jpeg, 0, jpeg.size, bounds)
        if (bounds.outWidth <= 0 || bounds.outHeight <= 0) return null
        var sample = 1
        while (maxOf(bounds.outWidth, bounds.outHeight) / sample > MAX_DISPLAY_PX) sample *= 2
        val options = BitmapFactory.Options().apply { inSampleSize = sample }
        return BitmapFactory.decodeByteArray(jpeg, 0, jpeg.size, options)?.asImageBitmap()
    }

    // ----- prompts ----------------------------------------------------------

    /** Restores the last tab if its file still exists; otherwise the first file tab, or Custom if there are none. */
    private fun initialPromptSelection(): String? {
        val stored = prefs.getString(KEY_PROMPT, null)
        if (stored == CUSTOM_SELECTION || stored == "CUSTOM") return null
        // Selections saved before prompts moved to files used enum names; most already match a file name.
        val saved = when (stored) {
            "CLICK" -> "GUI"
            "FILL_BLANK" -> "Fill_in_the_blank"
            else -> stored
        }
        return prompts.firstOrNull { it.name.equals(saved, ignoreCase = true) }?.name ?: prompts.firstOrNull()?.name
    }

    /** Selects a file-based prompt by name, or the Custom tab when [name] is null. */
    fun selectPrompt(name: String?) {
        selectedPrompt = name
        prefs.edit().putString(KEY_PROMPT, name ?: CUSTOM_SELECTION).apply()
    }

    fun updateCustomPrompt(text: String) {
        customPrompt = text
        prefs.edit().putString(KEY_CUSTOM_PROMPT, text).apply()
    }

    fun resetCustomPrompt() =
        updateCustomPrompt(getApplication<Application>().getString(R.string.custom_prompt_default))

    private fun selectedFilePrompt(): Prompt? = prompts.firstOrNull { it.name == selectedPrompt }

    fun promptText(): String = if (isCustomSelected) customPrompt else selectedFilePrompt()?.text.orEmpty()

    fun promptLabel(): String = if (isCustomSelected) CUSTOM_LABEL else selectedFilePrompt()?.label.orEmpty()

    // ----- text entry -------------------------------------------------------

    fun sendText() {
        val text = response
        if (text.isBlank()) {
            message = OpMessage(MessageKind.ERROR, "Paste the AI response first.")
            return
        }
        val api = api() ?: return
        typingActive = true
        cancelRequested = false
        typingJob = null
        message = OpMessage(MessageKind.INFO, "Sending text to the laptop...")
        viewModelScope.launch {
            var job: TypingJob? = null
            try {
                job = io { api.startTyping(text) }
                typingJob = job
                message = OpMessage(MessageKind.INFO, "Laptop accepted job #${job.id}. Typing ${job.total} characters...")
                while (job!!.state == "typing") {
                    delay(POLL_MS)
                    job = io { api.typingJob() }
                    typingJob = job
                }
                markConnected()
                message = when (job.state) {
                    "done" -> OpMessage(MessageKind.SUCCESS, "Laptop typed all ${job.total} characters.")
                    "cancelled" -> OpMessage(MessageKind.INFO, "Typing cancelled after ${job.typed} of ${job.total} characters.")
                    else -> OpMessage(MessageKind.ERROR, job.error ?: "Typing failed on the laptop.")
                }
            } catch (e: LaptopException) {
                if (job == null) {
                    onActionError(e, "Sending text")
                } else {
                    onActionError(e, "Checking typing progress")
                    message = OpMessage(
                        MessageKind.ERROR,
                        "Lost contact while the laptop was typing (job #${job.id}, ${job.typed}/${job.total}). " +
                            "It may still be typing. ${e.message}"
                    )
                }
            } finally {
                typingActive = false
                cancelRequested = false
            }
        }
    }

    fun cancelTyping() {
        val api = api() ?: return
        cancelRequested = true
        viewModelScope.launch {
            try {
                io { api.cancelTyping() }
                // The polling loop in sendText() reports the final state.
            } catch (e: LaptopException) {
                cancelRequested = false
                onActionError(e, "Cancel")
            }
        }
    }

    // ----- clicks -----------------------------------------------------------

    /** Parses the response for the click preview; returns the steps or an error message. */
    fun parseClicks(): Result<ParsedClicks> = runCatching { ClickParser.parse(response) }

    fun executeClicks() {
        val parsed = parseClicks().getOrElse {
            message = OpMessage(MessageKind.ERROR, it.message ?: "Invalid click response.")
            return
        }
        val api = api() ?: return
        clickBusy = true
        message = OpMessage(MessageKind.INFO, "Sending ${parsed.steps.size} click(s) to the laptop...")
        viewModelScope.launch {
            try {
                val result = io { api.click(parsed.request) }
                markConnected()
                message = OpMessage(
                    MessageKind.SUCCESS,
                    "Laptop clicked ${result.clicked} point(s) on its ${result.screenWidth}x${result.screenHeight} screen."
                )
            } catch (e: LaptopException) {
                onActionError(e, "Clicking")
            } finally {
                clickBusy = false
            }
        }
    }

    fun showMessage(kind: MessageKind, text: String) {
        message = OpMessage(kind, text)
    }

    private suspend fun <T> io(block: () -> T): T = withContext(Dispatchers.IO) { block() }

    companion object {
        private const val KEY_HOST = "host"
        private const val KEY_PORT = "port"
        private const val KEY_TOKEN = "token"
        private const val KEY_PROMPT = "prompt"
        private const val CUSTOM_SELECTION = "custom"  // no file tab can be named Custom
        const val CUSTOM_LABEL = "Custom"
        private const val KEY_CUSTOM_PROMPT = "custom_prompt"
        private const val POLL_MS = 300L
        private const val MAX_DISPLAY_PX = 2560
    }
}
