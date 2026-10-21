package com.example.pixelcut.ui.components

import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.example.pixelcut.core.AspectRatioPreset

@Composable
fun PresetSelector(
    selectedPreset: AspectRatioPreset,
    onPresetSelected: (AspectRatioPreset) -> Unit,
    shadowEnabled: Boolean,
    onToggleShadow: (Boolean) -> Unit,
    outlineEnabled: Boolean,
    onToggleOutline: (Boolean) -> Unit,
    modifier: Modifier = Modifier
) {
    Column(modifier = modifier.fillMaxWidth()) {
        // Aspect Ratio Row
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .horizontalScroll(rememberScrollState())
                .padding(horizontal = 16.dp, vertical = 4.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            AspectRatioPreset.values().forEach { preset ->
                val isSelected = selectedPreset == preset
                FilterChip(
                    selected = isSelected,
                    onClick = { onPresetSelected(preset) },
                    label = { Text(preset.title) },
                    colors = FilterChipDefaults.filterChipColors(
                        selectedContainerColor = MaterialTheme.colorScheme.primaryContainer,
                        selectedLabelColor = MaterialTheme.colorScheme.onPrimaryContainer
                    )
                )
            }
        }

        // Effects Row
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 4.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            FilterChip(
                selected = shadowEnabled,
                onClick = { onToggleShadow(!shadowEnabled) },
                label = { Text("Drop Shadow") }
            )

            FilterChip(
                selected = outlineEnabled,
                onClick = { onToggleOutline(!outlineEnabled) },
                label = { Text("White Outline") }
            )
        }
    }
}
