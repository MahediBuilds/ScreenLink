package com.mahedibuilds.screenlink

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectTransformGestures
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilterChip
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import androidx.lifecycle.viewmodel.compose.viewModel

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent { ScreenLinkTheme { ScreenLinkApp() } }
    }
}

@Composable
fun ScreenLinkTheme(content: @Composable () -> Unit) {
    val dark = isSystemInDarkTheme()
    val context = LocalContext.current
    val colors = when {
        Build.VERSION.SDK_INT >= Build.VERSION_CODES.S ->
            if (dark) dynamicDarkColorScheme(context) else dynamicLightColorScheme(context)
        dark -> darkColorScheme()
        else -> lightColorScheme()
    }
    MaterialTheme(colorScheme = colors, content = content)
}

@Composable
fun ScreenLinkApp(vm: ScreenLinkViewModel = viewModel()) {
    Surface(Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
        Column(
            Modifier
                .safeDrawingPadding()
                .imePadding()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 16.dp, vertical = 12.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text("ScreenLink", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
            ConnectionCard(vm)
            ScreenshotCard(vm)
            PromptCard(vm)
            ResponseCard(vm)
            Spacer(Modifier.size(24.dp))
        }
    }
}

@Composable
private fun Section(title: String, content: @Composable () -> Unit) {
    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            content()
        }
    }
}

// ----- connection -----------------------------------------------------------

@Composable
private fun ConnectionCard(vm: ScreenLinkViewModel) {
    Section("Laptop") {
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedTextField(
                value = vm.host,
                onValueChange = { vm.updateAddress(newHost = it.trim()) },
                label = { Text("Laptop IP address") },
                placeholder = { Text("e.g. 192.168.1.20") },
                singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri),
                modifier = Modifier.weight(1f),
            )
            OutlinedTextField(
                value = vm.port,
                onValueChange = { vm.updateAddress(newPort = it.filter(Char::isDigit).take(5)) },
                label = { Text("Port") },
                singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                modifier = Modifier.width(96.dp),
            )
        }

        val (dotColor, label) = when (vm.connState) {
            ConnState.CONNECTED -> Color(0xFF2E7D32) to "Connected"
            ConnState.CHECKING -> Color(0xFFF9A825) to "Checking..."
            ConnState.NOT_PAIRED -> Color(0xFFF9A825) to "Not paired"
            ConnState.FAILED -> Color(0xFFC62828) to "Not reachable"
            ConnState.NOT_CONNECTED -> Color.Gray to "Not connected"
        }
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Box(Modifier.size(12.dp).background(dotColor, CircleShape))
            Text(label, fontWeight = FontWeight.SemiBold)
        }
        Text(vm.connMessage, style = MaterialTheme.typography.bodyMedium)

        Button(
            onClick = vm::connect,
            enabled = vm.connState != ConnState.CHECKING,
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text(if (vm.connState == ConnState.NOT_CONNECTED) "Connect" else "Reconnect")
        }

        if (vm.connState == ConnState.NOT_PAIRED) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(
                    value = vm.pairingCode,
                    onValueChange = { vm.pairingCode = it.filter(Char::isDigit).take(12) },
                    label = { Text("Pairing code") },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.NumberPassword),
                    modifier = Modifier.weight(1f),
                )
                Button(onClick = vm::pair) { Text("Pair") }
            }
        }
        if (vm.connState == ConnState.CONNECTED) {
            TextButton(onClick = vm::forgetPairing) { Text("Forget pairing") }
        }
    }
}

// ----- screenshot -----------------------------------------------------------

@Composable
private fun ScreenshotCard(vm: ScreenLinkViewModel) {
    val context = LocalContext.current
    var fullscreen by remember { mutableStateOf(false) }
    val save: (ByteArray) -> Unit = { jpeg ->
        try {
            Sharing.saveToGallery(context, jpeg)
            vm.showMessage(MessageKind.SUCCESS, "Screenshot saved to Pictures/ScreenLink.")
        } catch (e: Exception) {
            vm.showMessage(MessageKind.ERROR, "Could not save screenshot: ${e.message}")
        }
    }
    val storagePermission = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        val jpeg = vm.screenshot?.jpeg
        if (!granted) vm.showMessage(MessageKind.ERROR, "Storage permission is needed to save to the gallery.")
        else if (jpeg != null) save(jpeg)
    }

    Section("Screenshot") {
        Button(
            onClick = vm::takeScreenshot,
            enabled = vm.isReady && !vm.screenshotLoading,
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text(if (vm.screenshotError != null) "Retry screenshot" else "Take screenshot")
        }
        if (vm.screenshotLoading) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                CircularProgressIndicator(Modifier.size(20.dp), strokeWidth = 2.dp)
                Text("Capturing laptop screen...")
            }
        }
        vm.screenshotError?.let { ErrorText(it) }

        val image = vm.screenshotImage
        val shot = vm.screenshot
        if (image != null && shot != null) {
            Image(
                bitmap = image,
                contentDescription = "Laptop screenshot. Tap to zoom.",
                contentScale = ContentScale.FillWidth,
                modifier = Modifier.fillMaxWidth().clickable { fullscreen = true },
            )
            Text(
                "${shot.width}x${shot.height}, ${shot.jpeg.size / 1024} KB, taken ${vm.screenshotTime}. Tap to zoom.",
                style = MaterialTheme.typography.bodySmall,
            )
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(
                    onClick = { Sharing.shareScreenshot(context, shot.jpeg, null) },
                    modifier = Modifier.weight(1f),
                ) { Text("Share") }
                OutlinedButton(
                    onClick = {
                        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q &&
                            context.checkSelfPermission(Manifest.permission.WRITE_EXTERNAL_STORAGE) !=
                            PackageManager.PERMISSION_GRANTED
                        ) {
                            storagePermission.launch(Manifest.permission.WRITE_EXTERNAL_STORAGE)
                        } else {
                            save(shot.jpeg)
                        }
                    },
                    modifier = Modifier.weight(1f),
                ) { Text("Save to gallery") }
            }

            if (fullscreen) ZoomDialog(image) { fullscreen = false }
        }
    }
}

@Composable
private fun ZoomDialog(image: androidx.compose.ui.graphics.ImageBitmap, onClose: () -> Unit) {
    var scale by remember { mutableFloatStateOf(1f) }
    var offset by remember { mutableStateOf(Offset.Zero) }
    Dialog(onDismissRequest = onClose, properties = DialogProperties(usePlatformDefaultWidth = false)) {
        Box(
            Modifier
                .fillMaxSize()
                .background(Color.Black)
                .pointerInput(Unit) {
                    detectTransformGestures { _, pan, zoom, _ ->
                        scale = (scale * zoom).coerceIn(1f, 8f)
                        offset = if (scale == 1f) Offset.Zero else offset + pan
                    }
                },
        ) {
            Image(
                bitmap = image,
                contentDescription = "Laptop screenshot, pinch to zoom",
                contentScale = ContentScale.Fit,
                modifier = Modifier
                    .fillMaxSize()
                    .graphicsLayer(scaleX = scale, scaleY = scale, translationX = offset.x, translationY = offset.y),
            )
            TextButton(
                onClick = onClose,
                modifier = Modifier.align(Alignment.TopEnd).safeDrawingPadding(),
            ) { Text("Close", color = Color.White) }
        }
    }
}

// ----- prompts --------------------------------------------------------------

@Composable
private fun PromptCard(vm: ScreenLinkViewModel) {
    val context = LocalContext.current
    Section("Prompt") {
        Row(
            Modifier.horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            vm.prompts.forEach { prompt ->
                FilterChip(
                    selected = vm.selectedPrompt == prompt.name,
                    onClick = { vm.selectPrompt(prompt.name) },
                    label = { Text(prompt.label) },
                )
            }
            FilterChip(
                selected = vm.isCustomSelected,
                onClick = { vm.selectPrompt(null) },
                label = { Text(ScreenLinkViewModel.CUSTOM_LABEL) },
            )
        }

        val prompt = vm.promptText()
        if (vm.isCustomSelected) {
            OutlinedTextField(
                value = vm.customPrompt,
                onValueChange = vm::updateCustomPrompt,
                label = { Text("Custom prompt (saved automatically)") },
                modifier = Modifier.fillMaxWidth().heightIn(min = 120.dp),
            )
            TextButton(onClick = vm::resetCustomPrompt) { Text("Reset to default") }
        } else {
            Text(
                prompt,
                style = MaterialTheme.typography.bodySmall,
                fontFamily = FontFamily.Monospace,
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(max = 220.dp)
                    .verticalScroll(rememberScrollState())
                    .background(MaterialTheme.colorScheme.surfaceVariant)
                    .padding(8.dp),
            )
        }

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedButton(
                onClick = {
                    Sharing.copy(context, "ScreenLink prompt", prompt)
                    vm.showMessage(MessageKind.SUCCESS, "${vm.promptLabel()} prompt copied to the clipboard.")
                },
                enabled = prompt.isNotBlank(),
                modifier = Modifier.weight(1f),
            ) { Text("Copy prompt") }
            OutlinedButton(
                onClick = { Sharing.shareText(context, prompt) },
                enabled = prompt.isNotBlank(),
                modifier = Modifier.weight(1f),
            ) { Text("Share prompt") }
        }
        val shot = vm.screenshot
        Button(
            onClick = {
                if (shot != null) {
                    // Many apps ignore text sent alongside an image, so also put the prompt on the clipboard.
                    Sharing.copy(context, "ScreenLink prompt", prompt)
                    Sharing.shareScreenshot(context, shot.jpeg, prompt)
                }
            },
            enabled = shot != null,
            modifier = Modifier.fillMaxWidth(),
        ) { Text(if (shot != null) "Share screenshot + prompt" else "Take a screenshot to share it") }
    }
}

// ----- response & actions ---------------------------------------------------

@Composable
private fun ResponseCard(vm: ScreenLinkViewModel) {
    val context = LocalContext.current
    Section("AI response") {
        OutlinedTextField(
            value = vm.response,
            onValueChange = { vm.response = it },
            label = { Text("Paste the AI response here") },
            modifier = Modifier.fillMaxWidth().heightIn(min = 140.dp),
        )
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedButton(
                onClick = {
                    val text = Sharing.paste(context)
                    if (text.isNullOrEmpty()) vm.showMessage(MessageKind.ERROR, "Clipboard is empty.")
                    else vm.response = text
                },
                modifier = Modifier.weight(1f),
            ) { Text("Paste") }
            OutlinedButton(
                onClick = { vm.response = "" },
                enabled = vm.response.isNotEmpty(),
                modifier = Modifier.weight(1f),
            ) { Text("Clear") }
        }

        HorizontalDivider()
        Text("Type on laptop", fontWeight = FontWeight.SemiBold)
        Text(
            "Types the response line by line into whichever window is focused on the laptop.",
            style = MaterialTheme.typography.bodySmall,
        )
        if (vm.typingActive) {
            val job = vm.typingJob
            if (job != null && job.total > 0) {
                LinearProgressIndicator(progress = { job.typed / job.total.toFloat() }, modifier = Modifier.fillMaxWidth())
                Text("Typing ${job.typed} / ${job.total}", style = MaterialTheme.typography.bodySmall)
            } else {
                LinearProgressIndicator(Modifier.fillMaxWidth())
            }
            Button(
                onClick = vm::cancelTyping,
                enabled = !vm.cancelRequested,
                modifier = Modifier.fillMaxWidth(),
            ) { Text(if (vm.cancelRequested) "Cancelling..." else "Cancel typing") }
        } else {
            Button(
                onClick = vm::sendText,
                enabled = vm.isReady && !vm.actionBusy && vm.response.isNotBlank(),
                modifier = Modifier.fillMaxWidth(),
            ) { Text("Send text to laptop") }
        }

        HorizontalDivider()
        Text("Click on laptop", fontWeight = FontWeight.SemiBold)
        Text(
            "For responses to the GUI prompt: JSON with normalized (0-1000) points.",
            style = MaterialTheme.typography.bodySmall,
        )
        if (vm.response.isNotBlank()) {
            vm.parseClicks().fold(
                onSuccess = { parsed ->
                    parsed.steps.forEachIndexed { i, step ->
                        val name = step.target.ifBlank { "point" }
                        Text(
                            "${i + 1}. $name at (${step.x.toInt()}, ${step.y.toInt()})",
                            style = MaterialTheme.typography.bodySmall,
                        )
                    }
                },
                onFailure = {
                    Text("Not a click response: ${it.message}", style = MaterialTheme.typography.bodySmall)
                },
            )
        }
        OutlinedButton(
            onClick = vm::executeClicks,
            enabled = vm.isReady && !vm.actionBusy && vm.parseClicks().isSuccess,
            modifier = Modifier.fillMaxWidth(),
        ) {
            if (vm.clickBusy) {
                CircularProgressIndicator(Modifier.size(18.dp), strokeWidth = 2.dp)
                Spacer(Modifier.width(8.dp))
                Text("Clicking...")
            } else {
                Text("Execute clicks on laptop")
            }
        }

        vm.message?.let { msg ->
            val color = when (msg.kind) {
                MessageKind.SUCCESS -> Color(0xFF2E7D32)
                MessageKind.ERROR -> MaterialTheme.colorScheme.error
                MessageKind.INFO -> MaterialTheme.colorScheme.onSurface
            }
            Text(msg.text, color = color, fontWeight = FontWeight.Medium)
        }
    }
}

@Composable
private fun ErrorText(text: String) {
    Text(text, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodyMedium)
}
