package com.mahedibuilds.screenlink

import org.junit.Assert.assertEquals
import org.junit.Test

class PromptLibraryTest {

    /** Loads from an in-memory folder: file name -> contents (null = unreadable). */
    private fun load(files: Map<String, String?>): List<Prompt> = PromptLibrary.load(
        list = { files.keys.toList() },
        read = { name -> files[name] ?: throw java.io.IOException("cannot read $name") },
    )

    private fun names(vararg files: String) = load(files.associateWith { "prompt text of $it" }).map { it.name }

    @Test
    fun generalThenPythonThenRestAlphabetically() {
        assertEquals(listOf("General", "Python", "Coding"), names("Coding.txt", "Python.txt", "General.txt"))
    }

    @Test
    fun guiComesDirectlyAfterGeneralAndPython() {
        assertEquals(
            listOf("General", "Python", "GUI", "Coding", "Email"),
            names("Email.txt", "GUI.txt", "Coding.txt", "Python.txt", "General.txt"),
        )
    }

    @Test
    fun orderIgnoresCaseAndFilesystemOrder() {
        val expected = listOf("general", "PYTHON", "Gui", "alpha", "Beta", "zeta")
        val files = listOf("zeta.txt", "Beta.txt", "Gui.txt", "alpha.txt", "PYTHON.txt", "general.txt")
        assertEquals(expected, names(*files.toTypedArray()))
        assertEquals(expected, names(*files.reversed().toTypedArray()))
        assertEquals(expected, names(*files.shuffled(java.util.Random(7)).toTypedArray()))
    }

    @Test
    fun onlyGeneralAndPython() {
        assertEquals(listOf("General", "Python"), names("General.txt", "Python.txt"))
    }

    @Test
    fun missingGeneralAndPythonStillLoadsTheRest() {
        assertEquals(listOf("GUI", "SQL"), names("SQL.txt", "GUI.txt"))
        assertEquals(emptyList<String>(), names())
    }

    @Test
    fun skipsEmptyUnreadableNonTxtAndCustomFiles() {
        val prompts = load(
            mapOf(
                "General.txt" to "Real prompt",
                "Empty.txt" to "  \n\n ",
                "Broken.txt" to null,
                "notes.md" to "not a prompt",
                "Custom.txt" to "should not become a second Custom tab",
                ".txt" to "no name",
            )
        )
        assertEquals(listOf("General"), prompts.map { it.name })
    }

    @Test
    fun usesFileContentsAsThePrompt() {
        val prompts = load(mapOf("General.txt" to "\r\nLine one\r\nLine two\r\n\r\n"))
        assertEquals("Line one\nLine two", prompts.single().text)
    }

    @Test
    fun duplicateNamesDifferingOnlyInCaseProduceOneTab() {
        assertEquals(1, names("Python.txt", "python.txt").size)
    }

    @Test
    fun readableLabelsKeepTheFileName() {
        val prompt = load(mapOf("Fill_in_the_blank.txt" to "x")).single()
        assertEquals("Fill_in_the_blank", prompt.name)
        assertEquals("Fill in the blank", prompt.label)
        assertEquals("Code review", PromptLibrary.label("Code-review"))
        assertEquals("SQL", PromptLibrary.label("SQL"))
    }

    @Test
    fun listingFailureMeansNoFileTabs() {
        val prompts = PromptLibrary.load(list = { throw java.io.IOException("no folder") }, read = { "" })
        assertEquals(emptyList<Prompt>(), prompts)
    }
}
