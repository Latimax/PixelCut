package com.example.pixelcut.ui.components

import android.graphics.Bitmap
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AddPhotoAlternate
import androidx.compose.material.icons.filled.Block
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Gradient
import androidx.compose.material.icons.filled.Palette
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.pixelcut.core.BackgroundType
import com.example.pixelcut.core.GradientPreset

private enum class BackgroundCategory {
    TRANSPARENT,
    SOLID,
    GRADIENT
}

val SOLID_COLOR_PALETTE = listOf(
    0xFFFFFFFF.toInt() to "White",
    0xFF000000.toInt() to "Black",
    0xFF1E293B.toInt() to "Slate",
    0xFF64748B.toInt() to "Steel",
    0xFF6366F1.toInt() to "Indigo",
    0xFFEC4899.toInt() to "Pink",
    0xFFEF4444.toInt() to "Red",
    0xFFF59E0B.toInt() to "Amber",
    0xFF10B981.toInt() to "Emerald",
    0xFF06B6D4.toInt() to "Cyan"
)

@Composable
fun BackgroundSelector(
    selectedBackground: BackgroundType,
    onBackgroundSelected: (BackgroundType) -> Unit,
    onPickCustomImage: () -> Unit,
    modifier: Modifier = Modifier
) {
    var activeCategory by remember {
        mutableStateOf(
            when (selectedBackground) {
                is BackgroundType.Transparent -> BackgroundCategory.TRANSPARENT
                is BackgroundType.Solid -> BackgroundCategory.SOLID
                is BackgroundType.Gradient -> BackgroundCategory.GRADIENT
                is BackgroundType.CustomImage -> BackgroundCategory.TRANSPARENT
            }
        )
    }

    Column(modifier = modifier.fillMaxWidth()) {
        // Category Tabs
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .horizontalScroll(rememberScrollState())
                .padding(horizontal = 16.dp, vertical = 4.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            FilterChip(
                selected = activeCategory == BackgroundCategory.TRANSPARENT && selectedBackground is BackgroundType.Transparent,
                onClick = {
                    activeCategory = BackgroundCategory.TRANSPARENT
                    onBackgroundSelected(BackgroundType.Transparent)
                },
                label = { Text("Transparent") },
                leadingIcon = { Icon(Icons.Default.Block, contentDescription = null, modifier = Modifier.size(16.dp)) },
                colors = FilterChipDefaults.filterChipColors(
                    selectedContainerColor = MaterialTheme.colorScheme.primaryContainer,
                    selectedLabelColor = MaterialTheme.colorScheme.onPrimaryContainer
                )
            )

            FilterChip(
                selected = activeCategory == BackgroundCategory.SOLID,
                onClick = {
                    activeCategory = BackgroundCategory.SOLID
                    if (selectedBackground !is BackgroundType.Solid) {
                        onBackgroundSelected(BackgroundType.Solid(SOLID_COLOR_PALETTE.first().first))
                    }
                },
                label = { Text("Solid Color") },
                leadingIcon = { Icon(Icons.Default.Palette, contentDescription = null, modifier = Modifier.size(16.dp)) }
            )

            FilterChip(
                selected = activeCategory == BackgroundCategory.GRADIENT,
                onClick = {
                    activeCategory = BackgroundCategory.GRADIENT
                    if (selectedBackground !is BackgroundType.Gradient) {
                        onBackgroundSelected(BackgroundType.Gradient(GradientPreset.values().first()))
                    }
                },
                label = { Text("Gradient") },
                leadingIcon = { Icon(Icons.Default.Gradient, contentDescription = null, modifier = Modifier.size(16.dp)) }
            )

            FilterChip(
                selected = selectedBackground is BackgroundType.CustomImage,
                onClick = onPickCustomImage,
                label = { Text("Custom Photo") },
                leadingIcon = { Icon(Icons.Default.AddPhotoAlternate, contentDescription = null, modifier = Modifier.size(16.dp)) }
            )
        }

        // Sub-options row
        when (activeCategory) {
            BackgroundCategory.SOLID -> {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .horizontalScroll(rememberScrollState())
                        .padding(horizontal = 16.dp, vertical = 8.dp),
                    horizontalArrangement = Arrangement.spacedBy(10.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    SOLID_COLOR_PALETTE.forEach { (colorInt, name) ->
                        val isSelected = selectedBackground is BackgroundType.Solid && selectedBackground.color == colorInt
                        Box(
                            modifier = Modifier
                                .size(40.dp)
                                .clip(CircleShape)
                                .background(Color(colorInt))
                                .border(
                                    width = if (isSelected) 3.dp else 1.dp,
                                    color = if (isSelected) Color(0xFF6366F1) else Color.DarkGray,
                                    shape = CircleShape
                                )
                                .clickable { onBackgroundSelected(BackgroundType.Solid(colorInt)) },
                            contentAlignment = Alignment.Center
                        ) {
                            if (isSelected) {
                                Icon(
                                    imageVector = Icons.Default.Check,
                                    contentDescription = name,
                                    tint = if (colorInt == 0xFFFFFFFF.toInt()) Color.Black else Color.White,
                                    modifier = Modifier.size(20.dp)
                                )
                            }
                        }
                    }
                }
            }
            BackgroundCategory.GRADIENT -> {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .horizontalScroll(rememberScrollState())
                        .padding(horizontal = 16.dp, vertical = 8.dp),
                    horizontalArrangement = Arrangement.spacedBy(10.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    GradientPreset.values().forEach { preset ->
                        val isSelected = selectedBackground is BackgroundType.Gradient && selectedBackground.preset == preset
                        val brush = Brush.linearGradient(preset.colors.map { Color(it) })
                        Box(
                            modifier = Modifier
                                .size(42.dp)
                                .clip(CircleShape)
                                .background(brush)
                                .border(
                                    width = if (isSelected) 3.dp else 1.dp,
                                    color = if (isSelected) Color.White else Color.DarkGray,
                                    shape = CircleShape
                                )
                                .clickable { onBackgroundSelected(BackgroundType.Gradient(preset)) },
                            contentAlignment = Alignment.Center
                        ) {
                            if (isSelected) {
                                Icon(
                                    imageVector = Icons.Default.Check,
                                    contentDescription = preset.title,
                                    tint = Color.White,
                                    modifier = Modifier.size(20.dp)
                                )
                            }
                        }
                    }
                }
            }
            BackgroundCategory.TRANSPARENT -> {
                // No sub-options needed for transparent
            }
        }
    }
}
