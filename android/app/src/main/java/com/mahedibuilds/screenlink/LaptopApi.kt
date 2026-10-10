package com.mahedibuilds.screenlink

import org.json.JSONException
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.IOException
import java.io.InputStream
import java.net.ConnectException
import java.net.HttpURLConnection
import java.net.NoRouteToHostException
import java.net.SocketTimeoutException
import java.net.URL
import java.net.UnknownHostException

/** A failure with a message that can be shown to the user as-is. */
open class LaptopException(message: String) : Exception(message)

/** The laptop answered but does not accept our token (not paired, or pairing reset). */
class NotPairedException(message: String) : LaptopException(message)

/** The laptop could not be reached or the transfer failed. */
class NetworkException(message: String) : LaptopException(message)

data class LaptopStatus(val hostname: String, val authorized: Boolean, val pairingEnabled: Boolean)

data class Screenshot(val jpeg: ByteArray, val width: Int, val height: Int)

data class TypingJob(val id: Int, val state: String, val typed: Int, val total: Int, val error: String?) {
    companion object {
        fun from(json: JSONObject) = TypingJob(
            id = json.getInt("id"),
            state = json.getString("state"),
            typed = json.getInt("typed"),
            total = json.getInt("total"),
            error = if (json.isNull("error")) null else json.getString("error"),
        )
    }
}

data class ClickResult(val clicked: Int, val screenWidth: Int, val screenHeight: Int)

/** Talks to the ScreenLink laptop client over HTTP. All calls block; run them off the main thread. */
class LaptopApi(private val host: String, private val port: Int, private val token: String?) {

    private val base = "http://${if (':' in host) "[$host]" else host}:$port"

    private class Response(val code: Int, val body: ByteArray, val headers: Map<String, String>) {
        fun json(): JSONObject = try {
            JSONObject(String(body, Charsets.UTF_8))
        } catch (e: JSONException) {
            throw LaptopException("Laptop sent an unexpected response (HTTP $code). Is this the ScreenLink client?")
        }
    }

    fun status(): LaptopStatus {
        val json = request("GET", "/status").json()
        if (json.optString("app") != "ScreenLink") {
            throw LaptopException("Something answered at $host:$port, but it is not the ScreenLink client.")
        }
        return LaptopStatus(
            hostname = json.optString("hostname", host),
            authorized = json.optBoolean("authorized"),
            pairingEnabled = json.optBoolean("pairing_enabled", true),
        )
    }

    /** Exchanges the pairing code shown in the laptop console for a long-lived token. */
    fun pair(code: String, deviceName: String): String {
        val body = JSONObject().put("code", code).put("device", deviceName)
        return request("POST", "/pair", body).json().getString("token")
    }

    fun screenshot(): Screenshot {
        val response = request("GET", "/screenshot", readTimeoutMs = 30_000, maxBytes = 40 * 1024 * 1024)
        if (response.headers["content-type"]?.startsWith("image/") != true) {
            throw LaptopException("Laptop did not return an image.")
        }
        if (response.body.isEmpty()) throw LaptopException("Laptop returned an empty screenshot.")
        return Screenshot(
            jpeg = response.body,
            width = response.headers["x-screen-width"]?.toIntOrNull() ?: 0,
            height = response.headers["x-screen-height"]?.toIntOrNull() ?: 0,
        )
    }

    fun startTyping(text: String): TypingJob {
        val body = JSONObject().put("text", text)
        return TypingJob.from(request("POST", "/type", body).json().getJSONObject("job"))
    }

    fun typingJob(): TypingJob = TypingJob.from(request("GET", "/type").json().getJSONObject("job"))

    fun cancelTyping(): TypingJob =
        TypingJob.from(request("POST", "/type/cancel", JSONObject()).json().getJSONObject("job"))

    fun click(clickRequest: JSONObject): ClickResult {
        val json = request("POST", "/click", clickRequest, readTimeoutMs = 30_000).json()
        val screen = json.getJSONArray("screen")
        return ClickResult(json.getInt("clicked"), screen.getInt(0), screen.getInt(1))
    }

    private fun request(
        method: String,
        path: String,
        body: JSONObject? = null,
        readTimeoutMs: Int = 10_000,
        maxBytes: Int = 1024 * 1024,
    ): Response {
        val connection = try {
            URL(base + path).openConnection() as HttpURLConnection
        } catch (e: Exception) {
            throw LaptopException("Invalid laptop address: $host")
        }
        try {
            connection.requestMethod = method
            connection.connectTimeout = 5_000
            connection.readTimeout = readTimeoutMs
            connection.useCaches = false
            token?.let { connection.setRequestProperty("Authorization", "Bearer $it") }
            if (body != null) {
                val bytes = body.toString().toByteArray(Charsets.UTF_8)
                connection.doOutput = true
                connection.setRequestProperty("Content-Type", "application/json")
                connection.setFixedLengthStreamingMode(bytes.size)
                connection.outputStream.use { it.write(bytes) }
            }

            val code = connection.responseCode
            val stream = if (code >= 400) connection.errorStream else connection.inputStream
            val data = stream?.use { readFully(it, maxBytes) } ?: ByteArray(0)
            val expected = connection.contentLengthLong
            if (expected >= 0 && data.size.toLong() != expected) {
                throw NetworkException("Transfer was interrupted (${data.size} of $expected bytes). Try again.")
            }
            val headers = connection.headerFields
                .filterKeys { it != null }
                .mapKeys { it.key.lowercase() }
                .mapValues { it.value.firstOrNull().orEmpty() }
            val response = Response(code, data, headers)

            if (code >= 400) {
                val message = runCatching { response.json().optString("error") }.getOrNull()
                    ?.takeIf { it.isNotBlank() } ?: "Laptop returned HTTP $code."
                if (code == 401) throw NotPairedException(message)
                throw LaptopException(message)
            }
            return response
        } catch (e: LaptopException) {
            throw e
        } catch (e: SocketTimeoutException) {
            throw NetworkException(
                "No response from $host:$port. Check that the laptop client is running, both devices are on " +
                    "the same Wi-Fi, Windows Firewall allows the port, and the network does not isolate devices."
            )
        } catch (e: ConnectException) {
            throw NetworkException(
                "Could not connect to $host:$port (${e.message}). Is the laptop client running on this port, " +
                    "and is the IP address correct?"
            )
        } catch (e: NoRouteToHostException) {
            throw NetworkException("No route to $host. The phone and laptop are probably on different networks.")
        } catch (e: UnknownHostException) {
            throw LaptopException("Invalid laptop address: $host")
        } catch (e: IOException) {
            throw NetworkException("Network error talking to $host:$port: ${e.message ?: e.javaClass.simpleName}")
        } finally {
            connection.disconnect()
        }
    }

    private fun readFully(input: InputStream, maxBytes: Int): ByteArray {
        val out = ByteArrayOutputStream()
        val buffer = ByteArray(64 * 1024)
        while (true) {
            val n = input.read(buffer)
            if (n < 0) break
            out.write(buffer, 0, n)
            if (out.size() > maxBytes) throw LaptopException("Response from laptop is too large.")
        }
        return out.toByteArray()
    }
}
