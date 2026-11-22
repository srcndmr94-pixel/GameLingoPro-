package com.example.altyazi.v6

/** No new MediaProjection session can be created without a fresh user grant.
 * A paused/static app may produce no frames even when the projection is valid.
 */
internal object V6CaptureRecovery {
    const val MAX_RESIZE_REATTACHES = 2
    const val FIRST_RETRY_MS = 2500L
    const val SECOND_RETRY_DELAY_MS = 5000L

    fun shouldReattach(
        projectionActive: Boolean,
        resizeAtMs: Long,
        framesSinceResize: Int,
        tries: Int,
        lastTryAtMs: Long,
        nowMs: Long
    ): Boolean {
        if (!projectionActive || resizeAtMs <= 0L ||
            framesSinceResize > 0 || tries !in 0 until MAX_RESIZE_REATTACHES) return false
        val wait = if (tries == 0) FIRST_RETRY_MS else SECOND_RETRY_DELAY_MS
        return nowMs >= resizeAtMs + FIRST_RETRY_MS &&
            nowMs - lastTryAtMs >= wait
    }

    fun needsUserConsentMessage(tries: Int, framesSinceResize: Int): Boolean =
        tries >= MAX_RESIZE_REATTACHES && framesSinceResize == 0

    fun noFrameExplanation(imageEventsSinceResize: Int): String =
        if (imageEventsSinceResize == 0) "üretici yeni görüntü vermiyor"
        else "görüntü bildirimi var, ancak kare alınamadı"
}
