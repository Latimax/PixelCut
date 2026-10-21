package com.example.pixelcut.core

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.LinearGradient
import android.graphics.Paint
import android.graphics.Rect
import android.graphics.RectF
import android.graphics.Shader

sealed class BackgroundType {
    object Transparent : BackgroundType()
    data class Solid(val color: Int) : BackgroundType()
    data class Gradient(val preset: GradientPreset) : BackgroundType()
    data class CustomImage(val bitmap: Bitmap) : BackgroundType()
}

enum class GradientPreset(val title: String, val colors: IntArray) {
    SUNSET("Sunset Glow", intArrayOf(Color.parseColor("#FF512F"), Color.parseColor("#DD2476"))),
    NEON_CYBER("Cyberpunk", intArrayOf(Color.parseColor("#00F260"), Color.parseColor("#0575E6"))),
    ROYAL_VIOLET("Royal Violet", intArrayOf(Color.parseColor("#8A2387"), Color.parseColor("#E94057"), Color.parseColor("#F27121"))),
    OCEAN_BREEZE("Ocean Breeze", intArrayOf(Color.parseColor("#2E3192"), Color.parseColor("#1BFFFF"))),
    CLEAN_STUDIO("Clean Studio", intArrayOf(Color.parseColor("#F5F7FA"), Color.parseColor("#C3CFE2"))),
    MIDNIGHT("Midnight Slate", intArrayOf(Color.parseColor("#0F2027"), Color.parseColor("#203A43"), Color.parseColor("#2C5364")))
}

enum class AspectRatioPreset(val title: String, val widthRatio: Float, val heightRatio: Float) {
    ORIGINAL("Original", 0f, 0f),
    SQUARE_1_1("1:1 Square", 1f, 1f),
    PORTRAIT_4_5("4:5 Instagram", 4f, 5f),
    STORY_9_16("9:16 Story", 9f, 16f),
    LANDSCAPE_16_9("16:9 Banner", 16f, 9f)
}

object CompositionEngine {

    fun compose(
        cutoutBitmap: Bitmap,
        background: BackgroundType,
        aspectRatio: AspectRatioPreset = AspectRatioPreset.ORIGINAL,
        shadowRadius: Float = 0f,
        outlineWidth: Float = 0f,
        outlineColor: Int = Color.WHITE
    ): Bitmap {
        val origW = cutoutBitmap.width
        val origH = cutoutBitmap.height

        val (targetW, targetH) = if (aspectRatio == AspectRatioPreset.ORIGINAL) {
            origW to origH
        } else {
            val ratio = aspectRatio.widthRatio / aspectRatio.heightRatio
            val origRatio = origW.toFloat() / origH.toFloat()
            if (origRatio > ratio) {
                // Image is wider than target ratio: expand height
                origW to (origW / ratio).toInt()
            } else {
                // Image is taller than target ratio: expand width
                (origH * ratio).toInt() to origH
            }
        }

        val resultBitmap = Bitmap.createBitmap(targetW, targetH, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(resultBitmap)

        // 1. Draw Background
        val paint = Paint(Paint.ANTI_ALIAS_FLAG)
        when (background) {
            is BackgroundType.Transparent -> {
                // Keep canvas transparent
            }
            is BackgroundType.Solid -> {
                canvas.drawColor(background.color)
            }
            is BackgroundType.Gradient -> {
                val gradient = LinearGradient(
                    0f, 0f, targetW.toFloat(), targetH.toFloat(),
                    background.preset.colors,
                    null,
                    Shader.TileMode.CLAMP
                )
                paint.shader = gradient
                canvas.drawRect(0f, 0f, targetW.toFloat(), targetH.toFloat(), paint)
                paint.shader = null
            }
            is BackgroundType.CustomImage -> {
                val bgBitmap = background.bitmap
                val srcRect = Rect(0, 0, bgBitmap.width, bgBitmap.height)
                val dstRect = Rect(0, 0, targetW, targetH)
                canvas.drawBitmap(bgBitmap, srcRect, dstRect, paint)
            }
        }

        // 2. Position cutout in center of target canvas
        val offsetX = (targetW - origW) / 2f
        val offsetY = (targetH - origH) / 2f

        // 3. Optional Drop Shadow
        if (shadowRadius > 0f) {
            val shadowPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
                setShadowLayer(shadowRadius, 0f, shadowRadius * 0.4f, Color.argb(130, 0, 0, 0))
            }
            // Draw alpha mask to cast shadow
            val alphaMask = cutoutBitmap.extractAlpha()
            canvas.drawBitmap(alphaMask, offsetX, offsetY, shadowPaint)
        }

        // 4. Optional Outline
        if (outlineWidth > 0f) {
            val outlinePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
                style = Paint.Style.STROKE
                strokeWidth = outlineWidth
                color = outlineColor
            }
            val alphaMask = cutoutBitmap.extractAlpha()
            // Expand slightly or draw shifted offsets for stroke outline
            for (dx in -1..1) {
                for (dy in -1..1) {
                    if (dx != 0 || dy != 0) {
                        canvas.drawBitmap(alphaMask, offsetX + dx * outlineWidth * 0.5f, offsetY + dy * outlineWidth * 0.5f, outlinePaint)
                    }
                }
            }
        }

        // 5. Draw Foreground Cutout
        val drawPaint = Paint(Paint.ANTI_ALIAS_FLAG or Paint.FILTER_BITMAP_FLAG)
        canvas.drawBitmap(cutoutBitmap, offsetX, offsetY, drawPaint)

        return resultBitmap
    }
}
