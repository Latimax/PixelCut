package com.example.pixelcut.core

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Color
import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.InputStream
import java.nio.FloatBuffer
import java.util.Collections
import kotlin.math.max
import kotlin.math.min

data class SegmentationResult(
    val cutoutBitmap: Bitmap,
    val maskBitmap: Bitmap,
    val inferenceTimeMs: Long
)

class SegmentationEngine private constructor(
    private val env: OrtEnvironment,
    private val session: OrtSession
) : AutoCloseable {

    companion object {
        private const val MODEL_INPUT_SIZE = 320
        private const val MODEL_ASSET_PATH = "models/u2netp.onnx"

        // ImageNet normalization parameters
        private val MEAN = floatArrayOf(0.485f, 0.456f, 0.406f)
        private val STD = floatArrayOf(0.229f, 0.224f, 0.225f)

        @Volatile
        private var instance: SegmentationEngine? = null

        fun getInstance(context: Context): SegmentationEngine {
            return instance ?: synchronized(this) {
                instance ?: createInstance(context.applicationContext).also { instance = it }
            }
        }

        private fun createInstance(context: Context): SegmentationEngine {
            val env = OrtEnvironment.getEnvironment()
            val sessionOptions = OrtSession.SessionOptions().apply {
                setIntraOpNumThreads(Runtime.getRuntime().availableProcessors().coerceAtLeast(2))
                setOptimizationLevel(OrtSession.SessionOptions.OptLevel.ALL_OPT)
            }

            val modelBytes = context.assets.open(MODEL_ASSET_PATH).use { it.readBytes() }
            val session = env.createSession(modelBytes, sessionOptions)
            return SegmentationEngine(env, session)
        }
    }

    suspend fun removeBackground(inputBitmap: Bitmap): Result<SegmentationResult> = withContext(Dispatchers.Default) {
        runCatching {
            val startTime = System.currentTimeMillis()
            val origWidth = inputBitmap.width
            val origHeight = inputBitmap.height

            // 1. Resize input image to 320x320
            val resized = Bitmap.createScaledBitmap(inputBitmap, MODEL_INPUT_SIZE, MODEL_INPUT_SIZE, true)

            // 2. Extract pixels and build NCHW FloatBuffer [1, 3, 320, 320]
            val pixels = IntArray(MODEL_INPUT_SIZE * MODEL_INPUT_SIZE)
            resized.getPixels(pixels, 0, MODEL_INPUT_SIZE, 0, 0, MODEL_INPUT_SIZE, MODEL_INPUT_SIZE)

            val floatBuffer = FloatBuffer.allocate(1 * 3 * MODEL_INPUT_SIZE * MODEL_INPUT_SIZE)
            val channelSize = MODEL_INPUT_SIZE * MODEL_INPUT_SIZE

            // Channel 0: Red
            for (i in 0 until channelSize) {
                val p = pixels[i]
                val r = (Color.red(p) / 255.0f - MEAN[0]) / STD[0]
                floatBuffer.put(r)
            }
            // Channel 1: Green
            for (i in 0 until channelSize) {
                val p = pixels[i]
                val g = (Color.green(p) / 255.0f - MEAN[1]) / STD[1]
                floatBuffer.put(g)
            }
            // Channel 2: Blue
            for (i in 0 until channelSize) {
                val p = pixels[i]
                val b = (Color.blue(p) / 255.0f - MEAN[2]) / STD[2]
                floatBuffer.put(b)
            }
            floatBuffer.rewind()

            // 3. Create Tensor and Run Inference
            val inputName = session.inputNames.iterator().next()
            val inputTensor = OnnxTensor.createTensor(env, floatBuffer, longArrayOf(1, 3, MODEL_INPUT_SIZE.toLong(), MODEL_INPUT_SIZE.toLong()))

            val results = session.run(Collections.singletonMap(inputName, inputTensor))
            val outputTensor = results[0].value as Array<Array<Array<FloatArray>>>
            val rawMask = outputTensor[0][0] // [320][320]

            // Clean up ONNX tensors
            inputTensor.close()
            results.close()

            // 4. Normalize mask (0.0 .. 1.0) and find min/max
            var minVal = Float.MAX_VALUE
            var maxVal = Float.MIN_VALUE
            for (y in 0 until MODEL_INPUT_SIZE) {
                for (x in 0 until MODEL_INPUT_SIZE) {
                    val v = rawMask[y][x]
                    if (v < minVal) minVal = v
                    if (v > maxVal) maxVal = v
                }
            }

            val range = if (maxVal - minVal > 1e-6f) maxVal - minVal else 1f
            val maskPixels320 = IntArray(MODEL_INPUT_SIZE * MODEL_INPUT_SIZE)

            for (y in 0 until MODEL_INPUT_SIZE) {
                for (x in 0 until MODEL_INPUT_SIZE) {
                    val norm = ((rawMask[y][x] - minVal) / range).coerceIn(0f, 1f)
                    val alpha = (norm * 255.0f).toInt().coerceIn(0, 255)
                    maskPixels320[y * MODEL_INPUT_SIZE + x] = Color.argb(255, alpha, alpha, alpha)
                }
            }

            // Create 320x320 mask bitmap
            val maskBitmap320 = Bitmap.createBitmap(MODEL_INPUT_SIZE, MODEL_INPUT_SIZE, Bitmap.Config.ARGB_8888)
            maskBitmap320.setPixels(maskPixels320, 0, MODEL_INPUT_SIZE, 0, 0, MODEL_INPUT_SIZE, MODEL_INPUT_SIZE)

            // Upsample mask to original dimensions
            val fullMaskBitmap = Bitmap.createScaledBitmap(maskBitmap320, origWidth, origHeight, true)

            // 5. Combine original image RGB with mask alpha channel
            val origPixels = IntArray(origWidth * origHeight)
            inputBitmap.getPixels(origPixels, 0, origWidth, 0, 0, origWidth, origHeight)

            val fullMaskPixels = IntArray(origWidth * origHeight)
            fullMaskBitmap.getPixels(fullMaskPixels, 0, origWidth, 0, 0, origWidth, origHeight)

            val cutoutPixels = IntArray(origWidth * origHeight)
            for (i in 0 until origWidth * origHeight) {
                val origPixel = origPixels[i]
                val maskVal = Color.red(fullMaskPixels[i]) // 0..255

                // Apply soft threshold curve to clean edge fringe
                val alpha = when {
                    maskVal < 15 -> 0
                    maskVal > 240 -> 255
                    else -> maskVal
                }

                cutoutPixels[i] = Color.argb(
                    alpha,
                    Color.red(origPixel),
                    Color.green(origPixel),
                    Color.blue(origPixel)
                )
            }

            val cutoutBitmap = Bitmap.createBitmap(origWidth, origHeight, Bitmap.Config.ARGB_8888)
            cutoutBitmap.setPixels(cutoutPixels, 0, origWidth, 0, 0, origWidth, origHeight)

            val elapsed = System.currentTimeMillis() - startTime
            SegmentationResult(cutoutBitmap, fullMaskBitmap, elapsed)
        }
    }

    override fun close() {
        session.close()
    }
}
