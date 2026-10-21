package com.example.pixelcut.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp

@Composable
fun CheckerboardCanvas(
    modifier: Modifier = Modifier,
    squareSizeDp: Float = 14f,
    lightColor: Color = Color(0xFF1E293B), // slate-800
    darkColor: Color = Color(0xFF0F172A)   // slate-900
) {
    Canvas(modifier = modifier.fillMaxSize()) {
        val squarePx = squareSizeDp * density
        val cols = (size.width / squarePx).toInt() + 1
        val rows = (size.height / squarePx).toInt() + 1

        for (r in 0 until rows) {
            for (c in 0 until cols) {
                val color = if ((r + c) % 2 == 0) lightColor else darkColor
                drawRect(
                    color = color,
                    topLeft = Offset(c * squarePx, r * squarePx),
                    size = Size(squarePx, squarePx)
                )
            }
        }
    }
}
