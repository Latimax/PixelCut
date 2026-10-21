package com.example.pixelcut.core

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import android.net.Uri
import androidx.exifinterface.media.ExifInterface
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.io.InputStream
import kotlin.math.max

object ImageUtils {

    private const val MAX_IMAGE_DIMENSION = 2048

    suspend fun decodeUriToBitmap(context: Context, uri: Uri): Result<Bitmap> = withContext(Dispatchers.IO) {
        runCatching {
            val resolver = context.contentResolver
            val tempFile = File(context.cacheDir, "temp_img_${System.currentTimeMillis()}.bin")

            try {
                // 1. Copy the stream to local app cache to bypass PhotoPicker permission restrictions
                var copied = false
                try {
                    resolver.openInputStream(uri)?.use { input ->
                        FileOutputStream(tempFile).use { output ->
                            input.copyTo(output)
                        }
                    }
                    copied = tempFile.exists() && tempFile.length() > 0
                } catch (e: Exception) {
                    copied = false
                }

                // If openInputStream failed or was denied, fallback to file descriptor
                if (!copied) {
                    resolver.openFileDescriptor(uri, "r")?.use { pfd ->
                        FileInputStream(pfd.fileDescriptor).use { input ->
                            FileOutputStream(tempFile).use { output ->
                                input.copyTo(output)
                            }
                        }
                    }
                }

                if (!tempFile.exists() || tempFile.length() == 0L) {
                    throw IllegalStateException("Cannot read image from $uri")
                }

                // 2. Read bounds to prevent OOM
                val boundsOptions = BitmapFactory.Options().apply {
                    inJustDecodeBounds = true
                }
                BitmapFactory.decodeFile(tempFile.absolutePath, boundsOptions)

                var sampleSize = 1
                var w = boundsOptions.outWidth
                var h = boundsOptions.outHeight
                while (w > MAX_IMAGE_DIMENSION || h > MAX_IMAGE_DIMENSION) {
                    sampleSize *= 2
                    w /= 2
                    h /= 2
                }

                // 3. Decode sampled bitmap
                val decodeOptions = BitmapFactory.Options().apply {
                    inSampleSize = sampleSize
                    inPreferredConfig = Bitmap.Config.ARGB_8888
                }
                val decodedBitmap = BitmapFactory.decodeFile(tempFile.absolutePath, decodeOptions)
                    ?: throw IllegalStateException("Failed to decode image from $uri")

                // 4. Correct EXIF orientation
                val orientation = FileInputStream(tempFile).use { stream ->
                    getExifOrientation(stream)
                }

                rotateBitmapIfNeeded(decodedBitmap, orientation)
            } finally {
                if (tempFile.exists()) {
                    tempFile.delete()
                }
            }
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
