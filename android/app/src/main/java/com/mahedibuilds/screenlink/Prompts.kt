package com.mahedibuilds.screenlink

import org.json.JSONArray
import org.json.JSONException
import org.json.JSONObject

/** A prompt loaded from assets/prompts/<name>.txt. */
data class Prompt(val name: String, val label: String, val text: String)

/**
 * Built-in prompts are the .txt files in app/src/main/assets/prompts/. Each file becomes one tab:
 * General first, Python second, GUI third, then the rest alphabetically (case-insensitive).
 * The Custom tab is not a file; it is added by the UI and stored in the app's preferences.
 */
object PromptLibrary {
    const val FOLDER = "prompts"
    private val PINNED = listOf("general", "python", "gui")

    /**
     * Loads every non-empty prompt. [list] returns the file names in the folder and [read] returns a
     * file's contents; both come from the AssetManager in the app and from fakes in tests.
     */
    fun load(list: () -> List<String>, read: (String) -> String): List<Prompt> {
        val files = runCatching { list() }.getOrDefault(emptyList())
            .filter { it.endsWith(".txt", ignoreCase = true) }
        val byName = linkedMapOf<String, String>()  // lowercase name -> file name; first wins
        for (file in files.sorted()) {
            val name = file.dropLast(4).trim()
            // Custom is always the editable tab, never a file-based one.
            if (name.isEmpty() || name.equals("custom", ignoreCase = true)) continue
            byName.putIfAbsent(name.lowercase(), file)
        }
        return order(byName.values.map { it.dropLast(4).trim() }).mapNotNull { name ->
            val text = runCatching { read(byName.getValue(name.lowercase())) }.getOrNull()
                ?.replace("\r\n", "\n")?.trim()
            if (text.isNullOrEmpty()) null else Prompt(name, label(name), text)
        }
    }

    /** General, Python, GUI first (when present), then the rest case-insensitively. */
    fun order(names: List<String>): List<String> = names.sortedWith(
        compareBy<String>(
            { PINNED.indexOf(it.lowercase()).let { i -> if (i < 0) PINNED.size else i } },
            { it.lowercase() },
            { it },
        )
    )

    /** "My_prompt" -> "My prompt"; the file name itself is unchanged. */
    fun label(name: String): String =
        name.replace('_', ' ').replace('-', ' ').replace(Regex("\\s+"), " ").trim()
}

data class ClickStep(val target: String, val x: Double, val y: Double)

data class ParsedClicks(val request: JSONObject, val steps: List<ClickStep>)

/**
 * Turns an AI reply to the click prompt into the laptop's click request:
 *   {"steps": [{"action": "click", "target": "...", "point": {"x": 0-1000, "y": 0-1000}}]}
 * Tolerates markdown code fences and text around the JSON. The laptop validates again.
 */
object ClickParser {
    fun parse(reply: String): ParsedClicks {
        val start = reply.indexOf('{')
        val end = reply.lastIndexOf('}')
        if (start < 0 || end <= start) throw IllegalArgumentException("No JSON object found in the response.")
        val root = try {
            JSONObject(reply.substring(start, end + 1))
        } catch (e: JSONException) {
            throw IllegalArgumentException("Response is not valid JSON: ${e.message}")
        }
        val steps = root.optJSONArray("steps")
            ?: throw IllegalArgumentException("JSON has no \"steps\" list.")
        if (steps.length() == 0) throw IllegalArgumentException("\"steps\" is empty.")

        val parsed = mutableListOf<ClickStep>()
        val clean = JSONArray()
        for (i in 0 until steps.length()) {
            val n = i + 1
            val step = steps.optJSONObject(i) ?: throw IllegalArgumentException("Step $n is not an object.")
            if (step.optString("action") != "click") {
                throw IllegalArgumentException("Step $n: only \"click\" actions are supported.")
            }
            val point = step.optJSONObject("point") ?: throw IllegalArgumentException("Step $n has no point.")
            val x = coordinate(point, "x", n)
            val y = coordinate(point, "y", n)
            val target = step.optString("target", "")
            parsed += ClickStep(target, x, y)
            clean.put(
                JSONObject()
                    .put("action", "click")
                    .put("target", target)
                    .put("point", JSONObject().put("x", x).put("y", y))
            )
        }
        return ParsedClicks(JSONObject().put("steps", clean), parsed)
    }

    private fun coordinate(point: JSONObject, axis: String, n: Int): Double {
        val value = point.opt(axis)
        if (value !is Number) throw IllegalArgumentException("Step $n: point.$axis must be a number.")
        val d = value.toDouble()
        if (d.isNaN() || d < 0 || d > 1000) {
            throw IllegalArgumentException("Step $n: point.$axis must be between 0 and 1000.")
        }
        return d
    }
}
