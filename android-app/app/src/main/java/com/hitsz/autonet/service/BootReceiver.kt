package com.hitsz.autonet.service

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.util.Log
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import com.hitsz.autonet.utils.PreferencesManager

/**
 * Receiver to start service on device boot
 */
class BootReceiver : BroadcastReceiver() {
    
    companion object {
        private const val TAG = "BootReceiver"
    }
    
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Intent.ACTION_BOOT_COMPLETED) {
            Log.i(TAG, "Boot completed - checking auto-start preference")
            
            val preferencesManager = PreferencesManager(context)
            
            // Check if auto-start is enabled
            CoroutineScope(Dispatchers.Default).launch {
                val autoStart = preferencesManager.autoStart.first()
                if (autoStart) {
                    Log.i(TAG, "Auto-start enabled - starting service")
                    val serviceIntent = Intent(context, NetworkMonitorService::class.java)
                    context.startForegroundService(serviceIntent)
                } else {
                    Log.i(TAG, "Auto-start disabled")
                }
            }
        }
    }
}
