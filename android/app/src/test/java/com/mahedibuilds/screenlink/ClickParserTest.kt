package com.mahedibuilds.screenlink

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class ClickParserTest {

    @Test
    fun parsesPromptFormat() {
        val reply = """
            {"steps": [
              {"action": "click", "target": "Java", "confidence": 0.99, "point": {"x": 366, "y": 347}},
              {"action": "click", "point": {"x": 0, "y": 1000.0}}
            ]}
        """
        val parsed = ClickParser.parse(reply)
        assertEquals(listOf(ClickStep("Java", 366.0, 347.0), ClickStep("", 0.0, 1000.0)), parsed.steps)
        val first = parsed.request.getJSONArray("steps").getJSONObject(0)
        assertEquals("click", first.getString("action"))
        assertEquals(366.0, first.getJSONObject("point").getDouble("x"), 0.0)
        // Fields the laptop does not need are dropped.
        assertEquals(false, first.has("confidence"))
    }

    @Test
    fun toleratesMarkdownFencesAndSurroundingText() {
        val reply = "Here you go:\n```json\n{\"steps\":[{\"action\":\"click\",\"point\":{\"x\":1,\"y\":2}}]}\n```"
        assertEquals(1, ClickParser.parse(reply).steps.size)
    }

    @Test
    fun rejectsInvalidResponses() {
        val bad = listOf(
            "def f(): return 1",
            "{not json}",
            "{\"answer\": 3}",
            "{\"steps\": []}",
            "{\"steps\": [{\"action\": \"type\", \"point\": {\"x\": 1, \"y\": 1}}]}",
            "{\"steps\": [{\"action\": \"click\"}]}",
            "{\"steps\": [{\"action\": \"click\", \"point\": {\"x\": \"1\", \"y\": 1}}]}",
            "{\"steps\": [{\"action\": \"click\", \"point\": {\"x\": 1001, \"y\": 1}}]}",
            "{\"steps\": [{\"action\": \"click\", \"point\": {\"x\": -5, \"y\": 1}}]}",
        )
        for (reply in bad) {
            assertThrows(reply, IllegalArgumentException::class.java) { ClickParser.parse(reply) }
        }
    }
}
