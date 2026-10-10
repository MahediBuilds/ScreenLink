package com.mahedibuilds.screenlink

import org.json.JSONArray
import org.json.JSONException
import org.json.JSONObject

/** Prompt templates bundled in res/raw. CUSTOM starts from its template and can be edited. */
enum class PromptType(val label: String, val rawRes: Int) {
    GENERAL("General", R.raw.prompt_general),
    FILL_BLANK("Fill in the blank", R.raw.prompt_fill_blank),
    PYTHON("Python", R.raw.prompt_python),
    SQL("SQL", R.raw.prompt_sql),
    EMAIL("Email", R.raw.prompt_email),
    CLICK("Click", R.raw.prompt_click),
    CUSTOM("Custom", R.raw.prompt_custom),
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
