package com.example.pixelcut.ui.main

import android.app.Application
import android.graphics.Bitmap
import android.net.Uri
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.example.pixelcut.core.AspectRatioPreset
import com.example.pixelcut.core.BackgroundType
import com.example.pixelcut.core.CompositionEngine
import com.example.pixelcut.core.ExportManager
import com.example.pixelcut.core.ImageUtils
import com.example.pixelcut.core.SegmentationEngine
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class MainUiState(
    val originalBitmap: Bitmap? = null,
    val cutoutBitmap: Bitmap? = null,
    val composedBitmap: Bitmap? = null,
    val isProcessing: Boolean = false,
    val processingTimeMs: Long? = null,
    val backgroundType: BackgroundType = BackgroundType.Transparent,
    val aspectRatio: AspectRatioPreset = AspectRatioPreset.ORIGINAL,
    val shadowEnabled: Boolean = false,
    val outlineEnabled: Boolean = false,
    val showBeforeAfter: Boolean = false,
    val userMessage: String? = null,
    val errorMessage: String? = null
)

class MainScreenViewModel(application: Application) : AndroidViewModel(application) {

    private val _uiState = MutableStateFlow(MainUiState())
    val uiState: StateFlow<MainUiState> = _uiState.asStateFlow()

    private val segmentationEngine by lazy {
        SegmentationEngine.getInstance(application)
    }

    fun processImageUri(uri: Uri) {
        viewModelScope.launch {
            _uiState.update { it.copy(isProcessing = true, errorMessage = null, userMessage = null) }

            val decodeResult = ImageUtils.decodeUriToBitmap(getApplication(), uri)
            decodeResult.fold(
                onSuccess = { bitmap ->
                    _uiState.update { it.copy(originalBitmap = bitmap) }
                    runSegmentation(bitmap)
                },
                onFailure = { error ->
                    _uiState.update {
                        it.copy(
                            isProcessing = false,
                            errorMessage = "Failed to load image: ${error.localizedMessage}"
                        )
                    }
                }
            )
        }
    }

    fun processBitmap(bitmap: Bitmap) {
        viewModelScope.launch {
            _uiState.update {
                it.copy(
                    originalBitmap = bitmap,
                    isProcessing = true,
                    errorMessage = null,
                    userMessage = null
                )
            }
            runSegmentation(bitmap)
        }
    }

    private suspend fun runSegmentation(sourceBitmap: Bitmap) {
        val result = segmentationEngine.removeBackground(sourceBitmap)
        result.fold(
            onSuccess = { segResult ->
                _uiState.update {
                    it.copy(
                        cutoutBitmap = segResult.cutoutBitmap,
                        processingTimeMs = segResult.inferenceTimeMs,
                        isProcessing = false
                    )
                }
                recompose()
            },
            onFailure = { error ->
                _uiState.update {
                    it.copy(
                        isProcessing = false,
                        errorMessage = "Segmentation failed: ${error.localizedMessage}"
                    )
                }
            }
        )
    }

    fun setBackground(bgType: BackgroundType) {
        _uiState.update { it.copy(backgroundType = bgType) }
        recompose()
    }

    fun setCustomBackground(bitmap: Bitmap) {
        _uiState.update { it.copy(backgroundType = BackgroundType.CustomImage(bitmap)) }
        recompose()
    }

    fun processCustomBackgroundUri(uri: Uri) {
        viewModelScope.launch {
            val decodeResult = ImageUtils.decodeUriToBitmap(getApplication(), uri)
            decodeResult.onSuccess { bitmap ->
                setCustomBackground(bitmap)
            }
        }
    }


    fun setAspectRatio(preset: AspectRatioPreset) {
        _uiState.update { it.copy(aspectRatio = preset) }
        recompose()
    }

    fun toggleShadow(enabled: Boolean) {
        _uiState.update { it.copy(shadowEnabled = enabled) }
        recompose()
    }

    fun toggleOutline(enabled: Boolean) {
        _uiState.update { it.copy(outlineEnabled = enabled) }
        recompose()
    }

    fun toggleBeforeAfter(show: Boolean) {
        _uiState.update { it.copy(showBeforeAfter = show) }
    }

    fun clearUserMessage() {
        _uiState.update { it.copy(userMessage = null, errorMessage = null) }
    }

    private fun recompose() {
        val state = _uiState.value
        val cutout = state.cutoutBitmap ?: return

        val shadowRadius = if (state.shadowEnabled) 24f else 0f
        val outlineWidth = if (state.outlineEnabled) 8f else 0f

        val composed = CompositionEngine.compose(
            cutoutBitmap = cutout,
            background = state.backgroundType,
            aspectRatio = state.aspectRatio,
            shadowRadius = shadowRadius,
            outlineWidth = outlineWidth
        )

        _uiState.update { it.copy(composedBitmap = composed) }
    }

    fun saveResultToGallery() {
        val state = _uiState.value
        val bitmapToSave = state.composedBitmap ?: state.cutoutBitmap ?: return

        viewModelScope.launch {
            _uiState.update { it.copy(isProcessing = true) }
            val format = if (state.backgroundType is BackgroundType.Transparent) {
                Bitmap.CompressFormat.PNG
            } else {
                Bitmap.CompressFormat.JPEG
            }

            val result = ExportManager.saveToGallery(getApplication(), bitmapToSave, format)
            result.fold(
                onSuccess = { uri ->
                    _uiState.update {
                        it.copy(
                            isProcessing = false,
                            userMessage = "Saved to Gallery (Pictures/PixelCut)!"
                        )
                    }
                },
                onFailure = { error ->
                    _uiState.update {
                        it.copy(
                            isProcessing = false,
                            errorMessage = "Failed to save: ${error.localizedMessage}"
                        )
                    }
                }
            )
        }
    }

    fun shareResult() {
        val state = _uiState.value
        val bitmapToShare = state.composedBitmap ?: state.cutoutBitmap ?: return

        viewModelScope.launch {
            val format = if (state.backgroundType is BackgroundType.Transparent) {
                Bitmap.CompressFormat.PNG
            } else {
                Bitmap.CompressFormat.JPEG
            }
            ExportManager.shareBitmap(getApplication(), bitmapToShare, format)
        }
    }
}
