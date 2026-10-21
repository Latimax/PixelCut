package com.example.pixelcut.ui.components

import android.graphics.Bitmap
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.SwapHoriz
import androidx.compose.material3.Icon
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.clipToBounds
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.dp
import kotlin.math.roundToInt

@Composable
fun BeforeAfterSlider(
    beforeBitmap: Bitmap,
    afterBitmap: Bitmap,
    modifier: Modifier = Modifier
) {
    var splitFraction by remember { mutableFloatStateOf(0.5f) }

    BoxWithConstraints(
        modifier = modifier
            .fillMaxSize()
            .clipToBounds()
    ) {
        val containerWidth = maxWidth
        val totalWidth = constraints.maxWidth.toFloat()
        val splitPx = totalWidth * splitFraction

        // Layer 1: Background / After Image (Full width)
        Box(modifier = Modifier.fillMaxSize()) {
            CheckerboardCanvas()
            Image(
                bitmap = afterBitmap.asImageBitmap(),
                contentDescription = "After Background Removal",
                modifier = Modifier.fillMaxSize(),
                contentScale = ContentScale.Fit
            )
        }

        // Layer 2: Original Before Image (Clipped to left side of split)
        Box(
            modifier = Modifier
                .fillMaxHeight()
                .width(containerWidth * splitFraction)
                .clipToBounds()
        ) {
            Image(
                bitmap = beforeBitmap.asImageBitmap(),
                contentDescription = "Before (Original)",
                modifier = Modifier
                    .fillMaxHeight()
                    .width(containerWidth),
                contentScale = ContentScale.Fit
            )
        }


        // Layer 3: Divider Line and Drag Handle
        Box(
            modifier = Modifier
                .offset { IntOffset(splitPx.roundToInt() - 1.dp.roundToPx(), 0) }
                .fillMaxHeight()
                .width(2.dp)
                .background(Color.White)
        )

        Box(
            modifier = Modifier
                .offset {
                    IntOffset(
                        (splitPx - 20.dp.roundToPx()).roundToInt(),
                        (constraints.maxHeight / 2 - 20.dp.roundToPx())
                    )
                }
                .size(40.dp)
                .clip(CircleShape)
                .background(Color(0xFF6366F1)) // Indigo accent
                .pointerInput(Unit) {
                    detectDragGestures { change, dragAmount ->
                        change.consume()
                        val newFraction = (splitFraction + dragAmount.x / totalWidth).coerceIn(0.05f, 0.95f)
                        splitFraction = newFraction
                    }
                },
            contentAlignment = Alignment.Center
        ) {
            Icon(
                imageVector = Icons.Default.SwapHoriz,
                contentDescription = "Drag to compare",
                tint = Color.White,
                modifier = Modifier.size(24.dp)
            )
        }
    }
}
