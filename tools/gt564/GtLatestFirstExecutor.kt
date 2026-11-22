package com.example.altyazi

import java.util.concurrent.Executor
import java.util.concurrent.LinkedBlockingDeque
import java.util.concurrent.ThreadFactory
import java.util.concurrent.ThreadPoolExecutor
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger

/** Original GameTranslator requests remain unchanged; only scheduling is adapted.
 * At most 2 in-flight calls plus ONE newest pending request are retained.
 */
internal class GtLatestFirstExecutor(
    private val onStart: (queueMs: Long) -> Unit = {},
    private val clockMs: () -> Long = { System.nanoTime() / 1_000_000L },
) : Executor {
    private val dropped = AtomicInteger()
    private val threadId = AtomicInteger()
    private val pool = ThreadPoolExecutor(
        2, 2, 0L, TimeUnit.MILLISECONDS,
        LinkedBlockingDeque<Runnable>(1),
        ThreadFactory { task ->
            Thread(task, "gt-original-fast-" + threadId.incrementAndGet()).apply { isDaemon = true }
        },
        ThreadPoolExecutor.DiscardPolicy()
    )

    @Synchronized override fun execute(command: Runnable) {
        if (pool.isShutdown) return
        val submittedAt = clockMs()
        val wrapped = Runnable {
            onStart((clockMs() - submittedAt).coerceAtLeast(0L))
            command.run()
        }
        if (pool.activeCount >= 2 && pool.queue.remainingCapacity() == 0) {
            if (pool.queue.poll() != null) dropped.incrementAndGet()
        }
        pool.execute(wrapped)
    }
    fun discardedOldRequests(): Int = dropped.get()
    fun close() = pool.shutdownNow()
}
