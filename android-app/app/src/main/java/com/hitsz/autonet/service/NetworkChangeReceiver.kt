package com.hitsz.autonet.service

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.net.ConnectivityManager
import android.util.Log

/**
 * Receiver for network connectivity changes
 * Triggers login check when network state changes
 */
class NetworkChangeReceiver : BroadcastReceiver() {
    
    companion object {
        private const val TAG = "NetworkChangeReceiver"
    }
    
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == ConnectivityManager.CONNECTIVITY_ACTION) {
            Log.d(TAG, "Network state changed")
            
            // Service will handle the actual check on its next iteration
            // We could also trigger an immediate check here if needed
        }
    }
}
