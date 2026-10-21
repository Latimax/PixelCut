package com.example.pixelcut.core

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import android.net.Uri
import androidx.exifinterface.media.ExifInterface
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.InputStream
import kotlin.math.max

object ImageUtils {

    private const val MAX_IMAGE_DIMENSION = 2048

    suspend fun decodeUriToBitmap(context: Context, uri: Uri): Result<Bitmap> = withContext(Dispatchers.IO) {
        runCatching {
            val resolver = context.contentResolver

            // 1. Read bounds to avoid OOM
            val options = BitmapFactory.Options().apply {
                inJustDecodeBounds = true
            }
            resolver.openInputStream(uri)?.use { stream ->
                BitmapFactory.decodeStream(stream, null, options)
            } ?: throw IllegalStateException("Cannot open input stream for $uri")

            var sampleSize = 1
            var w = options.outWidth
            var h = options.outHeight
            while (w > MAX_IMAGE_DIMENSION || h > MAX_IMAGE_DIMENSION) {
                sampleSize *= 2
                w /= 2
                h /= 2
            }

            // 2. Decode sampled bitmap
            val decodeOptions = BitmapFactory.Options().apply {
                inSampleSize = sampleSize
                inPreferredConfig = Bitmap.Config.ARGB_8888
            }
            val decodedBitmap = resolver.openInputStream(uri)?.use { stream ->
                BitmapFactory.decodeStream(stream, null, decodeOptions)
            } ?: throw IllegalStateException("Failed to decode bitmap from $uri")

            // 3. Correct EXIF orientation
            val orientation = resolver.openInputStream(uri)?.use { stream ->
                getExifOrientation(stream)
            } ?: ExifInterface.ORIENTATION_NORMAL

            rotateBitmapIfNeeded(decodedBitmap, orientation)
        }
    }

    private fun getExifOrientation(inputStream: InputStream): Int {
        return try {
            val exif = ExifInterface(inputStream)
            exif.getAttributeInt(ExifInterface.TAG_ORIENTATION, ExifInterface.ORIENTATION_NORMAL)
        } catch (e: Exception) {
            ExifInterface.ORIENTATION_NORMAL
        }
    }

    private fun rotateBitmapIfNeeded(bitmap: Bitmap, orientation: Int): Bitmap {
        val matrix = Matrix()
        when (orientation) {
            ExifInterface.ORIENTATION_ROTATE_90 -> matrix.postRotate(90f)
            ExifInterface.ORIENTATION_ROTATE_180 -> matrix.postRotate(180f)
            ExifInterface.ORIENTATION_ROTATE_270 -> matrix.postRotate(270f)
            ExifInterface.ORIENTATION_FLIP_HORIZONTAL -> matrix.preScale(-1f, 1f)
            ExifInterface.ORIENTATION_FLIP_VERTICAL -> matrix.preScale(1f, -1f)
            else -> return bitmap
        }

        val rotated = Bitmap.createBitmap(bitmap, 0, 0, bitmap.width, bitmap.height, matrix, true)
        if (rotated != bitmap) {
            bitmap.recycle()
        }
        return rotated
    }
}
