package com.mahedibuilds.screenlink

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import androidx.core.content.FileProvider
import java.io.File

/** Android clipboard and share-sheet helpers. */
object Sharing {

    fun copy(context: Context, label: String, text: String) {
        val clipboard = context.getSystemService(ClipboardManager::class.java)
        clipboard.setPrimaryClip(ClipData.newPlainText(label, text))
    }

    fun paste(context: Context): String? {
        val clipboard = context.getSystemService(ClipboardManager::class.java)
        val clip = clipboard.primaryClip ?: return null
        if (clip.itemCount == 0) return null
        return clip.getItemAt(0).coerceToText(context)?.toString()
    }

    fun shareText(context: Context, text: String) {
        val intent = Intent(Intent.ACTION_SEND).apply {
            type = "text/plain"
            putExtra(Intent.EXTRA_TEXT, text)
        }
        context.startActivity(Intent.createChooser(intent, "Share prompt"))
    }

    /** Shares the screenshot (optionally with the prompt as text) through the share sheet. */
    fun shareScreenshot(context: Context, jpeg: ByteArray, text: String?) {
        // One file in the cache, overwritten each time: nothing accumulates on the phone.
        val dir = File(context.cacheDir, "shared").apply { mkdirs() }
        val file = File(dir, "screenlink-screenshot.jpg")
        file.writeBytes(jpeg)
        val uri = FileProvider.getUriForFile(context, "${context.packageName}.files", file)

        val intent = Intent(Intent.ACTION_SEND).apply {
            type = "image/jpeg"
            putExtra(Intent.EXTRA_STREAM, uri)
            if (text != null) putExtra(Intent.EXTRA_TEXT, text)
            clipData = ClipData.newRawUri("Screenshot", uri)
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        context.startActivity(Intent.createChooser(intent, "Share screenshot"))
    }
}
