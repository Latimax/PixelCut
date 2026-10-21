package com.example.pixelcut

import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import com.example.pixelcut.ui.main.MainScreen
import com.example.pixelcut.ui.splash.SplashScreen

@Composable
fun MainNavigation() {
    var isSplashFinished by remember { mutableStateOf(false) }

    AnimatedContent(
        targetState = isSplashFinished,
        transitionSpec = {
            fadeIn(animationSpec = tween(450)) togetherWith fadeOut(animationSpec = tween(450))
        },
        label = "SplashToMainTransition",
        modifier = Modifier.fillMaxSize()
    ) { finished ->
        if (!finished) {
            SplashScreen(
                onSplashFinished = { isSplashFinished = true },
                modifier = Modifier.fillMaxSize()
            )
        } else {
            MainScreen(modifier = Modifier.safeDrawingPadding())
        }
    }
}
